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
from typing import Callable
from urllib.parse import urlparse

from agents import tracing
from agents.company import resolve
from agents.edgar import EdgarClient, EdgarError
from agents.llm import AGENT_MODEL
from agents.planner import Plan, fallback, plan, validate
from agents.research import SearchConfig, Web, gap_evidence, number_evidence, sec_evidence, to_dicts, web_evidence
from agents.writer import normalize, quote_found, write

DISCLAIMER = ("Draft for analyst review. Every figure is quoted from the cited source or computed in code "
              "from quoted inputs; claims that failed verification were removed.")


def _table(cells: list[dict], cite) -> list[str]:
    """Pivot verified cells into a markdown table, each value followed by its citations."""
    rows = list(dict.fromkeys(c["row"] for c in cells))
    cols = list(dict.fromkeys(c["column"] for c in cells))
    grid = {(c["row"], c["column"]): f"{c['value']} {cite(c)}".strip() for c in cells}
    out = ["| | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    out += [f"| {r} | " + " | ".join(grid.get((r, c), "—") for c in cols) + " |" for r in rows]
    return out


def citer(evidence: dict, mark: Callable[[int, str, dict], str] = lambda n, i, item: f"[{n}]",
          sep: str = "", ascending: bool = False) -> tuple[Callable[[dict], str], list[str]]:
    """A cite(statement) function marking each of the statement's sources, numbered by first citation, and the
    list of source ids it fills in that order. `mark(n, source_id, statement)` formats one marker; `ascending`
    lists a statement's markers by number instead of in the order it cites them."""
    order: list[str] = []

    def cite(item: dict) -> str:
        numbered = []
        for i in item["evidence_ids"]:
            if i in evidence:
                if i not in order:
                    order.append(i)
                numbered.append((order.index(i) + 1, i))
        return sep.join(mark(n, i, item) for n, i in (sorted(numbered) if ascending else numbered))

    return cite, order


def body(result: dict, cite) -> list[str]:
    """The answer itself: interpretation, table, claims, unavailable and declined items, each claim cited."""
    lines = []
    if result.get("assumptions"):
        lines += ["**Interpreted as:** " + " ".join(result["assumptions"]), ""]
    if result.get("table"):
        lines += _table(result["table"], cite) + [""]
    if result["claims"]:
        lines += [f"- {c['text']} {cite(c)}" for c in result["claims"]]
    if result["unavailable"]:
        lines += ["", "**Not available**"]
        lines += [f"- {u['item']}: {u['reason']} {cite(u)}".rstrip() for u in result["unavailable"]]
    if result.get("out_of_scope"):
        lines += ["", "**Outside this tool's scope**"] + [f"- {item}" for item in result["out_of_scope"]]
    if not result.get("semantic_check", True):
        lines += ["", "_The meaning check (company, period, basis) could not run for this answer; "
                      "quotes, numbers and arithmetic were still verified in code._"]
    return lines


def render(question: str, today: date, result: dict, evidence: dict) -> str:
    """Markdown brief with numbered citations to the sources actually used."""
    cite, order = citer(evidence)
    lines = [f"**Question:** {question}", f"*As of {today}*", ""]
    if result.get("draft_failed"):
        found = list(evidence.values())[:8]
        lines += ["**No verified answer.** The model service failed while drafting the answer, so nothing was "
                  "checked or cited. Sources retrieved for it:"]
        lines += [f"- {e['title']} ({urlparse(e['url']).netloc}, {e['date'] or 'undated'}) {e['url']}" for e in found]
        return "\n".join(lines + ["", f"_{DISCLAIMER}_"])
    lines += body(result, cite)
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


def _companies_note(companies: list) -> str:
    return "\n".join(f"- {c.name} ({c.ticker}, CIK {c.cik})" if c.resolved else f"- {c.requested}: {c.reason}"
                     for c in companies) or "No company identified"


def _plan_note(p) -> str:
    parts = [("Interpreted as", p.assumptions), ("Periods", [f"{r.ticker} {r.label}" for r in p.answer_periods]),
             ("Filings", [f"{d.ticker} {d.period} {d.document.replace('_', ' ')}" for d in p.documents]),
             ("Web searches", [s.query for s in p.searches]), ("Declined", p.out_of_scope),
             ("Availability", p.availability_notes)]
    return "\n".join(f"- **{name}:** " + "; ".join(items) for name, items in parts if items) or "Nothing to research"


def _verified_note(result: dict) -> str:
    if result.get("draft_failed"):
        return f"Drafting failed, so nothing was checked: {result['draft_failed']}"
    n = len(result["claims"]) + len(result.get("table", []))
    lines = [f"{n} statement(s) verified against their sources, {len(result['unavailable'])} marked not available"]
    lines += [f"- Withheld: {r['text']} ({r['problem']})" for r in result["removed"]]
    return "\n".join(lines)


def _sources(ids: set[str], items: list[dict], by_id: dict) -> dict:
    """Each cited source's metadata and the quotes taken from it: claim quotes found in its text, calculation inputs."""
    out = {}
    for i in sorted(ids & by_id.keys(), key=lambda i: int(i[1:])):
        e = by_id[i]
        text = [normalize(e["text"])]
        used = [q for c in items if i in c["evidence_ids"] for q in c["quotes"] if quote_found(q, text)]
        used += [x["quote"] for c in items if c.get("calculation") for x in c["calculation"]["inputs"]
                 if x["evidence_id"] == i]
        out[i] = {"url": e["url"], "title": e["title"], "date": e["date"], "tier": e["tier"],
                  "quotes": list(dict.fromkeys(used))}
    return out


def run(question: str, *, today: date | None = None, callbacks=None, web_cache: Path | str = "results/tavily_cache",
        live_web: bool = True, search: SearchConfig = SearchConfig(), fixed_plan: Plan | None = None,
        on_step: Callable[[str, str | None], None] | None = None) -> dict:
    """Answer one question. Returns the brief plus everything the eval harness records.

    `fixed_plan` replays a saved research plan (evaluation only), so runs that compare search
    settings differ only in how Tavily is called. `on_step(stage, detail)` reports progress to
    interactive front ends: `detail` is None when a stage starts and a short markdown summary when it ends.
    """
    today = today or date.today()
    step = on_step or (lambda stage, detail: None)
    start = time.perf_counter()
    client = EdgarClient()
    tokens = {"input": 0, "output": 0}

    def add(t):
        for k in tokens:
            tokens[k] += t.get(k, 0)

    step("Identify companies", None)
    with tracing.step("resolve", today=today.isoformat()) as span:
        try:
            companies, clarification, t = resolve(question, today, client, callbacks)
        except (ValueError, EdgarError) as exc:  # model or SEC unavailable: say so rather than return nothing
            return failed(question, today, f"identifying the company failed ({type(exc).__name__})", tokens, start)
        tracing.set_output(span, {"companies": [f"{c.name} ({c.ticker or c.cik})" for c in companies],
                                  "clarification": clarification})
    add(t)
    step("Identify companies", f"Needs clarification: {clarification}" if clarification else _companies_note(companies))
    if clarification:  # nothing to research until the user says what they mean
        return clarify(question, today, clarification, tokens, start)
    step("Plan research", None)
    with tracing.step("plan", fixed=bool(fixed_plan)) as span:
        if fixed_plan:
            research_plan = validate(fixed_plan, companies)
        else:
            try:
                research_plan, t = plan(question, companies, today, callbacks)
                add(t)
            except ValueError:
                research_plan = fallback(question, companies)
        tracing.set_output(span, research_plan.model_dump())
    step("Plan research", _plan_note(research_plan))
    web = Web(web_cache, live=live_web)
    step("Read SEC filings", None)
    with tracing.step("sec_evidence") as span:
        evidence = sec_evidence(question, research_plan, companies, today, client)
        tracing.set_output(span, [e.url for e in evidence], items=len(evidence))
    step("Read SEC filings", f"{len(evidence)} source(s) read: filing passages and tagged XBRL data")
    if research_plan.searches:
        step("Search the web", None)
    with tracing.step("web_evidence", live=live_web) as span:
        web_items = asyncio.run(web_evidence(question, research_plan, companies, today, web, search))
        tracing.set_output(span, [e.url for e in web_items], items=len(web_items))
    if research_plan.searches:
        step("Search the web", f"{len(web_items)} result(s) kept" + ("" if live_web else " (cached responses only)"))
    evidence = number_evidence(evidence + web_items)
    framing = {"assumptions": research_plan.assumptions, "out_of_scope": research_plan.out_of_scope}
    step("Write and verify", None)
    with tracing.step("write", evidence=len(evidence)) as span:
        result = write(question, today, research_plan.availability_notes, evidence, callbacks, **framing)
        tracing.set_output(span, {k: len(result.get(k) or []) for k in ("claims", "table", "unavailable", "removed")})
    add(result["tokens"])
    step("Write and verify", _verified_note(result))
    # Gap filling: if something may exist but wasn't in the evidence, search for it once and rewrite.
    gaps = [u["item"] for u in result["unavailable"] if u.get("kind") == "not_in_evidence"]
    if gaps:
        step("Fill gaps", None)
        known = {e.url for e in evidence}
        with tracing.step("gap_search", gaps=gaps) as span:
            extra = [e for e in asyncio.run(gap_evidence(question, gaps, companies, today, web, search)) if e.url not in known]
            tracing.set_output(span, [e.url for e in extra], items=len(extra))
        if extra:
            evidence = number_evidence(evidence + extra)  # new items are numbered after the existing ones
            with tracing.step("rewrite", evidence=len(evidence)) as span:
                rewritten = write(question, today, research_plan.availability_notes, evidence, callbacks, **framing)
                tracing.set_output(span, {"kept": not rewritten.get("draft_failed")})
            add(rewritten["tokens"])
            if not rewritten.get("draft_failed"):  # otherwise keep the first, already checked answer
                result = rewritten
        step("Fill gaps", f"Searched for: {'; '.join(gaps)}. {len(extra)} new source(s)"
             + (f", answer rewritten.\n{_verified_note(result)}" if extra and result is rewritten else "."))

    result.update(framing)
    by_id = {e["id"]: e for e in to_dicts(evidence)}
    answer = render(question, today, result, by_id)
    supported = result["claims"] + result.get("table", [])
    cited = {i for c in supported for i in c["evidence_ids"]} | {i for u in result["unavailable"] for i in u["evidence_ids"]}
    inputs = {x["evidence_id"] for c in supported if c.get("calculation") for x in c["calculation"]["inputs"]}
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
        "sources": _sources(cited | inputs, supported, by_id),
        "claims": result["claims"],
        "table": result.get("table", []),
        "unavailable": result["unavailable"],
        "removed": result["removed"],
        "semantic_check": result["semantic_check"],
        "gaps_searched": gaps,
        **framing,
        "clarification": None,
        "error": f"drafting failed: {result['draft_failed']}" if result.get("draft_failed") else None,
    }


def failed(question: str, today: date, reason: str, tokens: dict, start: float) -> dict:
    """The answer when a step before research fails: an explicit message, never an empty answer."""
    out = clarify(question, today, "", tokens, start)
    out["answer"] = "\n".join([f"**Question:** {question}", f"*As of {today}*", "",
                               f"**No answer.** {reason[0].upper() + reason[1:]}; please try again."])
    return {**out, "clarification": None, "error": reason}


def clarify(question: str, today: date, clarification: str, tokens: dict, start: float) -> dict:
    """The answer when the question can't be researched without asking the user first."""
    answer = "\n".join([f"**Question:** {question}", f"*As of {today}*", "", f"**Clarification needed:** {clarification}",
                        "", "_No figures were looked up; ask again with the company (and period) you mean._"])
    return {"answer": answer, "tool_calls": [], "tool_results": [{"results": []}], "tokens": tokens,
            "tavily_credits": 0, "latency_s": round(time.perf_counter() - start, 2), "model": AGENT_MODEL,
            "companies": [], "plan": None, "evidence_ids_cited": [], "sources": {}, "claims": [], "table": [],
            "unavailable": [], "removed": [], "semantic_check": True, "gaps_searched": [], "assumptions": [],
            "out_of_scope": [], "clarification": clarification}


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
