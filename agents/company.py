"""Resolve the companies in a question to SEC registrants.

The model only names the companies (and a ticker if it knows one). Code looks them up
in SEC's ticker list, so CIKs and fiscal calendars always come from SEC data. Anything
that doesn't match exactly one registrant is returned unresolved (e.g. private companies).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from pydantic import BaseModel, Field

from agents.edgar import EdgarClient
from agents.fiscal import Period, calendar
from agents.llm import structured


class Mention(BaseModel):
    name: str = Field(description="Company name as the parent reporting company")
    ticker: str | None = Field(default=None, description="Its primary US stock ticker, if publicly listed and known")


class Mentions(BaseModel):
    companies: list[Mention] = Field(description="Each distinct company the question asks about, in order")


PROMPT = """List the companies a financial analyst's question is about.
- Use the parent reporting company: map products, brands, segments, subsidiaries and former
  names to the company that files the financial reports (e.g. a cloud unit -> its parent).
- One entry per company, even if several share classes or tickers are mentioned.
- Give the primary US ticker only if you are confident it is publicly listed; otherwise null.
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


def _norm(name: str) -> str:
    name = re.sub(r"\b(corporation|corp|incorporated|inc|company|co|holdings|plc|ltd|limited|the)\b", "", name.lower())
    return re.sub(r"[^a-z0-9]", "", name)


def resolve(question: str, today: date, client: EdgarClient, callbacks=None) -> tuple[list[Company], dict]:
    mentions, tokens = structured(Mentions, PROMPT, question, reasoning="none", callbacks=callbacks)
    rows = list(client.tickers().values())
    companies: list[Company] = []
    for m in mentions.companies:
        matches = [r for r in rows if m.ticker and r["ticker"].upper() == m.ticker.upper().replace(".", "-")]
        if not matches:
            matches = [r for r in rows if _norm(r["title"]) == _norm(m.name)]
        ciks = {r["cik_str"] for r in matches}
        if len(ciks) != 1:
            reason = "matches several SEC registrants" if ciks else "no SEC-registered public company with this name"
            companies.append(Company(requested=m.name, name=m.name, resolved=False, reason=reason))
            continue
        cik = str(ciks.pop())
        if any(c.cik == cik for c in companies):
            continue
        sub = client.submissions(cik)
        companies.append(Company(requested=m.name, name=sub["name"], ticker=(sub.get("tickers") or [matches[0]["ticker"]])[0],
                                 cik=cik, fiscal_year_end=sub.get("fiscalYearEnd"),
                                 periods=calendar(client, cik, today)))
    return companies, tokens
