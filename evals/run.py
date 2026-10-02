"""Run an agent over the golden set, score it, and write a scorecard.

    uv run evals/run.py run --agent baseline --name baseline_r1
    uv run evals/run.py compare baseline_r1 baseline_r2
"""

from __future__ import annotations

import json
import random
import statistics
import traceback
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Annotated, Callable

import typer
from rich.console import Console

from evals.scorers import JUDGE_MODEL, _primary_hosts, score_row

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "evals" / "golden.jsonl"
RESULTS = ROOT / "results"

app = typer.Typer(add_completion=False)
console = Console()


def load_agent(name: str) -> Callable[[str], dict]:
    if name == "baseline":
        from agents.baseline import run
        return run
    raise typer.BadParameter(f"unknown agent: {name}")


def load_golden(ids: str | None) -> list[dict]:
    rows = [json.loads(line) for line in GOLDEN.read_text().splitlines() if line.strip()]
    if ids:
        wanted = set(ids.split(","))
        rows = [r for r in rows if r["id"] in wanted]
    return rows


def _pct(n: float, d: float) -> str:
    return f"{100 * n / d:.0f}%" if d else "n/a"


def summarize(records: list[dict]) -> dict:
    """Aggregate per-question records into scorecard metrics."""
    def agg(rs: list[dict]) -> dict:
        fixed = [r for r in rs if r["time_sensitivity"] == "static"]
        dyn = [r for r in rs if r["time_sensitivity"] == "dynamic"]
        c = [r["scores"]["citations"] for r in rs]
        s = [r["scores"]["sources"] for r in rs]
        return {
            "n": len(rs),
            "fixed_n": len(fixed),
            "fixed_correct": sum(r["scores"]["correctness"]["verdict"] == "correct" for r in fixed),
            "fixed_score": statistics.mean([r["scores"]["correctness"]["score"] for r in fixed]) if fixed else None,
            "dynamic_n": len(dyn),
            "dynamic_score": statistics.mean([r["scores"]["correctness"]["score"] for r in dyn]) if dyn else None,
            "numeric_claims": sum(x["numeric_claims"] for x in c),
            "numeric_cited": sum(x["numeric_cited"] for x in c),
            "cited_claims": sum(x["cited"] for x in c),
            "supported": sum(x["supported"] for x in c),
            "not_retrieved": sum(x["not_retrieved"] for x in c),
            "cited_urls": sum(len(x["cited_urls"]) for x in s),
            "cited_primary": sum(x["cited_primary"] for x in s),
            "errors": sum(1 for r in rs if r["output"].get("error")),
        }

    ok = [r for r in records if not r["output"].get("error")]
    lat = sorted(r["output"]["latency_s"] for r in ok)
    return {
        "overall": agg(records),
        "by_category": {k: agg(v) for k, v in sorted(_group(records, "category").items())},
        "by_difficulty": {k: agg(v) for k, v in _group(records, "difficulty").items()},
        "ops": {
            "latency_p50_s": statistics.median(lat) if lat else None,
            "latency_p95_s": lat[min(len(lat) - 1, int(0.95 * len(lat)))] if lat else None,
            "tokens_per_q": statistics.mean(r["output"]["tokens"]["input"] + r["output"]["tokens"]["output"] for r in ok) if ok else None,
            "credits_per_q": statistics.mean(r["output"]["tavily_credits"] for r in ok) if ok else None,
            "searches_per_q": statistics.mean(len(r["output"]["tool_calls"]) for r in ok) if ok else None,
        },
    }


def _group(records: list[dict], key: str) -> dict[str, list[dict]]:
    g = defaultdict(list)
    for r in records:
        g[r[key]].append(r)
    return g


def _row(label: str, a: dict) -> str:
    fixed = f"{a['fixed_correct']}/{a['fixed_n']} ({a['fixed_score']:.2f})" if a["fixed_n"] else "–"
    dyn = f"{a['dynamic_score']:.2f} (n={a['dynamic_n']})" if a["dynamic_n"] else "–"
    return (
        f"| {label} | {a['n']} | {fixed} | {dyn} | {_pct(a['numeric_cited'], a['numeric_claims'])} "
        f"| {_pct(a['supported'], a['cited_claims'])} | {_pct(a['cited_primary'], a['cited_urls'])} |"
    )


def write_scorecard(name: str, agent: str, summary: dict, records: list[dict]) -> Path:
    o, ops = summary["overall"], summary["ops"]
    head = "| Slice | Qs | Fixed: fully correct (mean score) | Time-sensitive: rubric score | Numbers with a citation | Cited claims supported | Cited URLs that are primary |\n|---|---|---|---|---|---|---|"
    lines = [
        f"# Scorecard: {name}",
        "",
        f"Agent: `{agent}` · Judge: `{JUDGE_MODEL}` · Questions: {o['n']} · Errors: {o['errors']}",
        "",
        "## Overall",
        "",
        head,
        _row("All", o),
        "",
        "## Operations (per question)",
        "",
        "| Median latency | p95 latency | Tokens | Tavily credits | Searches |",
        "|---|---|---|---|---|",
        f"| {ops['latency_p50_s']:.1f} s | {ops['latency_p95_s']:.1f} s | {ops['tokens_per_q']:,.0f} | {ops['credits_per_q']:.1f} | {ops['searches_per_q']:.1f} |",
        "",
        f"Cited claims whose URL the agent never retrieved: {o['not_retrieved']} of {o['cited_claims']}.",
        "",
        "## By category",
        "",
        head,
        *[_row(k, v) for k, v in summary["by_category"].items()],
        "",
        "## By difficulty",
        "",
        head,
        *[_row(k, summary["by_difficulty"][k]) for k in ("easy", "medium", "hard") if k in summary["by_difficulty"]],
        "",
        "## Per question",
        "",
        "| ID | Category | Verdict | Score | Credits | Latency | Judge rationale |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in sorted(records, key=lambda r: r["id"]):
        c = r["scores"]["correctness"]
        rationale = (r["output"].get("error") or c["rationale"]).replace("|", "/").replace("\n", " ")[:220]
        lines.append(
            f"| {r['id']} | {r['category']} | {c['verdict']} | {c['score']:.2f} | {r['output'].get('tavily_credits', 0)} "
            f"| {r['output'].get('latency_s', 0):.0f} s | {rationale} |"
        )
    path = RESULTS / f"scorecard_{name}.md"
    path.write_text("\n".join(lines) + "\n")
    return path


def write_judge_sample(name: str, records: list[dict], k: int = 10, seed: int = 7) -> Path:
    """Sample answers for the user to grade, to measure judge agreement."""
    fixed = [r for r in records if r["time_sensitivity"] == "static"]
    sample = random.Random(seed).sample(fixed, min(k, len(fixed)))
    out = [f"# Judge agreement sample: {name}", "", "For each, write your verdict (correct / partial / incorrect) next to **Your grade**.", ""]
    for r in sorted(sample, key=lambda r: r["id"]):
        c = r["scores"]["correctness"]
        out += [
            f"## {r['id']}: {r['question']}", "",
            f"**Grading rule:** {r['grading']}", "",
            f"**Reference:** {r['answer']}", "",
            f"**Agent answer:**\n\n> " + (r["output"].get("answer") or "(none)").replace("\n", "\n> "), "",
            f"**Judge:** {c['verdict']} ({c['score']:.2f}): {c['rationale']}", "",
            "**Your grade:** ", "",
        ]
    path = RESULTS / f"judge_sample_{name}.md"
    path.write_text("\n".join(out) + "\n")
    return path


@app.command()
def run(
    agent: Annotated[str, typer.Option(help="Agent to evaluate")] = "baseline",
    name: Annotated[str, typer.Option(help="Run name, used for output files")] = "baseline_r1",
    ids: Annotated[str | None, typer.Option(help="Comma-separated golden IDs (default: all)")] = None,
    workers: Annotated[int, typer.Option(help="Questions run in parallel")] = 4,
) -> None:
    """Run AGENT on the golden set, score every answer, and write the scorecard."""
    rows = load_golden(ids)
    agent_fn = load_agent(agent)
    primary_hosts = _primary_hosts(load_golden(None))
    raw_dir = RESULTS / "raw" / name
    raw_dir.mkdir(parents=True, exist_ok=True)

    def one(row: dict) -> dict:
        try:
            output = agent_fn(row["question"])
        except Exception as exc:
            output = {"answer": "", "tool_calls": [], "tool_results": [], "tokens": {"input": 0, "output": 0},
                      "tavily_credits": 0, "latency_s": 0.0, "error": f"{type(exc).__name__}: {exc}"[:500]}
        try:
            scores = score_row(row, output, primary_hosts)
        except Exception:
            raise RuntimeError(f"judge failed on {row['id']}:\n{traceback.format_exc()}")
        rec = {**{k: row[k] for k in ("id", "category", "difficulty", "time_sensitivity", "answer_type",
                                      "question", "grading", "answer")}, "output": output, "scores": scores}
        (raw_dir / f"{row['id']}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        return rec

    records = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(one, r): r["id"] for r in rows}
        for f in as_completed(futures):
            rec = f.result()
            records.append(rec)
            c = rec["scores"]["correctness"]
            console.print(f"{rec['id']}: {c['verdict']} ({c['score']:.2f}) · {rec['output'].get('latency_s', 0):.0f}s"
                          + (f" · ERROR {rec['output']['error'][:80]}" if rec["output"].get("error") else ""))

    summary = summarize(records)
    (RESULTS / f"summary_{name}.json").write_text(json.dumps(summary, indent=1))
    card = write_scorecard(name, agent, summary, records)
    sample = write_judge_sample(name, records)
    o = summary["overall"]
    console.print(f"\n[bold]{name}[/bold]: fixed {o['fixed_correct']}/{o['fixed_n']} correct · scorecard → {card.relative_to(ROOT)} · judge sample → {sample.relative_to(ROOT)}")


@app.command()
def rescore(source: str, name: str, workers: int = 4) -> None:
    """Re-judge a saved run's answers (no agent calls) to measure judge-only variation."""
    golden = {r["id"]: r for r in load_golden(None)}
    primary_hosts = _primary_hosts(list(golden.values()))
    raw_dir = RESULTS / "raw" / name
    raw_dir.mkdir(parents=True, exist_ok=True)
    saved = [json.loads(p.read_text()) for p in sorted((RESULTS / "raw" / source).glob("G*.json"))]

    def one(rec: dict) -> dict:
        rec = {**rec, "scores": score_row(golden[rec["id"]], rec["output"], primary_hosts)}
        (raw_dir / f"{rec['id']}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        return rec

    with ThreadPoolExecutor(max_workers=workers) as pool:
        records = list(pool.map(one, saved))
    summary = summarize(records)
    (RESULTS / f"summary_{name}.json").write_text(json.dumps(summary, indent=1))
    write_scorecard(name, f"rescore of {source}", summary, records)
    o = summary["overall"]
    console.print(f"{name}: fixed {o['fixed_correct']}/{o['fixed_n']} correct (re-judged {source})")


@app.command()
def compare(run_a: str, run_b: str) -> None:
    """Report run-to-run variation between two runs of the same agent."""
    def load(n):
        recs = {p.stem: json.loads(p.read_text()) for p in (RESULTS / "raw" / n).glob("G*.json")}
        return recs, json.loads((RESULTS / f"summary_{n}.json").read_text())
    ra, sa = load(run_a)
    rb, sb = load(run_b)
    common = sorted(set(ra) & set(rb))
    flips = [i for i in common if ra[i]["scores"]["correctness"]["verdict"] != rb[i]["scores"]["correctness"]["verdict"]]
    score_diff = [abs(ra[i]["scores"]["correctness"]["score"] - rb[i]["scores"]["correctness"]["score"]) for i in common]
    oa, ob = sa["overall"], sb["overall"]
    lines = [
        f"# Run-to-run variation: {run_a} vs {run_b}", "",
        "| Metric | " + run_a + " | " + run_b + " |", "|---|---|---|",
        f"| Fixed fully correct | {oa['fixed_correct']}/{oa['fixed_n']} | {ob['fixed_correct']}/{ob['fixed_n']} |",
        f"| Fixed mean score | {oa['fixed_score']:.3f} | {ob['fixed_score']:.3f} |",
        f"| Time-sensitive rubric score | {oa['dynamic_score']:.3f} | {ob['dynamic_score']:.3f} |",
        f"| Numbers with a citation | {_pct(oa['numeric_cited'], oa['numeric_claims'])} | {_pct(ob['numeric_cited'], ob['numeric_claims'])} |",
        f"| Cited claims supported | {_pct(oa['supported'], oa['cited_claims'])} | {_pct(ob['supported'], ob['cited_claims'])} |",
        f"| Cited URLs that are primary | {_pct(oa['cited_primary'], oa['cited_urls'])} | {_pct(ob['cited_primary'], ob['cited_urls'])} |",
        f"| Credits per question | {sa['ops']['credits_per_q']:.1f} | {sb['ops']['credits_per_q']:.1f} |",
        f"| Median latency | {sa['ops']['latency_p50_s']:.1f} s | {sb['ops']['latency_p50_s']:.1f} s |",
        "",
        f"Questions whose verdict changed between runs: {len(flips)} of {len(common)} ({', '.join(flips) or 'none'}).",
        f"Mean absolute per-question score difference: {statistics.mean(score_diff):.3f}.",
    ]
    path = RESULTS / f"variation_{run_a}_vs_{run_b}.md"
    path.write_text("\n".join(lines) + "\n")
    console.print("\n".join(lines))


if __name__ == "__main__":
    app()
