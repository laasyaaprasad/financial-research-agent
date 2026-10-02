"""Save public SEC calendar inputs for offline tests (no golden answers are used).

Keep registrant metadata, recent filing dates and deduplicated XBRL duration
contexts. Numeric values are omitted: this milestone only needs period boundaries.
Run again deliberately to update the pinned fixture snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from agents.edgar import EdgarClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tickers", nargs="+")
    parser.add_argument("--output", type=Path, default=Path("tests/fixtures/edgar"))
    args = parser.parse_args()
    client = EdgarClient()
    entries = client.tickers()
    wanted = {t.upper() for t in args.tickers}
    selected = {k: v for k, v in entries.items() if v["ticker"] in wanted}
    missing = wanted - {v["ticker"] for v in selected.values()}
    if missing:
        raise SystemExit(f"Unknown SEC tickers: {sorted(missing)}")
    urls = []

    def save(url, data):
        args.output.mkdir(parents=True, exist_ok=True)
        name = hashlib.sha256(url.encode()).hexdigest() + ".json"
        (args.output / name).write_text(json.dumps({"url": url, "data": data}, indent=2) + "\n")
        urls.append(url)

    save("https://www.sec.gov/files/company_tickers.json", selected)
    for cik in sorted({str(v["cik_str"]) for v in selected.values()}):
        sub = client.submissions(cik)
        keep = {k: sub.get(k) for k in ("cik", "name", "tickers", "fiscalYearEnd", "formerNames")}
        recent = sub["filings"]["recent"]
        keys = ("accessionNumber", "filingDate", "reportDate", "form", "primaryDocument", "items")
        indices = [i for i, form in enumerate(recent["form"])
                   if form in ("10-K", "10-Q", "8-K", "20-F", "40-F", "6-K")
                   and recent["filingDate"][i] >= "2022-01-01"]
        keep["filings"] = {"recent": {k: [recent[k][i] for i in indices] for k in keys}, "files": []}
        save(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", keep)
        facts = client.companyfacts(cik)
        contexts = {}
        for namespace in facts.get("facts", {}).values():
            for concept in namespace.values():
                for unit in concept.get("units", {}).values():
                    for f in unit:
                        if not f.get("start") or f.get("end", "") < "2022-01-01":
                            continue
                        context = {k: f[k] for k in ("start", "end", "accn", "fy", "fp", "form", "filed") if k in f}
                        contexts[json.dumps(context, sort_keys=True)] = context
        data = {"cik": facts["cik"], "entityName": facts.get("entityName"),
                "facts": {"calendar-contexts": {"Durations": {"units": {"contexts": list(contexts.values())}}}}}
        save(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json", data)
        print(sub["name"], 'saved')
    (args.output / "manifest.json").write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(), "urls": urls,
        "projection": "Public registrant metadata, recent filing dates and XBRL duration contexts; numeric values omitted. No golden set inputs."
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
