#!/bin/bash
# First boot: Docker, 1 GB of swap (the instance has 1 GB of RAM), the app's files, and a systemd timer that runs
# deploy.sh every 2 minutes (it starts the app once the image and the secrets exist, and restarts it when they change).
set -euxo pipefail
dnf install -y docker
systemctl enable --now docker
if [ ! -f /swapfile ]; then
  fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  echo '/swapfile swap swap defaults 0 0' >> /etc/fstab
fi
mkdir -p /opt/app
cat > /opt/app/Caddyfile <<'CADDYFILE'
${caddyfile}
CADDYFILE
cat > /opt/app/deploy.sh <<'DEPLOY'
${deploy_sh}
DEPLOY
chmod 700 /opt/app/deploy.sh

cat > /etc/systemd/system/app-deploy.service <<'UNIT'
[Unit]
Description=Pull the latest app image and restart the app if it changed
After=docker.service
Requires=docker.service
[Service]
Type=oneshot
ExecStart=/opt/app/deploy.sh
UNIT
cat > /etc/systemd/system/app-deploy.timer <<'UNIT'
[Unit]
Description=Check for a new app image every 2 minutes
[Timer]
OnBootSec=30s
OnUnitInactiveSec=2min
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now app-deploy.timer
