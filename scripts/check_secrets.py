"""Scan submission files and local results without displaying secret values."""
import os
import re
import subprocess
from pathlib import Path
from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parent.parent

def main():
    load_dotenv(ROOT/'.env')
    secrets=[os.getenv(n) for n in ('TAVILY_API_KEY','NEBIUS_API_KEY','LANGFUSE_SECRET_KEY') if os.getenv(n)]
    output=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT)
    paths={ROOT/p.decode() for p in output.split(b'\0') if p}
    paths.update(p for p in (ROOT/'results').rglob('*') if p.is_file())
    leaks=[];count=0
    for p in paths:
        if p.name.startswith('.env') or not p.is_file(): continue
        text=p.read_text(errors='ignore');count+=1
        if any(secret in text for secret in secrets) or re.search(r'tvly-[A-Za-z0-9_-]{20,}',text):
            leaks.append(str(p.relative_to(ROOT)))
    print(f'Scanned {count} files; credential matches: {len(leaks)}')
    for p in sorted(leaks): print(p)
    return bool(leaks)

if __name__=='__main__': raise SystemExit(main())
