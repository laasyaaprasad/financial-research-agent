"""One planning call: which reported periods, filings and web searches the question needs.

The model chooses from the company's real reporting calendar (labels, dates, status);
code validates every choice against that calendar and the search budget.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from agents.company import Company
from agents.llm import structured

MAX_SEARCHES = 3


class PeriodRef(BaseModel):
    ticker: str
    label: str = Field(description="A period label exactly as listed in that company's calendar")


class DocumentRequest(BaseModel):
    ticker: str
    period: str = Field(description="Period label from the calendar")
    document: Literal["earnings_release", "periodic_report"]


class SearchRequest(BaseModel):
    purpose: str
    query: str = Field(description="Short web search query that names the company; under 200 characters")
    topic: Literal["general", "news"] = "general"
    days_back: int | None = Field(default=None, description="Only for recency: limit results to the last N days")


class Plan(BaseModel):
    metrics: list[str] = Field(description="The specific figures, facts or judgements the answer needs")
    answer_periods: list[PeriodRef] = Field(default_factory=list, description="Periods the answer is about")
    documents: list[DocumentRequest] = Field(default_factory=list, description="Filings to read, at most 6")
    recent_filings_days: int | None = Field(default=None, description="Read 8-K current reports from the last N days (events such as leadership changes)")
    searches: list[SearchRequest] = Field(default_factory=list, description=f"Web searches, at most {MAX_SEARCHES}")
    availability_notes: list[str] = Field(default_factory=list, description="Requested data that may not exist as of today and why")


PROMPT = f"""You plan research for a financial analyst's question. Do not answer it.

You get today's date and, for each company, its reporting calendar from SEC filings: fiscal
period labels, exact dates and status (filed / earnings release only / not yet reported).

1. answer_periods: the periods the question asks about, using the calendar's labels. Map
   calendar-date wording (e.g. "April-June 2026") to the fiscal period with those dates.
2. documents (at most 6): the filings that contain the facts.
   - earnings_release: headline results, segment tables, non-GAAP reconciliations, management
     commentary and the outlook (guidance) for the NEXT period.
   - periodic_report (10-Q/10-K): full financial statements, notes (segments, remaining
     performance obligations, share repurchases), MD&A explanations, risk factors.
   - Guidance for a period was published in the earnings release of the PRECEDING period.
   - Calculations need every input: e.g. the prior-year period for growth; quarterly reports
     also contain year-to-date figures.
   - Only request periods whose status allows it: a periodic_report needs status "filed";
     an earnings_release needs an earnings release listed for that period.
3. availability_notes: if a requested period is not yet reported, the company is not an SEC
   registrant, or the metric may not be disclosed, say so. Never plan to estimate it.
4. recent_filings_days: set it (e.g. 45) only when the question is about recent events.
5. searches (at most {MAX_SEARCHES}, each costs credits): use the web only for what filings
   can't give: recent news and events (topic "news" with days_back), management remarks on
   earnings calls, industry context, or companies that don't file with the SEC. Many companies
   give guidance and quantify one-time effects only on the earnings call, not in the release:
   when the question asks for guidance or management's explanation, add one search for that
   call's coverage. Use none when the filings answer the question. Every query names the company."""


def _calendar_text(companies: list[Company]) -> str:
    blocks = []
    for c in companies:
        if not c.resolved:
            blocks.append(f"{c.name}: NOT an SEC registrant ({c.reason}); no filings available.")
            continue
        lines = "\n".join("  " + p.describe() for p in c.periods[-12:])
        blocks.append(f"{c.name} (ticker {c.ticker}, fiscal year ends {c.fiscal_year_end}):\n{lines}")
    return "\n\n".join(blocks)


def plan(question: str, companies: list[Company], today: date, callbacks=None) -> tuple[Plan, dict]:
    user = f"Today: {today}\nQuestion: {question}\n\nCompany calendars:\n{_calendar_text(companies)}"
    result, tokens = structured(Plan, PROMPT, user, callbacks=callbacks)
    return validate(result, companies), tokens


def validate(result: Plan, companies: list[Company]) -> Plan:
    """Drop choices that don't exist in the calendar and enforce limits."""
    periods = {(c.ticker, p.label): p for c in companies if c.resolved for p in c.periods}
    notes = list(result.availability_notes)
    keep_periods = []
    for ref in result.answer_periods:
        if (ref.ticker, ref.label) in periods:
            keep_periods.append(ref)
        else:
            notes.append(f"{ref.ticker} {ref.label} is not in the company's reporting calendar")
    docs = []
    for d in result.documents:
        p = periods.get((d.ticker, d.period))
        available = p and (p.report if d.document == "periodic_report" else p.earnings_releases)
        if available and d not in docs:
            docs.append(d)
    searches = [s for s in result.searches if 0 < len(s.query) < 400][:MAX_SEARCHES]
    return result.model_copy(update={"answer_periods": keep_periods, "documents": docs[:6],
                                     "searches": searches, "availability_notes": notes})
