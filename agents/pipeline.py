"""Financial research agent: resolve -> plan -> evidence -> write & verify -> cited brief.

    uv run python -m agents.pipeline "What was <company>'s revenue in its latest reported quarter?"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from agents import tracing
from agents.company import resolve
from agents.edgar import EdgarClient
from agents.llm import AGENT_MODEL
from agents.planner import Plan, plan, validate
from agents.research import SearchConfig, Web, gap_evidence, number_evidence, sec_evidence, to_dicts, web_evidence
from agents.writer import write

DISCLAIMER = ("Draft for analyst review. Every figure is quoted from the cited source or computed in code "
              "from quoted inputs; claims that failed verification were removed.")


def _table(cells: list[dict], cite) -> list[str]:
    """Pivot verified cells into a markdown table, each value followed by its citations."""
    rows = list(dict.fromkeys(c["row"] for c in cells))
    cols = list(dict.fromkeys(c["column"] for c in cells))
    grid = {(c["row"], c["column"]): f"{c['value']} {cite(c['evidence_ids'])}".strip() for c in cells}
    out = ["| | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    out += [f"| {r} | " + " | ".join(grid.get((r, c), "—") for c in cols) + " |" for r in rows]
    return out


def render(question: str, today: date, result: dict, evidence: dict) -> str:
    """Markdown brief with numbered citations to the sources actually used."""
    order: list[str] = []

    def cite(ids: list[str]) -> str:
        marks = []
        for i in ids:
            if i in evidence:
                if i not in order:
                    order.append(i)
                marks.append(f"[{order.index(i) + 1}]")
        return "".join(marks)

    lines = [f"**Question:** {question}", f"*As of {today}*", ""]
    if result.get("assumptions"):
        lines += ["**Interpreted as:** " + " ".join(result["assumptions"]), ""]
    if result.get("table"):
        lines += _table(result["table"], cite) + [""]
    if result["claims"]:
        lines += [f"- {c['text']} {cite(c['evidence_ids'])}" for c in result["claims"]]
    if result["unavailable"]:
        lines += ["", "**Not available**"]
        lines += [f"- {u['item']}: {u['reason']} {cite(u['evidence_ids'])}".rstrip() for u in result["unavailable"]]
    if result.get("out_of_scope"):
        lines += ["", "**Outside this tool's scope**"] + [f"- {item}" for item in result["out_of_scope"]]
    if not result.get("semantic_check", True):
        lines += ["", "_The meaning check (company, period, basis) could not run for this answer; "
                      "quotes, numbers and arithmetic were still verified in code._"]
    if result["removed"]:
        lines += ["", f"_{len(result['removed'])} draft statement(s) were withheld because they could not be "
                      "verified against the sources (details in the run record)._"]
    if order:
        lines += ["", "**Sources**"]
        for n, i in enumerate(order, start=1):
            e = evidence[i]
            lines.append(f"[{n}] {e['title']} ({urlparse(e['url']).netloc}, {e['date'] or 'undated'}, "
                         f"{e['tier']}) {e['url']}")
    lines += ["", f"_{DISCLAIMER}_"]
    return "\n".join(lines)


def run(question: str, *, today: date | None = None, callbacks=None, web_cache: Path | str = "results/tavily_cache",
        live_web: bool = True, search: SearchConfig = SearchConfig(), fixed_plan: Plan | None = None) -> dict:
    """Answer one question. Returns the brief plus everything the eval harness records.

    `fixed_plan` replays a saved research plan (evaluation only), so runs that compare search
    settings differ only in how Tavily is called.
    """
    today = today or date.today()
    start = time.perf_counter()
    client = EdgarClient()
    tokens = {"input": 0, "output": 0}

    def add(t):
        for k in tokens:
            tokens[k] += t.get(k, 0)

    companies, clarification, t = resolve(question, today, client, callbacks)
    add(t)
    if clarification:  # nothing to research until the user says what they mean
        return clarify(question, today, clarification, tokens, start)
    if fixed_plan:
        research_plan = validate(fixed_plan, companies)
    else:
        research_plan, t = plan(question, companies, today, callbacks)
        add(t)
    web = Web(web_cache, live=live_web)
    evidence = sec_evidence(question, research_plan, companies, today, client)
    evidence += asyncio.run(web_evidence(question, research_plan, companies, today, web, search))
    evidence = number_evidence(evidence)
    framing = {"assumptions": research_plan.assumptions, "out_of_scope": research_plan.out_of_scope}
    result = write(question, today, research_plan.availability_notes, evidence, callbacks, **framing)
    add(result["tokens"])
    # Gap filling: if something may exist but wasn't in the evidence, search for it once and rewrite.
    gaps = [u["item"] for u in result["unavailable"] if u.get("kind") == "not_in_evidence"]
    if gaps:
        known = {e.url for e in evidence}
        extra = [e for e in asyncio.run(gap_evidence(question, gaps, companies, today, web, search)) if e.url not in known]
        if extra:
            evidence = number_evidence(evidence + extra)
            result = write(question, today, research_plan.availability_notes, evidence, callbacks, **framing)
            add(result["tokens"])

    result.update(framing)
    by_id = {e["id"]: e for e in to_dicts(evidence)}
    answer = render(question, today, result, by_id)
    supported = result["claims"] + result.get("table", [])
    cited = {i for c in supported for i in c["evidence_ids"]} | {i for u in result["unavailable"] for i in u["evidence_ids"]}
    # What the scorers see as "retrieved": every evidence item, with the quotes used from it first.
    quotes = {}
    for c in supported:
        for i in c["evidence_ids"]:
            quotes.setdefault(i, []).extend(c["quotes"])
    retrieved = [{"url": e["url"], "title": e["title"], "published_date": e["date"],
                  "content": ("Quoted: " + " | ".join(quotes[e["id"]]) + "\n---\n" if e["id"] in quotes else "") + e["text"]}
                 for e in by_id.values()]
    return {
        "answer": answer,
        "tool_calls": web.calls,
        "tool_results": [{"results": retrieved}],
        "tokens": tokens,
        "tavily_credits": web.credits,
        "latency_s": round(time.perf_counter() - start, 2),
        "model": AGENT_MODEL,
        "companies": [{"name": c.name, "ticker": c.ticker, "cik": c.cik, "resolved": c.resolved} for c in companies],
        "plan": research_plan.model_dump(),
        "evidence_ids_cited": sorted(cited),
        "claims": result["claims"],
        "table": result.get("table", []),
        "unavailable": result["unavailable"],
        "removed": result["removed"],
        "semantic_check": result["semantic_check"],
        "gaps_searched": gaps,
        **framing,
        "clarification": None,
    }


def clarify(question: str, today: date, clarification: str, tokens: dict, start: float) -> dict:
    """The answer when the question can't be researched without asking the user first."""
    answer = "\n".join([f"**Question:** {question}", f"*As of {today}*", "", f"**Clarification needed:** {clarification}",
                        "", "_No figures were looked up; ask again with the company (and period) you mean._"])
    return {"answer": answer, "tool_calls": [], "tool_results": [{"results": []}], "tokens": tokens,
            "tavily_credits": 0, "latency_s": round(time.perf_counter() - start, 2), "model": AGENT_MODEL,
            "companies": [], "plan": None, "evidence_ids_cited": [], "claims": [], "table": [], "unavailable": [],
            "removed": [], "semantic_check": True, "gaps_searched": [], "assumptions": [], "out_of_scope": [],
            "clarification": clarification}


def main():
    parser = argparse.ArgumentParser(description="Cited answers to analyst questions about SEC-reporting companies.")
    parser.add_argument("question")
    parser.add_argument("--today", type=date.fromisoformat, default=date.today(), help="As-of date (YYYY-MM-DD)")
    parser.add_argument("--json", action="store_true", help="Print the full JSON record instead of the brief")
    args = parser.parse_args()
    with tracing.trace_question("agent", args.question, "cli") as trace:
        output = run(args.question, today=args.today, callbacks=trace.callbacks)
        trace.finish(output)
    tracing.flush()
    print(json.dumps(output, indent=1, default=str) if args.json else output["answer"])


if __name__ == "__main__":
    main()
