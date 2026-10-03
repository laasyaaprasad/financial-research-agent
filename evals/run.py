"""Run an agent over a question set, score every answer, and write a scorecard.

    uv run python -m evals.run run --agent baseline --set test --name baseline_test_r1
    uv run python -m evals.run run --agent agent --set dev --name agent_dev --no-web
    uv run python -m evals.run rescore agent_dev agent_dev_rejudged
    uv run python -m evals.run compare baseline_test_r1 agent_test_r1
"""

from __future__ import annotations

import hashlib
import json
import random
import statistics
import subprocess
import traceback
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from agents import tracing
from evals.scorers import JUDGE_MODEL, primary_hosts, score_row

ROOT = Path(__file__).resolve().parent.parent
SETS = {"dev": ROOT / "evals" / "golden.jsonl", "test": ROOT / "evals" / "test_heldout.jsonl",
        "hard": ROOT / "evals" / "test_hard.jsonl", "dev_tables": ROOT / "evals" / "dev_tables.jsonl",
        "tables": ROOT / "evals" / "test_tables.jsonl"}
RESULTS = ROOT / "results"
FIELDS = ("id", "category", "difficulty", "time_sensitivity", "answer_type", "question", "grading", "answer")
# Rows of table sets also carry "cells"; scorers grade those cell by cell.

app = typer.Typer(add_completion=False)
console = Console()


def load_set(name: str, ids: str | None = None) -> list[dict]:
    if not SETS[name].exists():
        return []
    rows = [json.loads(line) for line in SETS[name].read_text().splitlines() if line.strip()]
    if ids:
        wanted = set(ids.split(","))
        rows = [r for r in rows if r["id"] in wanted]
    return rows


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_version() -> str:
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "agents", "evals"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    return head + ("+uncommitted" if dirty else "")


def agent_runner(agent: str, name: str, web: bool, web_cache_from: str | None):
    if agent == "baseline":
        from agents.baseline import run

        return lambda row, callbacks: run(row["question"], callbacks=callbacks)
    if agent == "agent":
        from agents.pipeline import run

        cache = RESULTS / "tavily_cache" / (web_cache_from or name)
        return lambda row, callbacks: run(row["question"], today=date.fromisoformat(row["as_of"][:10]), callbacks=callbacks,
                                          web_cache=cache, live_web=web and not web_cache_from)
    raise typer.BadParameter(f"unknown agent: {agent}")


# ---------- aggregation ----------

def _pct(n: float, d: float) -> str:
    return f"{100 * n / d:.0f}%" if d else "n/a"


def summarize(records: list[dict]) -> dict:
    def agg(rs: list[dict]) -> dict:
        fixed = [r for r in rs if r["time_sensitivity"] == "static"]
        dyn = [r for r in rs if r["time_sensitivity"] == "dynamic"]
        cit = [r["scores"]["citations"] for r in rs]
        src = [r["scores"]["sources"] for r in rs]
        return {
            "n": len(rs),
            "fixed_n": len(fixed),
            "fixed_correct": sum(r["scores"]["correctness"]["verdict"] == "correct" for r in fixed),
            "fixed_score": statistics.mean(r["scores"]["correctness"]["score"] for r in fixed) if fixed else None,
            "dynamic_n": len(dyn),
            "dynamic_score": statistics.mean(r["scores"]["correctness"]["score"] for r in dyn) if dyn else None,
            "numeric_claims": sum(c["numeric_claims"] for c in cit),
            "numeric_cited": sum(c["numeric_cited"] for c in cit),
            "cited_claims": sum(c["cited"] for c in cit),
            "supported": sum(c["supported"] for c in cit),
            "cited_urls": sum(len(s["cited_urls"]) for s in src),
            "cited_primary": sum(s["cited_primary"] for s in src),
            "errors": sum(1 for r in rs if r["output"].get("error")),
            "judge_errors": sum(1 for r in rs if r["scores"]["correctness"].get("judge_error")),
        }

    ok = [r for r in records if not r["output"].get("error")]
    lat = sorted(r["output"]["latency_s"] for r in ok)
    groups = defaultdict(list)
    for r in records:
        groups[r["category"]].append(r)
    return {
        "overall": agg(records),
        "by_category": {k: agg(v) for k, v in sorted(groups.items())},
        "ops": {
            "latency_p50_s": statistics.median(lat) if lat else None,
            "latency_p95_s": lat[min(len(lat) - 1, int(0.95 * len(lat)))] if lat else None,
            "tokens_per_q": statistics.mean(r["output"]["tokens"]["input"] + r["output"]["tokens"]["output"] for r in ok) if ok else None,
            "credits_per_q": statistics.mean(r["output"].get("tavily_credits", 0) for r in ok) if ok else None,
            "credits_total": sum(r["output"].get("tavily_credits", 0) for r in records),
        },
    }


HEAD = ("| Slice | Qs | Fixed answers: fully correct (mean score) | Time-sensitive: rubric score "
        "| Numbers with a citation | Cited claims supported | Cited URLs that are primary |\n|---|---|---|---|---|---|---|")


def _row(label: str, a: dict) -> str:
    fixed = f"{a['fixed_correct']}/{a['fixed_n']} ({a['fixed_score']:.2f})" if a["fixed_n"] else "–"
    dyn = f"{a['dynamic_score']:.2f} (n={a['dynamic_n']})" if a["dynamic_n"] else "–"
    return (f"| {label} | {a['n']} | {fixed} | {dyn} | {_pct(a['numeric_cited'], a['numeric_claims'])} "
            f"| {_pct(a['supported'], a['cited_claims'])} | {_pct(a['cited_primary'], a['cited_urls'])} |")


def write_scorecard(name: str, manifest: dict, summary: dict, records: list[dict]) -> Path:
    o, ops = summary["overall"], summary["ops"]
    lines = [
        f"# Scorecard: {name}", "",
        f"Agent `{manifest['agent']}` · set `{manifest['set']}` · model `{manifest.get('model')}` · judge `{JUDGE_MODEL}` "
        f"· code `{manifest['code']}` · questions {o['n']} · agent errors {o['errors']} · judge errors {o['judge_errors']}", "",
        HEAD, _row("All", o), "",
        "| Median latency | p95 latency | Tokens / question | Tavily credits / question | Tavily credits total |",
        "|---|---|---|---|---|",
        f"| {ops['latency_p50_s']:.1f} s | {ops['latency_p95_s']:.1f} s | {ops['tokens_per_q']:,.0f} "
        f"| {ops['credits_per_q']:.1f} | {ops['credits_total']:.0f} |", "",
        "## By category", "", HEAD, *[_row(k, v) for k, v in summary["by_category"].items()], "",
        "## Per question", "",
        "| ID | Category | Verdict | Score | Credits | Latency | Trace | Judge rationale |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(records, key=lambda r: r["id"]):
        c, out = r["scores"]["correctness"], r["output"]
        why = (out.get("error") or c["rationale"]).replace("|", "/").replace("\n", " ")[:240]
        trace = f"[trace]({out['trace_url']})" if out.get("trace_url") else "–"
        lines.append(f"| {r['id']} | {r['category']} | {c['verdict']} | {c['score']:.2f} | {out.get('tavily_credits', 0):g} "
                     f"| {out.get('latency_s', 0):.0f} s | {trace} | {why} |")
    path = RESULTS / f"scorecard_{name}.md"
    path.write_text("\n".join(lines) + "\n")
    return path


def write_judge_sample(name: str, records: list[dict], k: int = 10, seed: int = 7) -> Path:
    """Answers for a human to grade, to measure agreement with the judge."""
    fixed = [r for r in records if r["time_sensitivity"] == "static"]
    out = [f"# Judge agreement sample: {name}", "", "Write your verdict (correct / partial / incorrect) after **Your grade**.", ""]
    for r in sorted(random.Random(seed).sample(fixed, min(k, len(fixed))), key=lambda r: r["id"]):
        c = r["scores"]["correctness"]
        out += [f"## {r['id']}: {r['question']}", "", f"**Grading rule:** {r['grading']}", "",
                f"**Reference:** {r['answer']}", "",
                "**Agent answer:**\n\n> " + (r["output"].get("answer") or "(none)").replace("\n", "\n> "), "",
                f"**Judge:** {c['verdict']} ({c['score']:.2f}): {c['rationale']}", "", "**Your grade:** ", ""]
    path = RESULTS / f"judge_sample_{name}.md"
    path.write_text("\n".join(out) + "\n")
    return path


def finish(name: str, manifest: dict, records: list[dict]) -> dict:
    summary = summarize(records)
    (RESULTS / f"summary_{name}.json").write_text(json.dumps({"manifest": manifest, **summary}, indent=1))
    card = write_scorecard(name, manifest, summary, records)
    write_judge_sample(name, records)
    o = summary["overall"]
    console.print(f"[bold]{name}[/bold]: fixed {o['fixed_correct']}/{o['fixed_n']} fully correct "
                  f"(mean {o['fixed_score']:.2f}) · credits {summary['ops']['credits_total']:g} → {card.relative_to(ROOT)}")
    return summary


# ---------- commands ----------

@app.command()
def run(
    agent: Annotated[str, typer.Option(help="baseline | agent")] = "agent",
    set_name: Annotated[str, typer.Option("--set", help="dev | test | hard | dev_tables | tables")] = "dev",
    name: Annotated[str, typer.Option(help="Run name (output files)")] = "dev_run",
    ids: Annotated[str | None, typer.Option(help="Comma-separated question IDs")] = None,
    workers: Annotated[int, typer.Option(help="Questions in parallel")] = 4,
    web: Annotated[bool, typer.Option(help="Allow live Tavily calls (agent only)")] = True,
    web_cache_from: Annotated[str | None, typer.Option(help="Replay Tavily responses from an earlier run; no credits")] = None,
    resume: Annotated[bool, typer.Option(help="Continue an interrupted run, skipping saved questions")] = False,
) -> None:
    """Run an agent on a question set, score every answer, and write the scorecard."""
    rows = load_set(set_name, ids)
    raw_dir = RESULTS / "raw" / name
    done = {}
    if raw_dir.exists() and any(raw_dir.glob("[GTHDX][0-9]*.json")):
        if not resume:
            raise typer.BadParameter(f"results/raw/{name} already exists; choose a new run name or pass --resume")
        done = {p.stem: json.loads(p.read_text()) for p in raw_dir.glob("[GTHDX][0-9]*.json")}
    raw_dir.mkdir(parents=True, exist_ok=True)
    runner = agent_runner(agent, name, web, web_cache_from)
    hosts = primary_hosts([r for s in SETS for r in load_set(s)])
    manifest = {"agent": agent, "set": set_name, "set_sha256": sha256(SETS[set_name]), "code": code_version(),
                "ids": [r["id"] for r in rows], "web": web, "web_cache_from": web_cache_from}
    if done and (raw_dir / "manifest.json").exists():
        first = json.loads((raw_dir / "manifest.json").read_text())
        manifest = {**first, "resumed": first.get("resumed", []) + [{"code": manifest["code"], "skipped": sorted(done)}]}
    (raw_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))

    def one(row: dict) -> dict:
        with tracing.trace_question(agent, row["question"], name, row) as trace:
            try:
                output = runner(row, trace.callbacks)
            except Exception as exc:
                output = {"answer": "", "tool_calls": [], "tool_results": [], "tokens": {"input": 0, "output": 0},
                          "tavily_credits": 0, "latency_s": 0.0,
                          "error": f"{type(exc).__name__}: {exc}"[:500], "traceback": traceback.format_exc()[-2000:]}
            trace.finish(output)
        output["trace_id"], output["trace_url"] = trace.trace_id, trace.url
        scores = score_row(row, output, hosts)
        tracing.attach_scores(trace.trace_id, scores)
        record = {**{k: row[k] for k in FIELDS}, "output": output, "scores": scores}
        (raw_dir / f"{row['id']}.json").write_text(json.dumps(record, indent=1, ensure_ascii=False, default=str))
        return record

    records = [done[r["id"]] for r in rows if r["id"] in done]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(one, r) for r in rows if r["id"] not in done]):
            rec = future.result()
            records.append(rec)
            c = rec["scores"]["correctness"]
            err = f" · ERROR {rec['output']['error'][:100]}" if rec["output"].get("error") else ""
            console.print(f"{rec['id']}: {c['verdict']} ({c['score']:.2f}) · {rec['output'].get('latency_s', 0):.0f}s"
                          f" · {rec['output'].get('tavily_credits', 0):g} cr{err}")
    tracing.flush()
    manifest["model"] = next((r["output"].get("model") for r in records if r["output"].get("model")), None)
    finish(name, manifest, records)


@app.command()
def rescore(source: str, name: str, workers: int = 4) -> None:
    """Re-judge a saved run's answers without re-running the agent."""
    src = RESULTS / "raw" / source
    manifest = {**json.loads((src / "manifest.json").read_text()), "rescored_from": source}
    rows = {r["id"]: r for s in SETS for r in load_set(s)}
    hosts = primary_hosts(list(rows.values()))
    out_dir = RESULTS / "raw" / name
    out_dir.mkdir(parents=True, exist_ok=False)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))

    def one(path: Path) -> dict:
        rec = json.loads(path.read_text())
        rec["scores"] = score_row(rows[rec["id"]], rec["output"], hosts)
        (out_dir / path.name).write_text(json.dumps(rec, indent=1, ensure_ascii=False, default=str))
        return rec

    with ThreadPoolExecutor(max_workers=workers) as pool:
        records = list(pool.map(one, sorted(src.glob("[GTHDX][0-9]*.json"))))
    finish(name, manifest, records)


@app.command()
def compare(run_a: str, run_b: str) -> None:
    """Side-by-side metrics and per-question verdict changes for two runs on the same set."""
    def load(n):
        recs = {p.stem: json.loads(p.read_text()) for p in (RESULTS / "raw" / n).glob("[GTHDX][0-9]*.json")}
        return recs, json.loads((RESULTS / f"summary_{n}.json").read_text())

    (ra, sa), (rb, sb) = load(run_a), load(run_b)
    common = sorted(set(ra) & set(rb))
    oa, ob = sa["overall"], sb["overall"]
    verdict = lambda r, i: r[i]["scores"]["correctness"]["verdict"]
    flips = [f"{i} ({verdict(ra, i)}→{verdict(rb, i)})" for i in common if verdict(ra, i) != verdict(rb, i)]

    def fmt(x, spec):
        return "n/a" if x is None else format(x, spec)

    lines = [
        f"# {run_a} vs {run_b}", "", f"| Metric | {run_a} | {run_b} |", "|---|---|---|",
        f"| Fixed answers fully correct | {oa['fixed_correct']}/{oa['fixed_n']} | {ob['fixed_correct']}/{ob['fixed_n']} |",
        f"| Fixed answers mean score | {fmt(oa['fixed_score'], '.3f')} | {fmt(ob['fixed_score'], '.3f')} |",
        f"| Time-sensitive rubric score | {fmt(oa['dynamic_score'], '.3f')} | {fmt(ob['dynamic_score'], '.3f')} |",
        f"| Numbers with a citation | {_pct(oa['numeric_cited'], oa['numeric_claims'])} | {_pct(ob['numeric_cited'], ob['numeric_claims'])} |",
        f"| Cited claims supported | {_pct(oa['supported'], oa['cited_claims'])} | {_pct(ob['supported'], ob['cited_claims'])} |",
        f"| Cited URLs that are primary | {_pct(oa['cited_primary'], oa['cited_urls'])} | {_pct(ob['cited_primary'], ob['cited_urls'])} |",
        f"| Tavily credits / question | {fmt(sa['ops']['credits_per_q'], '.1f')} | {fmt(sb['ops']['credits_per_q'], '.1f')} |",
        f"| Tokens / question | {fmt(sa['ops']['tokens_per_q'], ',.0f')} | {fmt(sb['ops']['tokens_per_q'], ',.0f')} |",
        f"| Median latency | {fmt(sa['ops']['latency_p50_s'], '.1f')} s | {fmt(sb['ops']['latency_p50_s'], '.1f')} s |",
        "", f"Verdict changes ({len(flips)} of {len(common)}): {', '.join(flips) or 'none'}",
    ]
    path = RESULTS / f"compare_{run_a}_vs_{run_b}.md"
    path.write_text("\n".join(lines) + "\n")
    console.print("\n".join(lines))


if __name__ == "__main__":
    app()
