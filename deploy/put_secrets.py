"""Copy the app's secrets from .env into SSM Parameter Store (SecureString), where the instance reads them.

    uv run --with boto3 deploy/put_secrets.py

Values are read programmatically and never printed. CHAINLIT_AUTH_SECRET (signs sign-in sessions) is generated once.
"""

import os
import secrets
from pathlib import Path

import boto3
from dotenv import dotenv_values, find_dotenv

PATH = "/fin-research-agent"
KEYS = ["NEBIUS_API_KEY", "TAVILY_API_KEY", "SEC_USER_AGENT", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY",
        "LANGFUSE_BASE_URL", "APP_PASSWORD"]
GENERATED = {"CHAINLIT_AUTH_SECRET": lambda: secrets.token_urlsafe(48)}

# DOTENV_PATH, else the nearest .env from the current directory upward (so it works from the repo root or a worktree).
dotenv_path = os.getenv("DOTENV_PATH") or find_dotenv(usecwd=True)
if not dotenv_path or not Path(dotenv_path).is_file():
    raise SystemExit("No .env found: run this from the repo, or set DOTENV_PATH.")
env = dotenv_values(dotenv_path)
ssm = boto3.client("ssm", region_name="us-east-2")
existing = {p["Name"].rsplit("/", 1)[1] for page in ssm.get_paginator("get_parameters_by_path").paginate(Path=PATH)
            for p in page["Parameters"]}

for name in KEYS + ["CHAINLIT_AUTH_SECRET"]:
    value = env.get(name)
    if not value and name in GENERATED:
        if name in existing:
            print(f"kept      {name}")
            continue
        value = GENERATED[name]()
    if not value:
        print(f"missing   {name} (not in .env)")
        continue
    ssm.put_parameter(Name=f"{PATH}/{name}", Value=value, Type="SecureString", Overwrite=True)
    print(f"uploaded  {name}")
print("The instance picks up changes within 2 minutes (it restarts the app when the secrets change).")
