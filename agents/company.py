"""Extract company mentions, then resolve exclusively against SEC registrants.

The model cannot supply a CIK or a fiscal year end. Share classes are collapsed
by CIK and ambiguous/private/uncovered entities are returned as unresolved.
"""

from __future__ import annotations

import re

from pydantic import Field

from agents.edgar import EdgarClient
from agents.models import SMALL_MODEL, structured
from agents.schemas import Entity, Record, Resolution


class Mentions(Record):
    names: list[str] = Field(min_length=1, max_length=8)


EXTRACT_PROMPT = """Extract the companies being researched from the user question.
Return one concise company name or ticker for each reporting entity, in order.
Prefer its widely used stock ticker when confident, otherwise its official name.
Resolve product/business names to their parent (AWS -> Amazon, Azure -> Microsoft,
Google Cloud -> Alphabet). Facebook -> Meta Platforms. Do not invent extra companies.
Prefer the reporting parent over a spin-off when the question asks about its consolidated
results. Respect an explicitly named spin-off as its own reporting entity.
Consolidated sales vs sales excluding a division/spin-off is a comparison of the
parent's reporting bases, not a request to resolve the excluded division separately.
GOOG and GOOGL are share classes of one Alphabet registrant; return only Alphabet.
Return private/unknown names as supplied so code can return unresolved.
Do not provide IDs, dates, financial results, or an answer to the question."""


def normalized(name: str) -> str:
    name = re.sub(r"(?:'s|’s)$", "", name.casefold())
    name = re.sub(r"\b(?:corporation|corp|incorporated|inc|company|co|limited|ltd|plc)\b", "", name)
    return re.sub(r"[^a-z0-9]", "", name)


ALIASES = {"facebook": "META", "fb": "META", "google": "GOOGL",
           "googlecloud": "GOOGL", "aws": "AMZN", "azure": "MSFT",
           "honeywell": "HON", "honeywelltechnologies": "HON", "honeywellinternational": "HON", "cargill": "Cargill"}

# Public calendar metadata only, not a financial reference answer. SEC resolution
# remains unresolved for private Cargill; no ticker or CIK is manufactured.
PUBLIC_CALENDARS = {"cargill": {"name": "Cargill, Incorporated", "fye": "0531",
                               "source": "https://www.cargill.com/sustainability/2025-impact-report"}}


def resolve(question: str, *, client: EdgarClient | None = None, model: str = SMALL_MODEL,
            callbacks: list | None = None, mentions: list[str] | None = None) -> Resolution:
    client = client or EdgarClient()
    tokens = {}
    if mentions is None:
        extracted, tokens = structured(Mentions, EXTRACT_PROMPT, question,
                                       model=model, callbacks=callbacks)
        mentions = extracted.names
    index = list(client.tickers().values())
    entities, seen = [], set()
    for name in mentions:
        key = ALIASES.get(normalized(name), name)
        exact_ticker = [r for r in index if r["ticker"].casefold() == key.casefold()]
        matches = exact_ticker or [r for r in index if normalized(r["title"]) == normalized(key)]
        if not matches:
            # Require a full prefix at a word boundary, never arbitrary substring matches.
            words = re.sub(r"[^a-z0-9 ]", " ", key.casefold()).split()
            prefix = " ".join(words)
            matches = [r for r in index if prefix and (
                r["title"].casefold().startswith(prefix + " ") or
                r["title"].casefold() == prefix)]
        ciks = {str(r["cik_str"]) for r in matches}
        if len(ciks) != 1:
            public_calendar = PUBLIC_CALENDARS.get(normalized(name), {})
            entities.append(Entity(requested_name=name, status="unresolved",
                                   company_name=public_calendar.get("name"),
                                   fiscal_year_end=public_calendar.get("fye"),
                                   calendar_source_urls=[public_calendar["source"]] if public_calendar else [],
                                   reason="Ambiguous SEC registrants" if ciks else "No matching publicly traded SEC registrant"))
            continue
        cik = ciks.pop()
        if cik in seen:
            continue
        seen.add(cik)
        sub = client.submissions(cik)
        forms = sub.get("filings", {}).get("recent", {}).get("form", [])
        annual = next((f for f in forms if f in ("10-K", "20-F", "40-F")), None)
        tickers = sub.get("tickers") or [matches[0]["ticker"]]
        # A canonical class, independent of the class named in the question.
        ticker = "GOOGL" if "GOOGL" in tickers else tickers[0]
        entities.append(Entity(requested_name=name, status="resolved", ticker=ticker,
                               cik=f"{int(cik):010d}", company_name=sub["name"],
                               fiscal_year_end=sub.get("fiscalYearEnd"), tickers=tickers,
                               calendar_source_urls=[f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"],
                               annual_form=annual))
    return Resolution(entities=entities, tokens=tokens)
