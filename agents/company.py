"""Resolve the companies in a question to SEC registrants, or ask the user which one they mean.

The model only names the companies (and a ticker if it knows one), and says when the
question can't be researched without a clarification. Code looks the names up in SEC's
ticker list, then in EDGAR's company search for filers without a ticker, so CIKs and fiscal
calendars always come from SEC data. Anything that doesn't match exactly one currently
reporting registrant is returned unresolved (e.g. private or deregistered companies).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from pydantic import BaseModel, Field

from agents.edgar import EdgarClient, EdgarError
from agents.fiscal import PERIODIC, Period, calendar, filings_as_of
from agents.llm import structured


class Mention(BaseModel):
    as_written: str = Field(default="", description="The words in the question that refer to this company")
    name: str = Field(description="Company name as the parent reporting company")
    ticker: str | None = Field(default=None, description="Its primary US stock ticker, if publicly listed and known")
    aliases: list[str] = Field(default_factory=list, description="Other names the press uses for it: short name, "
                               "former name, best-known brands; at most 4")


class Mentions(BaseModel):
    companies: list[Mention] = Field(description="Each distinct company the question asks about, in order")
    clarification: str | None = Field(default=None, description="One short question to ask the user, only when "
                                      "the request can't be researched without it; otherwise null")


PROMPT = """List the companies a financial analyst's question is about.
- Use the parent reporting company: map products, brands, segments, subsidiaries and former
  names to the company that files the financial reports (e.g. a cloud unit -> its parent).
- Analysts type tersely: a lowercase word or a lone ticker may be a company; fix obvious typos. A short
  abbreviation after a company or ticker is normally a metric (shorthand for gross margin, revenue, EPS and
  the like), not a second company, even when it matches another ticker.
- One entry per company, even if several share classes or tickers are mentioned.
- Give the primary US ticker only if you are confident it is publicly listed; otherwise null.
- Set `clarification` only when there is no reasonable reading, and then list no companies:
  - no company is named or implied;
  - a name that plausibly means several different public companies (e.g. a common word or a
    place name shared by several listed companies), and nothing else in the question (its metric,
    industry or wording) singles one out; list the candidates with tickers;
  - the text is not a question about companies (unreadable, or a bare term with no company);
  - a screen or ranking across a whole sector or market: say that ranking a universe of
    companies is out of scope and ask which companies to compare.
  If one reading is clearly most likely, use it instead of asking.
- Do not answer the question."""


@dataclass
class Company:
    requested: str
    name: str
    ticker: str | None = None
    cik: str | None = None
    fiscal_year_end: str | None = None  # MMDD from SEC
    periods: list[Period] = field(default_factory=list)
    resolved: bool = True
    reason: str = ""
    aliases: list[str] = field(default_factory=list)  # other names sources use: the user's words, short names, brands


def _norm(name: str) -> str:
    name = re.sub(r"\b(corporation|corp|incorporated|inc|company|co|holdings|plc|ltd|limited|the)\b", "", name.lower())
    return re.sub(r"[^a-z0-9]", "", name)


def _aliases(m: Mention) -> list[str]:
    return list(dict.fromkeys(a for a in [m.as_written, m.name, *m.aliases[:4]] if a and a.strip()))


def _search(client: EdgarClient, name: str) -> list[str]:
    """EDGAR company search, which matches name prefixes: try the plain name, then without legal suffixes."""
    plain = re.sub(r"\s+", " ", re.sub(r"[^\w&\s-]", " ", name)).strip()
    short = re.sub(r"\b(corporation|corp|incorporated|inc|company|co|plc|ltd|limited)\s*$", "", plain, flags=re.I).strip()
    for candidate in dict.fromkeys([plain, short]):
        try:
            found = client.company_search(candidate)
        except EdgarError:
            found = []
        if found:
            return found
    return []


def _last_periodic_report(client: EdgarClient, cik: str, today: date) -> date | None:
    return max((f.filed for f in filings_as_of(client, cik, today) if f.form in PERIODIC), default=None)


def resolve(question: str, today: date, client: EdgarClient,
            callbacks=None) -> tuple[list[Company], str | None, dict]:
    """Returns (companies, clarification question or None, token usage)."""
    mentions, tokens = structured(Mentions, PROMPT, question, reasoning="low", callbacks=callbacks)
    if mentions.clarification:
        return [], mentions.clarification, tokens
    rows = list(client.tickers().values())
    companies: list[Company] = []
    for m in mentions.companies:
        matches = [r for r in rows if m.ticker and r["ticker"].upper() == m.ticker.upper().replace(".", "-")]
        if not matches:
            matches = [r for r in rows if _norm(r["title"]) == _norm(m.name)]
        ciks = {str(r["cik_str"]) for r in matches}
        if not ciks:
            # Filers without a listed ticker; they must still be filing periodic reports.
            found = _search(client, m.name)
            if len(found) == 1:
                last = _last_periodic_report(client, found[0], today)
                if last and last >= today - timedelta(days=400):
                    ciks = set(found)
                else:
                    companies.append(Company(requested=m.as_written or m.name, name=m.name, resolved=False, reason=(
                        f"no longer files periodic reports with the SEC (last one filed {last})"), aliases=_aliases(m)))
                    continue
            elif found:
                ciks = set(found)
        if len(ciks) != 1:
            reason = "matches several SEC registrants" if ciks else "no SEC-registered public company with this name"
            companies.append(Company(requested=m.as_written or m.name, name=m.name, resolved=False, reason=reason,
                                     aliases=_aliases(m)))
            continue
        cik = ciks.pop()
        if any(c.cik == cik for c in companies):
            continue
        sub = client.submissions(cik)
        ticker = (sub.get("tickers") or [r["ticker"] for r in matches] or [None])[0]
        companies.append(Company(requested=m.as_written or m.name, name=sub["name"], ticker=ticker or f"CIK{cik}",
                                 cik=cik, fiscal_year_end=sub.get("fiscalYearEnd"),
                                 periods=calendar(client, cik, today), aliases=_aliases(m)))
    return companies, None, tokens
