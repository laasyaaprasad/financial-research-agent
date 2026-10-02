"""Small SEC JSON client with a shared rate limit and explicit offline cache mode.

Only public response bodies are cached. User-Agent is read from the environment;
request headers, credentials and HTTP diagnostics are never persisted.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()


class EdgarError(RuntimeError):
    pass


class EdgarClient:
    _lock = threading.Lock()
    _last_request = 0.0

    def __init__(self, cache_dir: Path | str = "results/sec", *, offline: bool = False,
                 transport: httpx.BaseTransport | None = None, max_age_s: float = 86400):
        self.cache_dir = Path(cache_dir)
        self.offline = offline
        self.transport = transport
        self.max_age_s = max_age_s

    def get(self, url: str) -> dict:
        if not url.startswith(("https://www.sec.gov/", "https://data.sec.gov/")):
            raise EdgarError("Only SEC endpoints are permitted")
        path = self.cache_dir / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        if path.exists() and (self.offline or time.time() - path.stat().st_mtime < self.max_age_s):
            saved = json.loads(path.read_text())
            if saved["url"] != url:
                raise EdgarError("SEC cache URL mismatch")
            return saved["data"]
        if self.offline:
            raise EdgarError(f"No saved SEC response for {url}")
        user_agent = os.getenv("SEC_USER_AGENT")
        if not user_agent or "@" not in user_agent:
            raise EdgarError("Set SEC_USER_AGENT with contact email in .env")
        with httpx.Client(headers={"User-Agent": user_agent}, timeout=45,
                          transport=self.transport, follow_redirects=True) as client:
            for attempt in range(3):
                with self._lock:
                    wait = 0.15 - (time.monotonic() - self.__class__._last_request)
                    if wait > 0:
                        time.sleep(wait)
                    self.__class__._last_request = time.monotonic()
                try:
                    response = client.get(url)
                except httpx.TransportError:
                    if attempt == 2:
                        raise EdgarError("SEC transport failed after three attempts") from None
                    time.sleep(2 ** attempt)
                    continue
                if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                    try:
                        delay = float(response.headers.get("Retry-After", 2 ** attempt))
                    except ValueError:
                        delay = 2 ** attempt
                    time.sleep(max(0, min(delay, 10)))
                    continue
                if response.status_code != 200:
                    raise EdgarError(f"SEC returned HTTP {response.status_code}")
                data = response.json()
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"url": url, "data": data}))
                return data
        raise EdgarError("SEC request failed")

    def tickers(self) -> dict:
        return self.get("https://www.sec.gov/files/company_tickers.json")

    def submissions(self, cik: str) -> dict:
        return self.get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json")

    def companyfacts(self, cik: str) -> dict:
        return self.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json")


def filings(submissions: dict, today) -> list[dict]:
    """Recent filings available on the requested as-of date, including earnings 8-Ks."""
    recent = submissions.get("filings", {}).get("recent", {})
    rows = []
    for i, form in enumerate(recent.get("form", [])):
        row = {k: v[i] for k, v in recent.items() if isinstance(v, list) and i < len(v)}
        if row.get("filingDate", "9999") <= today.isoformat():
            rows.append(row)
    return rows
