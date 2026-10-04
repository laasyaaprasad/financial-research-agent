"""Build the results tables from saved runs, and export compact per-question records.

    uv run python -m evals.report baseline_test_r1,baseline_test_r2 agent_v3_test_r1,agent_v3_test_r2 ...
    uv run python -m evals.report --export baseline_test_r1 agent_v3_test_r1 ...
    uv run python -m evals.report --final > results/final/results.md

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

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "results" / "raw"                   # full local records (git-ignored)
RECORDS = ROOT / "results" / "final" / "records"  # committed compact records


def load(run: str) -> list[dict]:
    folder = RAW / run if (RAW / run).exists() else RECORDS / run
    return [json.loads(p.read_text()) for p in sorted(folder.glob("[GTHDXEW][0-9]*.json"))]


def export(run: str) -> None:
    """Keep everything the report and a reader need; drop the retrieved evidence text."""
    out = RECORDS / run
    out.mkdir(parents=True, exist_ok=True)
    for rec in load(run):
        o = rec["output"]
        compact = {k: o.get(k) for k in ("answer", "tokens", "tavily_credits", "latency_s", "model", "error",
                                         "trace_url", "companies", "plan", "unavailable", "removed", "assumptions",
                                         "out_of_scope", "clarification")}
        compact["tool_calls"] = [{"name": c.get("name"), "args": c.get("args")} for c in o.get("tool_calls") or []]
        (out / f"{rec['id']}.json").write_text(json.dumps({**rec, "output": compact}, indent=1, ensure_ascii=False))


def group_metrics(runs: list[str]) -> dict:
    recs = [r for run in runs for r in load(run)]
    fixed = [r for r in recs if r["time_sensitivity"] == "static"]
    dyn = [r for r in recs if r["time_sensitivity"] == "dynamic"]
    cit = [r["scores"]["citations"] for r in recs]

    def undecided(c):  # claims the citation judge left undecided although their source was retrieved
        return c.get("undecided", sum(1 for x in c.get("claims", []) if x.get("in_retrieved") and x.get("supported") is None))

    def verified(r):
        c = r["scores"]["citations"]
        return (r["scores"]["correctness"]["verdict"] == "correct" and c["supported"] == c["cited"] - undecided(c)
                and c["numeric_cited"] == c["numeric_claims"])

    ok = [r for r in recs if not r["output"].get("error")]
    cited = sum(c["cited"] - undecided(c) for c in cit)
    unsupported = cited - sum(c["supported"] for c in cit)
    urls = sum(len(r["scores"]["sources"]["cited_urls"]) for r in recs)
    primary = sum(r["scores"]["sources"]["cited_primary"] for r in recs)
    lat = sorted(r["output"]["latency_s"] for r in ok)
    return {
        "runs": len(runs), "questions": len(recs),
        "fixed_correct": sum(r["scores"]["correctness"]["verdict"] == "correct" for r in fixed), "fixed_n": len(fixed),
        "fixed_mean": statistics.mean(r["scores"]["correctness"]["score"] for r in fixed) if fixed else None,
        "dynamic_mean": statistics.mean(r["scores"]["correctness"]["score"] for r in dyn) if dyn else None,
        "dynamic_correct": sum(r["scores"]["correctness"]["verdict"] == "correct" for r in dyn), "dynamic_n": len(dyn),
        "verified_correct": sum(verified(r) for r in fixed),
        "cells_correct": sum(r["scores"]["correctness"].get("cells_correct", 0) for r in recs),
        "cells_total": sum(r["scores"]["correctness"].get("cells_total", 0) for r in recs),
        "unsupported": unsupported, "cited": cited, "undecided": sum(undecided(c) for c in cit),
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
            ("Table cells correct", lambda m: f"{m['cells_correct']}/{m['cells_total']} ({100 * m['cells_correct'] / m['cells_total']:.0f}%)" if m["cells_total"] else "–"),
            ("Verified-correct (correct, every cited claim supported, every number cited)",
             lambda m: f"{m['verified_correct']}/{m['fixed_n']}"),
            ("Time-sensitive rubric score", lambda m: f"{m['dynamic_mean']:.2f}" if m["dynamic_mean"] is not None else "–"),
            ("Cited claims not supported by retrieved text", lambda m: f"{m['unsupported']}/{m['cited']} ({100 * m['unsupported'] / max(1, m['cited']):.0f}%)"),
            ("Cited claims the checker left undecided (excluded above)", lambda m: str(m["undecided"])),
            ("Cited URLs that are primary (SEC / company)", lambda m: f"{100 * m['primary'] / max(1, m['urls']):.0f}%"),
            ("Tavily credits per question", lambda m: f"{m['credits_per_q']:.1f}"),
            ("Tokens per question", lambda m: f"{m['tokens_per_q']:,.0f}"),
            ("Median / p95 latency", lambda m: f"{m['latency_p50']:.0f} s / {m['latency_p95']:.0f} s"),
            ("Agent errors", lambda m: str(m["errors"]))]
    metrics = [group_metrics(g.split(",")) for g in groups]
    out = ["| Metric | " + " | ".join(groups) + " |", "|---|" + "---|" * len(groups)]
    out += [f"| {label} | " + " | ".join(f(m) for m in metrics) + " |" for label, f in rows]
    return "\n".join(out)


# The final evaluation: (heading, starter as shipped, starter design on our model, our agent).
SETS = {
    "test": ("starter_test_r1,starter_test_r2", "baseline_test_r1,baseline_test_r2", "agent_v3_test_r1,agent_v3_test_r2"),
    "hard": ("starter_hard_r1,starter_hard_r2", "baseline_hard_r1,baseline_hard_r2", "agent_v3_hard_r1,agent_v3_hard_r2"),
    "tables": (None, "baseline_tables_r1_g,baseline_tables_r2_g", "agent_tables_r1_g,agent_tables_r2_g"),
    "dev": ("starter_dev_r1,starter_dev_r2,starter_dev_r3", "baseline_dev", "agent_v3_dev"),
}
FINAL = [
    ("Held-out sets 1 and 2 pooled (the as-shipped starter was not run on the table set; see note)",
     *(",".join(SETS[k][i] for k in ("test", "hard")) for i in range(3))),
    ("All held-out sets pooled, same-model comparison", None,
     *(",".join(SETS[k][i] for k in ("test", "hard", "tables")) for i in (1, 2))),
    ("Held-out set 1: 20 questions, 21 companies (`evals/test_heldout.jsonl`)", *SETS["test"]),
    ("Held-out set 2, hard: point-in-time, filing-only, multi-step fiscal, traps (`evals/test_hard.jsonl`)", *SETS["hard"]),
    ("Held-out set 3: analyst tables, 8 tasks, 86 cells (`evals/test_tables.jsonl`)", *SETS["tables"]),
    ("Dev set: 30 questions, inspected during development (`evals/golden.jsonl`)", *SETS["dev"]),
]

HEADER = """# Final results

Generated by `uv run python -m evals.report --final` from the per-question records in `records/`.

- **Starter (as shipped):** the provided starter agent unchanged, including its default model `moonshotai/Kimi-K2.6`. This is the baseline.
- **Starter design on our model:** the same prompt, Tavily tool and agent loop on `deepseek-ai/DeepSeek-V4.1-Flash`. It isolates what the architecture contributes, as distinct from the model choice.
- **Our agent:** `agents/pipeline.py` (v3) on `deepseek-ai/DeepSeek-V4.1-Flash`; the model choice is part of the solution.
- **Judge:** `nvidia/Nemotron-3-Ultra-550b-a55b` for every run, including re-graded early runs. Table tasks are graded cell by cell: the judge only extracts values, and code compares them to the reference.
- **Runs:**
  - our agent and the same-model starter: two runs per held-out set
  - the as-shipped starter: two runs on held-out sets 1 and 2, and three dev runs (its original M1/M2 runs, re-graded). It was not run on the table set: it averaged 13.5 Tavily credits per hard question, and a table run would have exceeded the 1,500-credit budget
  - `_g` table runs are the same answers re-graded with the fixed label grader
- **Verified-correct:** fully correct AND every cited claim supported by text the agent retrieved AND every number cited.
"""

COLUMNS = "| Metric | Starter (as shipped) | Starter design on our model | Our agent |"


# M7, ambiguous and incomplete questions: (heading, [(column, run), ...]). Graded with three judge votes.
EDGE = [
    ("Held-out: 16 questions (`evals/test_edge.jsonl`)",
     [("Before M7, web off", "edge_before_test_j3"), ("After M7, web off", "edge_after_test"),
      ("After M7, web on", "edge_live_test")]),
    ("Dev: 24 questions (`evals/edge_dev.jsonl`)",
     [("Before M7, web off", "edge_before_dev_j3"), ("After M7, web off", "edge_after_dev_j3"),
      ("After M7, web on", "edge_live_dev")]),
]


def edge_table(columns: list[tuple[str, str]]) -> str:
    rows = [("Questions meeting every rubric point", lambda m: f"{m['dynamic_correct']}/{m['dynamic_n']}"),
            ("Mean rubric score", lambda m: f"{m['dynamic_mean']:.2f}"),
            ("Cited claims not supported by retrieved text", lambda m: f"{m['unsupported']}/{m['cited']}"),
            ("Tavily credits per question", lambda m: f"{m['credits_per_q']:.1f}"),
            ("Tokens per question", lambda m: f"{m['tokens_per_q']:,.0f}")]
    metrics = [group_metrics([run]) for _, run in columns]
    out = ["| Metric | " + " | ".join(label for label, _ in columns) + " |", "|---|" + "---|" * len(columns)]
    return "\n".join(out + [f"| {label} | " + " | ".join(f(m) for m in metrics) + " |" for label, f in rows])


def final_report() -> str:
    parts = [HEADER]
    for heading, *groups in FINAL:
        present = [g for g in groups if g]
        rows = table(present).splitlines()
        if len(present) == len(groups):
            rows[0], rows[1] = COLUMNS, "|---|---|---|---|"
        else:
            rows[0], rows[1] = "| Metric | Starter design on our model | Our agent |", "|---|---|---|"
        parts += [f"## {heading}", "", "\n".join(rows), ""]
    parts += ["## Ambiguous and incomplete questions (M7)", "",
              "Our agent before and after the M7 changes. Graded three times against behaviour rubrics (answer with a "
              "stated interpretation, ask a clarifying question, decline the out-of-scope part, or say the figure "
              "can't exist yet); the median verdict counts. Latency isn't compared: these runs shared the model "
              "provider with other jobs.", ""]
    for heading, columns in EDGE:
        present = [(label, run) for label, run in columns if load(run)]
        if present:
            parts += [f"### {heading}", "", edge_table(present), ""]
    return "\n".join(parts)


if __name__ == "__main__":
    if sys.argv[1] == "--final":
        print(final_report())
        sys.exit()
    elif sys.argv[1] == "--export":
        for run in sys.argv[2:]:
            export(run)
    else:
        print(table(sys.argv[1:]))
