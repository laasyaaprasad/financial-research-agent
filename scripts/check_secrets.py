"""Scan repository files and local results for API key material, without printing any value.

    uv run python scripts/check_secrets.py
"""

import os
import re
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
SECRET_VARS = ("TAVILY_API_KEY", "NEBIUS_API_KEY", "LANGFUSE_SECRET_KEY")


def main() -> int:
    load_dotenv(ROOT / ".env")
    secrets = [os.environ[v] for v in SECRET_VARS if os.getenv(v)]
    listed = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT)
    paths = {ROOT / p.decode() for p in listed.split(b"\0") if p}
    paths |= {p for p in (ROOT / "results").rglob("*") if p.is_file()}
    leaks = []
    for path in paths:
        if path.name.startswith(".env") or not path.is_file():
            continue
        text = path.read_text(errors="ignore")
        if any(s in text for s in secrets) or re.search(r"tvly-[A-Za-z0-9_-]{20,}", text):
            leaks.append(path.relative_to(ROOT))
    print(f"Scanned {len(paths)} files; files containing key material: {len(leaks)}")
    for path in sorted(leaks):
        print(f"  {path}")
    return 1 if leaks else 0


if __name__ == "__main__":
    sys.exit(main())
