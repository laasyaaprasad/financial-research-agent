"""Check a traced eval run in Langfuse: one complete trace per question, no key material.

    uv run python scripts/verify_traces.py agent_v3_test_r1

Uses Langfuse's v2 observations API (the legacy trace endpoints are unavailable to new orgs).
Key values are compared in memory only and never printed.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
# LANGFUSE_PUBLIC_KEY is excluded: the Langfuse SDK itself stamps it on every span
# (scope.attributes.public_key) to identify the project; it is not a secret.
SECRET_VARS = ["TAVILY_API_KEY", "NEBIUS_API_KEY", "LANGFUSE_SECRET_KEY"]


def fetch_observations(host: str, auth: tuple[str, str], start: dt.datetime, end: dt.datetime) -> list[dict]:
    out, cursor = [], None
    while True:
        params = {"fromStartTime": start.isoformat(), "toStartTime": end.isoformat(), "limit": 1000,
                  "fields": "core,basic,io,usage,metadata"}
        if cursor:
            params["cursor"] = cursor
        r = httpx.get(f"{host}/api/public/v2/observations", params=params, auth=auth, timeout=60)
        r.raise_for_status()
        body = r.json()
        out += body.get("data", [])
        cursor = (body.get("meta") or {}).get("cursor")
        if not cursor:
            return out


def main(run_name: str) -> int:
    load_dotenv(ROOT / ".env")
    host = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL") or "https://us.cloud.langfuse.com"
    auth = (os.environ["LANGFUSE_PUBLIC_KEY"], os.environ["LANGFUSE_SECRET_KEY"])
    records = [json.loads(p.read_text()) for p in sorted((ROOT / "results" / "raw" / run_name).glob("G*.json"))]
    if not records:
        print(f"no records for {run_name}")
        return 1

    now = dt.datetime.now(dt.timezone.utc)
    obs = fetch_observations(host, auth, now - dt.timedelta(hours=6), now)
    by_trace = defaultdict(list)
    for o in obs:
        by_trace[o["traceId"]].append(o)

    secrets = [os.environ[v] for v in SECRET_VARS if os.getenv(v)]
    problems, leaks = [], 0
    for rec in records:
        tid, rid = rec["output"].get("trace_id"), rec["id"]
        spans = by_trace.get(tid, [])
        roots = [s for s in spans if s.get("isRootObservation")]
        gens = [s for s in spans if s["type"] == "GENERATION"]
        tools = [s for s in spans if s["type"] == "TOOL"]
        expected_tools = len(rec["output"].get("tool_calls") or [])
        if not tid or not spans:
            problems.append(f"{rid}: no trace found")
            continue
        if len(roots) != 1 or not roots[0]["name"].startswith("invoke_agent"):
            problems.append(f"{rid}: expected one invoke_agent root span, got {[r['name'] for r in roots]}")
        elif (roots[0].get("metadata") or {}).get("golden_id") != rid:
            problems.append(f"{rid}: root span not tagged with golden_id")
        if not gens or any(not (g.get("usageDetails") or {}).get("output") for g in gens):
            problems.append(f"{rid}: model calls missing or without token usage")
        if len(tools) != expected_tools:
            problems.append(f"{rid}: {len(tools)} tool spans vs {expected_tools} tool calls")
        blob = json.dumps(spans, default=str)
        if any(s in blob for s in secrets) or re.search(r"tvly-[A-Za-z0-9]{8,}", blob):
            leaks += 1
            problems.append(f"{rid}: KEY MATERIAL IN TRACE")

    n = len(records)
    print(f"{run_name}: {n} questions, {n - len({p.split(':')[0] for p in problems})} with complete traces")
    print(f"traces containing key material: {leaks}")
    for p in problems:
        print("  -", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
