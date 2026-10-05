#!/bin/bash
# Runs on the instance every 2 minutes (systemd timer): pull the latest image, and restart the app behind Caddy only if
# the image or the secrets changed. Terraform fills in the region, image, domain and parameter path (bash expansions
# are escaped as $${...}). Run it by hand with `sudo /opt/app/deploy.sh` (e.g. through SSM Session Manager).
set -euo pipefail
REGION="${region}" IMAGE="${image}:latest" DOMAIN="${domain}" PARAMS="${param_path}" REGISTRY_USER="${registry_user}"
cd /opt/app

# Secrets: SSM Parameter Store (SecureString) -> an env file only root can read.
umask 077
aws ssm get-parameters-by-path --region "$REGION" --path "$PARAMS" --with-decryption \
  --query 'Parameters[].[Name,Value]' --output text | while IFS=$'\t' read -r name value; do
  echo "$${name##*/}=$value"; done | sort > app.env.new
if [ ! -s app.env.new ]; then echo "no secrets in SSM under $PARAMS yet"; rm -f app.env.new; exit 0; fi
# The image is private: log in with the read-only package token, which the app itself never sees.
grep '^GHCR_TOKEN=' app.env.new | cut -d= -f2- | docker login ghcr.io -u "$REGISTRY_USER" --password-stdin >/dev/null 2>&1 \
  || echo "ghcr.io login failed (is GHCR_TOKEN in SSM?)"
sed -i '/^GHCR_TOKEN=/d' app.env.new

docker pull -q "$IMAGE" >/dev/null 2>&1 || { echo "no image at $IMAGE yet"; rm -f app.env.new; exit 0; }
want="$(docker image inspect -f '{{.Id}}' "$IMAGE") $(sha256sum app.env.new | cut -c1-64)"
if [ -f running ] && [ "$(cat running)" = "$want" ] && [ -n "$(docker ps -q -f name=^app$)" ]; then
  rm -f app.env.new; exit 0  # nothing changed
fi
mv app.env.new app.env

docker network inspect web >/dev/null 2>&1 || docker network create web >/dev/null
docker rm -f app >/dev/null 2>&1 || true
docker run -d --name app --network web --restart unless-stopped --env-file app.env \
  -v agent-cache:/app/results -p 127.0.0.1:8000:8000 "$IMAGE" >/dev/null
if [ -z "$(docker ps -q -f name=^caddy$)" ]; then
  docker rm -f caddy >/dev/null 2>&1 || true
  docker run -d --name caddy --network web --restart unless-stopped -p 80:80 -p 443:443 -e DOMAIN="$DOMAIN" \
    -v /opt/app/Caddyfile:/etc/caddy/Caddyfile:ro -v caddy-data:/data caddy:2 >/dev/null
fi

for _ in $(seq 60); do  # wait until the app answers
  if curl -fsS -o /dev/null http://127.0.0.1:8000/; then
    echo "$want" > running
    docker image prune -f >/dev/null
    echo "deployed $(docker image inspect -f '{{index .RepoDigests 0}}' "$IMAGE") at https://$DOMAIN"; exit 0
  fi
  sleep 2
done
echo "the app did not start; last log lines:"; docker logs --tail 40 app; exit 1
