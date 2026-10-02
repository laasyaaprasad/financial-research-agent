"""One small-model planning call; code owns dates, company IDs and credit limits.

The model selects periods from a filing-based catalog and describes retrieval
intents. This module executes no Tavily searches and no research/answer step.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from typing import Literal

from pydantic import Field

from agents.calendar import DAY, FiscalCalendar, add_months
from agents.company import resolve
from agents.edgar import EdgarClient
from agents.models import SMALL_MODEL, structured
from agents.periods import explicit_periods
from agents.schemas import Brief, EdgarFetch, Period, Record, Researcher, ResearchPlan, Resolution, Search

class PeriodChoice(Record):
    keys: list[str] = Field(default_factory=list)
    transform: Literal["identity", "union", "ttm", "next_twelve_months", "news_window", "calendar_year", "comp_window"] = "identity"
    label: str = ""
    year: int | None = None
    days: int | None = None


class FetchChoice(Record):
    key: str
    form: Literal["10-K", "10-Q", "8-K", "20-F", "40-F", "6-K"]
    item: str


class SearchChoice(Record):
    researcher: Researcher
    reason: str
    intent: str = Field(min_length=1, max_length=250)
    tickers: list[str] = Field(default_factory=list)
    search_depth: Literal["basic", "fast", "advanced"] = "advanced"


class PlanDraft(Record):
    brief: Brief
    periods: list[PeriodChoice]
    edgar_fetches: list[FetchChoice]
    searches: list[SearchChoice] = Field(max_length=8)


PLAN_PROMPT = """Plan company research for a financial analyst. Return structured data;
do not research, answer, fabricate facts, or call external tools. Work once, no re-planning.

INPUTS: question, as-of date, resolved entities, period catalog and search credit budget.
When requested_periods is supplied, code has already bound the answer scope. Use
those exact periods; do not change their identities, combine them or add comparisons.
Choose exactly the periods needed for the requested answer, including prior-year
comparisons when growth requires them. Do not select every period used only to fetch
inputs: the separate edgar_fetches field can reference those input periods.
In particular:
- A quarter's disclosed YoY growth rate or management commentary needs only the
  requested quarter in periods; place prior-year quarter inputs in edgar_fetches.
- Annual revenue/fee growth calculations need current and prior annual periods.
- Reported vs constant-exchange growth disclosures need only the stated annual year.
- A consecutive-quarter series includes exactly that range, not an extra prior
  quarter needed to calculate the first growth rate (that belongs in edgar_fetches).
- Implied Q4 from annual guidance needs 9M actual plus Q4 implied, not an extra
  full-year answer period. The annual guide belongs in edgar_fetches.
- A TTM revenue construction needs the annual and current/prior quarterly components
  as well as the TTM result; RPO next-year recognition needs its forward window too.

Periods: use catalog keys; code supplies exact dates. 'identity' selects a single
key, 'union' merges contiguous periods or multiple companies sharing exactly the
same dates. A nine-month implied total needs a 9M period (not separate quarters).
'ttm' is twelve months ending at one selected quarter; 'next_twelve_months' is the
next year after its end (only when the question asks for the forward time window).
'news_window' uses days=30 for an inclusive last-30-days window; 'calendar_year'
uses year; 'comp_window' is a 13-week comparison window ending at a selected quarter.
Prefer the catalog label. Add 'implied' or 'actual' to aggregate periods where
needed; add company names to distinguish periods in multi-company comparisons.
Do not replace fiscal with calendar labels. Calendar-year companies use Qn YYYY.
Target's FY labels refer to the starting calendar year; Walmart's to the ending year.
Honeywell's calendar-convention periods are used, not its operational closing date.
For Walmart U.S. comparable-sales comparisons, use comp_window on the financial
quarter to obtain its disclosed 13-week window. Target fiscal quarters already
span 13 weeks; render their year as Qn YYYY. Costco Q4 spans 16 weeks.
For news/management questions, do not invent a financial period when none is needed.
Use filing histories to distinguish most recently REPORTED quarters from merely
ended quarters; earnings may be released via 8-K before a 10-Q appears.

Brief: identify metrics, answer type and potential missing/unreported data. Private
companies cannot supply a public 10-K; Apple stopped disclosing iPhone unit sales;
Azure margin/revenue dollars are not separately disclosed. Do not substitute estimates.

Choose only necessary researchers from financials, news, company, industry:
- numerical financial lookup/calculation/reconciliation -> financials
- management guidance, outlook, remaining performance obligations/conversion,
  beat vs management guide, management commentary -> company (plus financials if numeric)
- recency/latest reported quarter, unreported/undisclosed/private data, recent events,
  or management commentary on one-time drivers -> news
- cross-company comparisons or export-control industry/regulatory context -> industry
Each chosen researcher must have at least one search. Max 8 searches; advanced=2
credits, basic/fast=1, never exceed the supplied budget. Zero budget means no searches.
For EVERY positive-budget plan, include at least one search per required researcher,
even when the main answer should come from EDGAR. Searches verify disclosures and
provide source context. Do not return an empty search list when the budget is positive.
The company researcher also covers leadership changes and RPO disclosures. Financials
must be included when a requested financial metric may be unreported, even if the
plan expects to abstain. Current cross-company capex guidance needs industry, news,
and company. For Honeywell consolidated/ex-Aerospace results, include only HON.
Financial information is sourced from SEC first; search supplements the filings.
Search intents must be short, specific, and factual. Code adds companies, dates
and fiscal labels. Do not rely on topic=finance being better (it is untested).

EDGAR fetches: choose form, catalog key and item. Use 20-F/6-K for foreign filers,
10-K for annual statements, 10-Q for quarters, 8-K for US earnings releases/guidance
or annual results released before a 10-K. No EDGAR fetch for unresolved companies.
Include comparative inputs and guidance source quarters required by calculations.
Future or not-yet-reported actuals must be flagged as possibly unreported; do not
plan a future filing as if it already exists."""


def catalog_for(resolution: Resolution, client: EdgarClient, today: date):
    catalog, calendars, warnings = {}, {}, []
    for entity in resolution.entities:
        if entity.status == "unresolved":
            warnings.append(f"{entity.requested_name}: {entity.reason}; no CIK or EDGAR fetch")
            if entity.company_name == "Cargill, Incorporated":
                for year in range(today.year - 4, today.year + 3):
                    catalog[f"Cargill:FY{year}"] = Period(
                        label=f"FY{year}", start=date(year - 1, 6, 1), end=date(year, 5, 31),
                        basis="projected", source_urls=entity.calendar_source_urls)
                warnings.append("Cargill calendar projected from its published June–May convention; private financial disclosures require company sources")
            continue
        cal = FiscalCalendar(entity, client, today)
        calendars[entity.ticker] = cal
        for p in cal.catalog():
            catalog[f"{entity.ticker}:{p.label}"] = p
        if cal.weekly and not cal.rule:
            warnings.append(f"{entity.ticker}: future 52-week projection; next 53-week adjustment must be confirmed from a filing")
    return catalog, calendars, warnings


def materialize(choice: PeriodChoice, catalog: dict[str, Period], today: date) -> Period:
    selected = [lookup_period(k, catalog) for k in choice.keys]  # unknown key fails closed
    if choice.transform == "news_window":
        days = choice.days or 30
        if not 1 <= days <= 366:
            raise ValueError("Invalid news window length")
        return Period(label=choice.label or f"{days}-day news window", start=today - timedelta(days=days-1), end=today)
    if choice.transform == "calendar_year":
        if not choice.year:
            raise ValueError("A calendar-year period needs its year")
        return Period(label=choice.label or f"Calendar {choice.year}", start=date(choice.year, 1, 1), end=date(choice.year, 12, 31))
    if not selected:
        raise ValueError("Period selection needs a known catalog key")
    period = selected[0].model_copy(deep=True)
    if choice.transform == "identity" and len(selected) != 1:
        raise ValueError("Identity period must have exactly one key")
    if choice.transform == "union":
        ordered = sorted(selected, key=lambda p: p.start)
        end = ordered[0].end
        for p in ordered[1:]:
            if p.start > end + DAY:
                raise ValueError("Cannot merge non-contiguous fiscal periods")
            end = max(end, p.end)
        period.start, period.end = ordered[0].start, end
        period.tickers = list(dict.fromkeys(t for p in selected for t in p.tickers))
        period.source_urls = list(dict.fromkeys(u for p in selected for u in p.source_urls))
        period.reported = all(p.reported for p in selected)
        if any(p.basis == "projected" for p in selected):
            period.basis = "projected"
    elif choice.transform == "ttm":
        period.start = add_months(period.end + DAY, -12)
        period.label = f"TTM through {period.label}"
    elif choice.transform == "next_twelve_months":
        period.start, period.end = period.end + DAY, add_months(period.end + DAY, 12) - DAY
        period.label = "Next twelve months"
        period.basis, period.reported = "projected", False
    elif choice.transform == "comp_window":
        period.start = period.end - timedelta(days=90)
        period.label += " comp window"
        period.basis = "calendar"
    if choice.label:
        if choice.transform == "identity":
            # Keep the fiscal identity supplied by code. Optional descriptors
            # distinguish guidance from actual aggregate periods, not identities.
            for suffix in ("implied", "actual", "outlook"):
                if suffix in choice.label.lower() and (period.label.startswith(("6M", "9M")) or suffix == "outlook"):
                    period.label += " " + suffix
        else:
            period.label = choice.label
    return Period.model_validate(period.model_dump())


def lookup_period(key: str, catalog: dict[str, Period]) -> Period:
    if key in catalog:
        return catalog[key]
    # A missing company prefix is harmless only when the fiscal identity has
    # exactly one owner. Never resolve an ambiguous or invented period.
    matching = [p for k, p in catalog.items() if k.split(":", 1)[-1] == key]
    if len(matching) == 1:
        return matching[0]
    raise ValueError("Unknown or ambiguous catalog period")


def plan(question: str, entity: Resolution, today: date, budget: int = 16, *,
         client: EdgarClient | None = None, model: str = SMALL_MODEL,
         callbacks: list | None = None) -> ResearchPlan:
    if budget < 0:
        raise ValueError("Budget cannot be negative")
    client = client or EdgarClient()
    catalog, calendars, warnings = catalog_for(entity, client, today)
    bound_periods = explicit_periods(question, entity, calendars, catalog, today)
    payload = {
        "question": question, "today": today.isoformat(), "search_credit_budget": budget,
        "entities": [e.model_dump() for e in entity.entities],
        "requested_periods": [p.model_dump(mode="json") for p in bound_periods] if bound_periods is not None else None,
        "period_catalog": [{"key": k, "start": p.start.isoformat(), "end": p.end.isoformat(),
                            "reported": p.reported, "basis": p.basis} for k, p in catalog.items()],
        "recent_filings": {t: [{"form": f["form"], "reportDate": f.get("reportDate"), "filingDate": f["filingDate"]}
                               for f in cal.filings[:12]] for t, cal in calendars.items()},
    }
    draft, tokens = structured(PlanDraft, PLAN_PROMPT, json.dumps(payload), model=model, callbacks=callbacks)
    periods = bound_periods if bound_periods is not None else [materialize(p, catalog, today) for p in draft.periods]
    by_ticker = {e.ticker: e for e in entity.entities if e.status == "resolved"}
    aliases = {t: e.ticker for e in by_ticker.values() for t in e.tickers}
    fetches = []
    for f in draft.edgar_fetches:
        prefix, sep, label = f.key.partition(":")
        key = f"{aliases.get(prefix, prefix)}:{label}" if sep else f.key
        p = lookup_period(key, catalog)
        if len(p.tickers) != 1 or p.tickers[0] not in by_ticker:
            raise ValueError("EDGAR fetch requires a resolved company")
        e = by_ticker[p.tickers[0]]
        if e.annual_form in ("20-F", "40-F") and f.form not in (e.annual_form, "6-K"):
            raise ValueError("Foreign filer requires its actual SEC form")
        if p.end > today:
            warnings.append(f"{e.ticker} {p.label}: future filing omitted; obtain outlook from a reported earnings release")
            continue
        if not p.reported and p.basis == "projected":
            warnings.append(f"{e.ticker} {p.label}: no reported filing yet; actual-results fetch omitted")
            continue
        form = f.form
        available = {r["form"] for r in calendars[e.ticker].filings if r.get("reportDate") == p.end.isoformat()}
        if form in ("10-K", "10-Q") and form not in available:
            if "10-K" in available:
                form = "10-K"  # Q4 statements are filed in the annual report.
            elif p.reported and "10-Q" not in available and "10-K" not in available:
                form = "8-K"  # Earnings can precede the periodic report.
                warnings.append(f"{e.ticker} {p.label}: use published earnings release before periodic filing")
        fetches.append(EdgarFetch(ticker=e.ticker, cik=e.cik, form=form, period_end=p.end, item=f.item))
    unreported = draft.brief.may_be_unreported or any(
        p.end > today or (not p.reported and p.basis == "projected") for p in periods)
    brief = draft.brief.model_copy(update={"may_be_unreported": unreported})
    required = required_researchers(question, entity, brief)
    choices = list(draft.searches)
    for researcher in sorted(required - {s.researcher for s in choices}):
        choices.append(SearchChoice(researcher=researcher, reason=f"Required {researcher} coverage for the question",
                                    intent=f"Verify {'; '.join(draft.brief.metrics) or question}"[:250]))
    # Reserve one search per required researcher before optional extra queries.
    primary, extra, seen = [], [], set()
    for s in choices:
        if s.researcher in required and s.researcher not in seen:
            primary.append(s)
            seen.add(s.researcher)
        else:
            extra.append(s)
    choices = (primary + extra)[:8]
    searches = []
    remaining = budget
    for s in choices:
        tickers = list(dict.fromkeys(aliases.get(t, t) for t in s.tickers))
        if any(t not in by_ticker for t in tickers):
            raise ValueError("Search references an unresolved or unknown ticker")
        es = [by_ticker[t] for t in tickers] if tickers else entity.entities
        names = "; ".join(f"{e.company_name or e.requested_name} {e.ticker or ''}".strip() for e in es)
        relevant = [p for p in periods if not p.tickers or not tickers or set(p.tickers) & set(tickers)]
        dates = "; ".join(f"{p.label} ({p.start} to {p.end})" for p in relevant[:2])
        prefix = f"{names} {dates}".strip()
        if len(prefix) >= 350:
            prefix = "; ".join(e.ticker or e.requested_name for e in es) + " " + dates
        query = f"{prefix} {s.intent[:398-len(prefix)]}".strip()
        depth = s.search_depth
        credits = 2 if depth == "advanced" else 1
        if remaining == 0:
            warnings.append("Search budget exhausted; remaining intents omitted")
            break
        if credits > remaining:
            depth, credits = "basic", 1
        remaining -= credits
        news_window = next((p for p in periods if "news window" in p.label.lower()), None)
        searches.append(Search(researcher=s.researcher, reason=s.reason, query=query,
                               topic="news" if s.researcher == "news" else "general", search_depth=depth,
                               start_date=news_window.start if s.researcher == "news" and news_window else None,
                               end_date=today if s.researcher == "news" and news_window else None,
                               preferred_domains=["sec.gov"] if s.researcher in ("financials", "company") else []))
    return ResearchPlan(brief=brief, periods=periods, edgar_fetches=fetches, searches=searches,
                        warnings=warnings, search_budget=budget, model=model, tokens=tokens)


def required_researchers(question: str, entity: Resolution, brief: Brief) -> set[str]:
    """Minimum coverage rules; the model can still choose additional researchers."""
    text = question.lower()
    required = set()
    if brief.answer_type in ("number", "list") or any(w in text for w in (
        "revenue", "margin", "eps", "rpo", "performance obligations", "net income", "share repurchases", "outlook")):
        required.add("financials")
    if any(w in text for w in ("guidance", "guiding", "outlook", "management", "rpo", "performance obligations", "ceo")):
        required.add("company")
    if (any(w in text for w in ("latest", "most recent", "right now", "current", "past 30", "what drove"))
            or brief.may_be_unreported or any(e.status == "unresolved" for e in entity.entities)):
        required.add("news")
    if len(entity.entities) > 1 or any(w in text for w in ("export controls", "competitor", "industry")):
        required.add("industry")
    return required or {"company"}


def main():
    parser = argparse.ArgumentParser(description="Resolve and plan company research; no Tavily calls")
    parser.add_argument("question")
    parser.add_argument("--today", type=date.fromisoformat, required=True, help="Explicit as-of date (YYYY-MM-DD)")
    parser.add_argument("--budget", type=int, default=16, help="Search credit budget; extraction reserved for M4")
    parser.add_argument("--model", default=SMALL_MODEL)
    args = parser.parse_args()
    client = EdgarClient()
    entities = resolve(args.question, client=client, model=args.model)
    result = plan(args.question, entities, args.today, args.budget, client=client, model=args.model)
    print(json.dumps({"resolution": entities.model_dump(), "plan": result.model_dump(mode="json")}, indent=2))


if __name__ == "__main__":
    main()
