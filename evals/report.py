"""Build the results table for the README from saved runs.

    uv run python -m evals.report baseline_test_r1,baseline_test_r2 agent_v2_test_r1,agent_v2_test_r2 ...

Each argument is a comma-separated group of runs (e.g. repeated runs of one agent on one set);
metrics are pooled over the group. A cited claim counts as supported only if the judge confirmed
it against text the agent retrieved. "Verified-correct" means fully correct AND every cited claim
supported AND every number cited: an answer an analyst can use without re-checking it.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "results" / "raw"


def load(run: str) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted((RAW / run).glob("[GT][0-9]*.json"))]


def group_metrics(runs: list[str]) -> dict:
    recs = [r for run in runs for r in load(run)]
    fixed = [r for r in recs if r["time_sensitivity"] == "static"]
    dyn = [r for r in recs if r["time_sensitivity"] == "dynamic"]
    cit = [r["scores"]["citations"] for r in recs]

    def verified(r):
        c = r["scores"]["citations"]
        return (r["scores"]["correctness"]["verdict"] == "correct" and c["supported"] == c["cited"]
                and c["numeric_cited"] == c["numeric_claims"])

    ok = [r for r in recs if not r["output"].get("error")]
    cited = sum(c["cited"] for c in cit)
    unsupported = cited - sum(c["supported"] for c in cit)
    urls = sum(len(r["scores"]["sources"]["cited_urls"]) for r in recs)
    primary = sum(r["scores"]["sources"]["cited_primary"] for r in recs)
    lat = sorted(r["output"]["latency_s"] for r in ok)
    return {
        "runs": len(runs), "questions": len(recs),
        "fixed_correct": sum(r["scores"]["correctness"]["verdict"] == "correct" for r in fixed), "fixed_n": len(fixed),
        "fixed_mean": statistics.mean(r["scores"]["correctness"]["score"] for r in fixed) if fixed else None,
        "dynamic_mean": statistics.mean(r["scores"]["correctness"]["score"] for r in dyn) if dyn else None,
        "verified_correct": sum(verified(r) for r in fixed),
        "unsupported": unsupported, "cited": cited,
        "primary": primary, "urls": urls,
        "credits": sum(r["output"].get("tavily_credits", 0) for r in recs),
        "credits_per_q": statistics.mean(r["output"].get("tavily_credits", 0) for r in recs),
        "tokens_per_q": statistics.mean(r["output"]["tokens"]["input"] + r["output"]["tokens"]["output"] for r in ok),
        "latency_p50": statistics.median(lat), "latency_p95": lat[min(len(lat) - 1, int(0.95 * len(lat)))],
        "errors": len(recs) - len(ok),
    }


def table(groups: list[str]) -> str:
    rows = [("Runs", lambda m: str(m["runs"])),
            ("Fixed answers fully correct", lambda m: f"{m['fixed_correct']}/{m['fixed_n']} ({m['fixed_mean']:.2f})"),
            ("Verified-correct (correct, every cited claim supported, every number cited)",
             lambda m: f"{m['verified_correct']}/{m['fixed_n']}"),
            ("Time-sensitive rubric score", lambda m: f"{m['dynamic_mean']:.2f}" if m["dynamic_mean"] is not None else "–"),
            ("Cited claims not supported by retrieved text", lambda m: f"{m['unsupported']}/{m['cited']} ({100 * m['unsupported'] / max(1, m['cited']):.0f}%)"),
            ("Cited URLs that are primary (SEC / company)", lambda m: f"{100 * m['primary'] / max(1, m['urls']):.0f}%"),
            ("Tavily credits per question", lambda m: f"{m['credits_per_q']:.1f}"),
            ("Tokens per question", lambda m: f"{m['tokens_per_q']:,.0f}"),
            ("Median / p95 latency", lambda m: f"{m['latency_p50']:.0f} s / {m['latency_p95']:.0f} s"),
            ("Agent errors", lambda m: str(m["errors"]))]
    metrics = [group_metrics(g.split(",")) for g in groups]
    out = ["| Metric | " + " | ".join(groups) + " |", "|---|" + "---|" * len(groups)]
    out += [f"| {label} | " + " | ".join(f(m) for m in metrics) + " |" for label, f in rows]
    return "\n".join(out)


if __name__ == "__main__":
    print(table(sys.argv[1:]))
