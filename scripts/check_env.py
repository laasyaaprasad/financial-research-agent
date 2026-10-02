"""Report whether each required key is set in .env. Prints presence only, never values."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

REQUIRED = ["TAVILY_API_KEY", "NEBIUS_API_KEY", "SEC_USER_AGENT"]
OPTIONAL = ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"]  # tracing


def main() -> int:
    load_dotenv()
    missing = 0
    for name in REQUIRED:
        present = bool(os.getenv(name))
        missing += not present
        print(f"{name}: {'present' if present else 'missing'}")
    for name in OPTIONAL:
        print(f"{name} (optional, tracing): {'present' if os.getenv(name) else 'missing'}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
