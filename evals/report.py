"""Build the results tables from saved runs, and export compact per-question records.

    uv run python -m evals.report baseline_test_r1,baseline_test_r2 agent_v3_test_r1,agent_v3_test_r2 ...
    uv run python -m evals.report --export baseline_test_r1 agent_v3_test_r1 ...
    uv run python -m evals.report --final > results/final/results.md
    uv run python -m evals.report --exact50 > results/final/exact50.md

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


# Exact50 (2026-10-05): column -> its runs (the first three were run in two halves of 25). Judge: GPT-6 Luna, 3 votes.
EXACT50 = {
    "Starter (as shipped, Kimi K2.6)": ["half_starter_exact50", "half2_starter_exact50"],
    "Starter design on our model": ["half_baseline_exact50", "half2_baseline_exact50"],
    "Our agent, first version": ["half_agent_exact50", "half2_agent_exact50"],
    "Our agent, final": ["x50v2_agent"],
}


def _exact50_class(qid: str) -> str:
    if qid[0] in "EW":
        return {"E": "Edge and ambiguous", "W": "Web-dependent"}[qid[0]]
    return ("Actual vs. guidance" if qid in ("T11", "T12", "H17", "H18") else
            "Comparison across fiscal calendars" if qid in ("T20", "X01", "X03", "X04") else "Trap")


def exact50_report() -> str:
    from evals.run import load_set
    order = [r["id"] for r in load_set("exact50")]
    recs = {col: {r["id"]: r for run in runs for r in load(run)} for col, runs in EXACT50.items()}

    def cited(r):
        c = r["scores"]["citations"]
        return c["supported"], c["cited"] - c.get("undecided", 0)

    def verified(r):
        s, d = cited(r)
        c = r["scores"]["citations"]
        return r["scores"]["correctness"]["verdict"] == "correct" and s == d and c["numeric_cited"] == c["numeric_claims"]

    rows = [
        ("Fully correct", lambda rs: f"{sum(r['scores']['correctness']['verdict'] == 'correct' for r in rs)}/{len(rs)}"),
        ("Mean rubric score", lambda rs: f"{statistics.mean(r['scores']['correctness']['score'] for r in rs):.2f}"),
        ("Verified-correct (correct, every cited claim supported, every number cited)",
         lambda rs: f"{sum(verified(r) for r in rs)}/{len(rs)}"),
        ("Cited claims supported by the cited source", lambda rs: (lambda s, d: f"{s}/{d} ({100 * s / max(1, d):.0f}%)")(
            sum(cited(r)[0] for r in rs), sum(cited(r)[1] for r in rs))),
        ("Cited URLs that are primary (SEC / company)", lambda rs: (lambda p, u: f"{100 * p / max(1, u):.0f}%")(
            sum(r["scores"]["sources"]["cited_primary"] for r in rs), sum(len(r["scores"]["sources"]["cited_urls"]) for r in rs))),
        ("Tavily credits (total)", lambda rs: f"{sum(r['output'].get('tavily_credits') or 0 for r in rs):g}"),
        ("Tokens per question", lambda rs: f"{statistics.mean(sum((r['output'].get('tokens') or {}).values()) for r in rs):,.0f}"),
        ("Median latency", lambda rs: f"{statistics.median(r['output']['latency_s'] for r in rs):.0f} s"),
        ("Judge errors / agent errors", lambda rs: f"{sum(bool(r['scores']['correctness'].get('judge_error')) for r in rs)} / "
                                                   f"{sum(bool(r['output'].get('error')) for r in rs)}"),
    ]
    classes = list(dict.fromkeys(_exact50_class(i) for i in order))
    head = "| Measure | " + " | ".join(EXACT50) + " |\n|---|" + "---|" * len(EXACT50)
    out = ["# Exact50 results", "",
           "Generated by `uv run python -m evals.report --exact50` from the run records (kept out of git; per-question "
           "verdicts, judge rationales and trace links are in `scorecards/`). Exact50 is 50 held-out "
           "questions chosen by fixed rules (`evals/exact50_selection.md`). Every answer was graded by `gpt-6-luna` (OpenAI, "
           "high reasoning; 8 of 10 agreement with the user's grades) with three votes; the median verdict counts. Each "
           "column is one fresh run of every question.", "", "## Summary", "", head]
    out += [f"| {label} | " + " | ".join(f(list(recs[c].values())) for c in EXACT50) + " |" for label, f in rows]
    out += ["", "## Fully correct by question class", "", head]
    for k in classes:
        ids = [i for i in order if _exact50_class(i) == k]
        out.append(f"| {k} ({len(ids)}) | " + " | ".join(
            str(sum(recs[c][i]["scores"]["correctness"]["verdict"] == "correct" for i in ids if i in recs[c])) for c in EXACT50) + " |")
    out += ["", "## Per question (verdict and rubric score)", "", "| Question | Class | " + " | ".join(EXACT50) + " |",
            "|---|---|" + "---|" * len(EXACT50)]
    for i in order:
        cells = [(lambda c: f"{c['verdict']} {c['score']:.2f}")(recs[col][i]["scores"]["correctness"]) if i in recs[col] else "–"
                 for col in EXACT50]
        out.append(f"| {i} | {_exact50_class(i)} | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def recall(run: str) -> tuple[int, int]:
    """Reference figures found in retrieved text, summed over a run (computed from full local records)."""
    from evals.scorers import evidence_recall, retrieved_index
    from evals.run import SETS, load_set
    rows = {r["id"]: r for name in SETS for r in load_set(name)}
    figures = found = 0
    for rec in load(run):
        r = evidence_recall(rows[rec["id"]], retrieved_index(rec["output"].get("tool_results") or []))
        figures, found = figures + r["figures"], found + r["found"]
    return found, figures


if __name__ == "__main__":
    if sys.argv[1] == "--recall":
        for run in sys.argv[2:]:
            found, figures = recall(run)
            print(f"{run}: {found}/{figures} reference figures in retrieved text ({100 * found / max(1, figures):.0f}%)")
        sys.exit()
    if sys.argv[1] == "--final":
        print(final_report())
        sys.exit()
    if sys.argv[1] == "--exact50":
        print(exact50_report(), end="")
        sys.exit()
    elif sys.argv[1] == "--export":
        for run in sys.argv[2:]:
            export(run)
    else:
        print(table(sys.argv[1:]))
