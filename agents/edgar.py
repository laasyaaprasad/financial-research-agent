"""SEC EDGAR access: JSON APIs and filing documents, rate-limited and cached on disk.

The User-Agent comes from SEC_USER_AGENT in the environment. Only public response
bodies are cached; request headers are never written to disk.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from html.parser import HTMLParser
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

ARCHIVES = "https://www.sec.gov/Archives/edgar/data"


class EdgarError(RuntimeError):
    pass


class EdgarClient:
    _lock = threading.Lock()
    _last_request = 0.0
    MIN_INTERVAL_S = 0.15  # SEC fair-access limit is 10 requests/second

    def __init__(self, cache_dir: Path | str = "results/sec", *, offline: bool = False, json_max_age_s: float = 6 * 3600):
        self.cache_dir = Path(cache_dir)
        self.offline = offline
        self.json_max_age_s = json_max_age_s  # submissions/companyfacts change as companies file

    # ---------- transport ----------

    def _fetch(self, url: str, kind: str) -> str:
        if not url.startswith(("https://www.sec.gov/", "https://data.sec.gov/")):
            raise EdgarError("Only SEC endpoints are permitted")
        path = self.cache_dir / kind / (hashlib.sha256(url.encode()).hexdigest() + ".txt")
        fresh = kind != "json" or time.time() - path.stat().st_mtime < self.json_max_age_s if path.exists() else False
        if path.exists() and (fresh or self.offline):
            return path.read_text()  # filing documents and indexes never change; API data expires
        if self.offline:
            raise EdgarError(f"No cached SEC response for {url}")
        user_agent = os.getenv("SEC_USER_AGENT")
        if not user_agent:
            raise EdgarError("Set SEC_USER_AGENT (name and contact email) in .env")
        for attempt in range(3):
            self._throttle()
            try:
                response = httpx.get(url, headers={"User-Agent": user_agent}, timeout=45, follow_redirects=True)
            except httpx.TransportError:
                time.sleep(2 ** attempt)
                continue
            if response.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            if response.status_code != 200:
                raise EdgarError(f"SEC returned HTTP {response.status_code} for {url}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(response.text)
            return response.text
        raise EdgarError(f"SEC request failed after retries: {url}")

    @classmethod
    def _throttle(cls) -> None:
        with cls._lock:
            wait = cls.MIN_INTERVAL_S - (time.monotonic() - cls._last_request)
            if wait > 0:
                time.sleep(wait)
            cls._last_request = time.monotonic()

    def json(self, url: str) -> dict:
        return json.loads(self._fetch(url, "json"))

    # ---------- APIs ----------

    def tickers(self) -> dict:
        return self.json("https://www.sec.gov/files/company_tickers.json")

    def submissions(self, cik: str) -> dict:
        return self.json(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json")

    def companyfacts(self, cik: str) -> dict:
        try:
            return self.json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json")
        except EdgarError:
            return {"facts": {}}  # some registrants file no XBRL financial data

    def exhibits(self, cik: str, accession: str) -> list[dict]:
        """Documents in a filing with their declared types (e.g. EX-99.1), from the filing index page."""
        acc = accession.replace("-", "")
        page = self._fetch(f"{ARCHIVES}/{int(cik)}/{acc}/{accession}-index.htm", "index")
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", page, flags=re.S | re.I)
        docs = []
        for row in rows:
            cells = [re.sub(r"<[^>]+>", " ", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S | re.I)]
            link = re.search(r'href="([^"]+)"', row)
            if len(cells) >= 4 and link:
                href = link.group(1).replace("/ix?doc=", "")
                docs.append({"description": cells[1], "type": cells[3],
                             "url": "https://www.sec.gov" + href if href.startswith("/") else href})
        return docs

    def text(self, url: str) -> str:
        """Plain text of a filing document. Table cells are separated by ' | ', one row per line."""
        return html_to_text(self._fetch(url, "documents"))


class _TextParser(HTMLParser):
    BLOCKS = {"p", "div", "br", "tr", "h1", "h2", "h3", "h4", "li", "table"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "ix:header"):
            self.skip += 1
        elif not self.skip and tag in self.BLOCKS:
            self.parts.append("\n")
        elif not self.skip and tag in ("td", "th"):
            self.parts.append(" | ")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "ix:header") and self.skip:
            self.skip -= 1
        elif not self.skip and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextParser()
    parser.feed(html)
    lines = []
    for line in "".join(parser.parts).splitlines():
        line = re.sub(r"[ \t\xa0]+", " ", line).strip()
        line = re.sub(r"(\|\s*)+\|", "|", line).strip(" |")  # collapse empty table cells
        if line:
            lines.append(line)
    return "\n".join(lines)
