"""Collect evidence for a plan: SEC filing passages, XBRL facts and web results.

Every evidence item carries its source URL, publication/filing date, the period it
covers and a text body the writer must quote from. SEC data is free and preferred;
Tavily is used only for the plan's searches. `SearchConfig` sets how Tavily is called.
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import json
import math
import os
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from agents import tracing
from agents.company import Company
from agents.edgar import ARCHIVES, EdgarClient, EdgarError
from agents.fiscal import Filing, filings_as_of
from agents.llm import structured
from agents.planner import Plan, SearchRequest

PASSAGE_CHARS = 1500
MAX_EXTRACT_URLS = 3
# Social and user-generated sites are not credible sources for an analyst brief.
EXCLUDED_DOMAINS = ["facebook.com", "linkedin.com", "x.com", "twitter.com", "instagram.com", "tiktok.com",
                    "reddit.com", "youtube.com", "quora.com"]


@dataclass(frozen=True)
class SearchConfig:
    """How Tavily search is called. The defaults are the configuration evaluated in M5."""
    depth: str = "basic"           # "basic": page summaries, then one query-focused extract; "advanced": ranked chunks
    max_results: int = 5
    finance_topic: bool = False    # topic="finance" for searches the planner didn't mark as news
    company_sites: bool = False    # search the companies' own sites first; the open web if that finds little
    auto_parameters: bool = False  # Tavily chooses the topic; dates, depth and domains stay pinned


class Domains(BaseModel):
    domains: list[str] = Field(default_factory=list, description="Domains only, e.g. example.com")


@functools.lru_cache(maxsize=256)
def official_domains(company: str) -> tuple[str, ...]:
    """The company's own web domains (corporate site, investor relations, newsroom), as the model knows them."""
    try:
        result, _ = structured(Domains, "List the official web domains of this company: corporate site, investor "
                               "relations and newsroom. At most 4; none if you aren't sure.", company, reasoning="none")
    except ValueError:
        return ()
    return tuple(d.lower().strip().removeprefix("https://").removeprefix("www.").strip("/")
                 for d in result.domains if "." in d)[:4]


@dataclass
class Evidence:
    id: str
    url: str
    title: str
    tier: str              # "primary" (company filings/releases/IR) or "secondary"
    date: str | None       # filing or publication date
    text: str
    period: str | None = None


# ---------- passage ranking ----------

STOP = set("a an and are as at be by for from has have in is it its of on or that the this to was were what which with how did does do you".split())


# Common financial synonyms, so "sales" also finds "Revenue" and "profit" finds "income".
SYNONYMS = {"sales": ["revenue", "revenues"], "revenue": ["sales", "revenues"], "revenues": ["revenue", "sales"],
            "profit": ["income", "earnings"], "earnings": ["income", "profit"], "income": ["earnings", "profit"],
            "eps": ["earnings", "per", "share"], "capex": ["capital", "expenditures", "property", "equipment"],
            "buybacks": ["repurchases", "repurchase"], "guidance": ["outlook", "expects"], "outlook": ["guidance", "expects"]}


def terms(text: str) -> list[str]:
    words = [w for w in re.findall(r"[a-z][a-z0-9\-]+|\d{4}", text.lower()) if w not in STOP]
    return words + [s for w in words for s in SYNONYMS.get(w, [])]


def passages(text: str) -> list[str]:
    """Split document text into ~1,500-character passages along line boundaries."""
    out, current = [], ""
    for line in text.splitlines():
        if current and len(current) + len(line) > PASSAGE_CHARS:
            out.append(current)
            current = ""
        current += line + "\n"
    if current:
        out.append(current)
    return out


def top_passages(text: str, query: list[str], k: int) -> str:
    """BM25-ranked passages, kept in document order. Short documents are returned whole."""
    chunks = passages(text)
    if len(chunks) <= k:
        return text
    docs = [Counter(terms(c)) for c in chunks]
    avg = sum(sum(d.values()) for d in docs) / len(docs)
    df = Counter(t for d in docs for t in d)
    q = set(query)

    def score(d: Counter) -> float:
        length = sum(d.values()) or 1
        s = 0.0
        for t in q:
            if d[t]:
                idf = math.log(1 + (len(docs) - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * d[t] * 2.2 / (d[t] + 1.2 * (0.25 + 0.75 * length / avg))
        return s

    best = sorted(range(len(chunks)), key=lambda i: score(docs[i]), reverse=True)[:k]
    return "\n[...]\n".join(chunks[i].strip() for i in sorted(best))


# ---------- SEC evidence ----------

def _sec_documents(plan: Plan, companies: list[Company], today: date, client: EdgarClient):
    """(company, period label, document kind, filing, url, title) for every planned filing document."""
    by_ticker = {c.ticker: c for c in companies if c.resolved}
    docs = []
    for req in plan.documents:
        company = by_ticker.get(req.ticker)
        period = next((p for p in company.periods if p.label == req.period), None) if company else None
        if not period:
            continue
        if req.document == "periodic_report" and period.report:
            f = period.report
            docs.append((company, period.label, f, f.url, f"{company.name} {f.form} for {period.label} (filed {f.filed})"))
        elif req.document == "earnings_release" and period.earnings_releases:
            f = period.earnings_releases[0]
            for ex in _exhibits(client, company.cik, f):
                docs.append((company, period.label, f, ex["url"],
                             f"{company.name} earnings release for {period.label}, {f.form} {ex['type']} (filed {f.filed})"))
    if plan.recent_filings_days:
        since = today - timedelta(days=plan.recent_filings_days)
        for company in by_ticker.values():
            recent = [f for f in filings_as_of(client, company.cik, today) if f.form == "8-K" and f.filed >= since]
            for f in recent[:4]:
                for ex in _exhibits(client, company.cik, f) or [{"url": f.url, "type": "8-K"}]:
                    docs.append((company, None, f, ex["url"],
                                 f"{company.name} {f.form} current report, items {f.items} (filed {f.filed}) {ex['type']}"))
    return docs


def _exhibits(client: EdgarClient, cik: str, filing: Filing) -> list[dict]:
    """Press-release style exhibits (EX-99.x) of an 8-K/6-K."""
    try:
        return [d for d in client.exhibits(cik, filing.accession)
                if d["type"].upper().startswith("EX-99") and d["url"].lower().endswith((".htm", ".html"))][:3]
    except EdgarError:
        return []


MAX_CONCEPTS = 20
# Core income-statement lines (standard US-GAAP / IFRS tags) are always included; other concepts
# are ranked by how well their label matches the question.
CORE_CONCEPTS = {"Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "Revenue", "CostOfRevenue",
                 "CostOfGoodsAndServicesSold", "GrossProfit", "OperatingIncomeLoss", "ProfitLossFromOperatingActivities",
                 "NetIncomeLoss", "ProfitLoss", "EarningsPerShareDiluted", "DilutedEarningsLossPerShare"}


def _xbrl_evidence(company: Company, filings: list[Filing], query: list[str], client: EdgarClient) -> list[Evidence]:
    """Exact tagged values reported in the given filings: all facts of the most relevant concepts.

    A concept's relevance favours labels the question covers fully ("Revenues" beats
    "Comprehensive Income (Loss), Net of Tax, Attributable to Parent" for "revenue").
    """
    accessions = {f.accession: f for f in filings}
    q = set(query)
    by_filing: dict[str, dict[str, tuple[float, list[str]]]] = {}
    for namespace in client.companyfacts(company.cik).get("facts", {}).values():
        for concept, data in namespace.items():
            label = data.get("label") or concept
            words = set(terms(label + " " + re.sub(r"([a-z])([A-Z])", r"\1 \2", concept)))
            matched = len(q & words)
            if concept in CORE_CONCEPTS:
                relevance = 100.0
            elif not matched:
                continue
            else:
                first = (terms(label) or [""])[0]
                relevance = matched / math.sqrt(len(words)) + (1.0 if first in q else 0.0)
            for unit, facts in data.get("units", {}).items():
                for fact in facts:
                    f = accessions.get(fact.get("accn"))
                    if not f:
                        continue
                    span = f"{fact['start']} to {fact['end']}" if fact.get("start") else f"as of {fact['end']}"
                    value = f"{fact['val']:,}" if isinstance(fact["val"], (int, float)) else str(fact["val"])
                    entry = by_filing.setdefault(f.accession, {}).setdefault(concept, (relevance, []))
                    entry[1].append(f"{label} ({concept}): {value} {unit}, {span}")
    out = []
    for acc, concepts in by_filing.items():
        f = accessions[acc]
        top = sorted(concepts.values(), key=lambda c: -c[0])[:MAX_CONCEPTS]
        lines = sorted({line for _, facts in top for line in facts})
        out.append(Evidence(id="", url=f"{ARCHIVES}/{int(company.cik)}/{acc.replace('-', '')}/",
                            title=f"{company.name} XBRL data tagged in {f.form} filed {f.filed}",
                            tier="primary", date=str(f.filed), text="\n".join(lines)))
    return out


def sec_evidence(question: str, plan: Plan, companies: list[Company], today: date, client: EdgarClient) -> list[Evidence]:
    query = terms(question + " " + " ".join(plan.metrics))
    evidence, seen, used_filings = [], set(), {}
    for company, period, filing, url, title in _sec_documents(plan, companies, today, client):
        if url in seen:
            continue
        seen.add(url)
        try:
            text = client.text(url)
        except EdgarError:
            continue
        k = 8 if filing.form in ("8-K", "6-K") else 6
        evidence.append(Evidence(id="", url=url, title=title, tier="primary", date=str(filing.filed),
                                 text=top_passages(text, query, k), period=f"{company.ticker} {period}" if period else None))
        used_filings.setdefault(company.cik, (company, []))[1].append(filing)
    # Tagged financial data for every answer period, so multi-period tables don't need every filing
    # read in full. A fiscal Q4 is usually tagged only as full year and nine months, so include Q3 too.
    by_ticker = {c.ticker: c for c in companies if c.resolved}
    for ref in plan.answer_periods:
        company = by_ticker.get(ref.ticker)
        if not company:
            continue
        labels = [ref.label] + ([ref.label.replace("Q4", "Q3", 1)] if ref.label.startswith("Q4 ") else [])
        for p in company.periods:
            if p.label in labels and p.report:
                used_filings.setdefault(company.cik, (company, []))[1].append(p.report)
    for company, filings in used_filings.values():
        unique = list({f.accession: f for f in filings if f.form not in ("8-K", "6-K")}.values())
        evidence += _xbrl_evidence(company, unique, query, client)
    return evidence


# ---------- web evidence (Tavily) ----------

class Web:
    """Tavily calls with a response cache, so a run can be replayed without spending credits."""

    def __init__(self, cache_dir: Path | str, live: bool = True, project_id: str = "agent"):
        self.cache_dir = Path(cache_dir)
        self.live = live
        self.project_id = project_id
        self.credits = 0.0
        self.calls: list[dict] = []

    async def call(self, operation: str, **params) -> dict:
        key = hashlib.sha256(json.dumps([operation, params], sort_keys=True).encode()).hexdigest()
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text())["response"]
        if not self.live:
            return {"results": [], "error": "not cached"}
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"), project_id=self.project_id)
        with tracing.tool_span(f"tavily_{operation}", params) as span:
            try:
                response = await getattr(client, operation)(**params, include_usage=True)
            except Exception as exc:  # network/quota errors: record and continue without this source
                response = {"results": [], "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
            span.finish({"credits": (response.get("usage") or {}).get("credits", 0)})
        credits = (response.get("usage") or {}).get("credits", 0)
        self.credits += credits
        self.calls.append({"name": f"tavily_{operation}", "args": params, "credits": credits})
        if "error" not in response:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"operation": operation, "params": params, "response": response}))
        return response


def _published(value: str | None) -> str | None:
    """Tavily dates come as ISO strings or RFC 2822 ('Wed, 23 Sep 2026 14:00:00 GMT')."""
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        try:
            return parsedate_to_datetime(value).date().isoformat()
        except (TypeError, ValueError):
            return None


def _is_company_source(url: str, companies: list[Company]) -> bool:
    host = urlparse(url).netloc.lower()
    if host.split(".")[0] in ("investor", "investors", "ir"):
        return True
    names = [re.sub(r"[^a-z]", "", c.name.lower().split()[0]) for c in companies]
    domain = ".".join(host.split(".")[-2:])
    return any(n and len(n) >= 3 and n in domain for n in names)


def _mentions_company(result: dict, companies: list[Company]) -> bool:
    text = (result.get("title", "") + " " + result.get("content", "")).lower()
    for c in companies:
        tokens = [t for t in re.findall(r"[a-z]+", c.name.lower()) if len(t) >= 3 and t not in ("inc", "corp", "com", "the")]
        if (tokens and tokens[0] in text) or (c.ticker and re.search(rf"\b{c.ticker.lower()}\b", text)):
            return True
    return False


def _on(host: str, domains) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


async def web_evidence(question: str, plan: Plan, companies: list[Company], today: date, web: Web,
                       config: SearchConfig = SearchConfig()) -> list[Evidence]:
    if not plan.searches:
        return []
    own = [d for c in companies for d in official_domains(c.name)] if config.company_sites else []

    async def search(s, include=None):
        params = {"query": s.query[:399], "search_depth": config.depth, "max_results": config.max_results,
                  "end_date": str(today), "exclude_domains": EXCLUDED_DOMAINS}
        if config.auto_parameters:
            params["auto_parameters"] = True
        else:
            params["topic"] = "finance" if config.finance_topic and s.topic == "general" else s.topic
        if config.depth == "advanced":
            params["chunks_per_source"] = 3
        if s.days_back:
            params["start_date"] = str(today - timedelta(days=s.days_back))
        if include:
            params["include_domains"] = include
        return await web.call("search", **params)

    responses = []
    if own:
        responses = await asyncio.gather(*(search(s, own) for s in plan.searches))
        found = sum(1 for r in responses for x in r.get("results", []) if _on(urlparse(x["url"]).netloc.lower(), own))
        if found < 2:  # the company's own sites had little: search the open web too
            responses += await asyncio.gather(*(search(s) for s in plan.searches))
    else:
        responses = await asyncio.gather(*(search(s) for s in plan.searches))
    results: dict[str, dict] = {}
    for response in responses:
        for r in response.get("results", []):
            host = urlparse(r["url"]).netloc
            if "sec.gov" in host or r["url"] in results or not _mentions_company(r, companies):
                continue
            results[r["url"]] = r
    ranked = sorted(results.values(), key=lambda r: r.get("score", 0), reverse=True)[:6]
    if not ranked:
        return []

    extracted = {}
    if config.depth == "basic":  # basic search returns page summaries; extract the passages that matter
        top = [r["url"] for r in ranked[:MAX_EXTRACT_URLS]]
        response = await web.call("extract", urls=top, query=question[:399], chunks_per_source=5, extract_depth="basic")
        for r in response.get("results", []):
            extracted[r["url"]] = r.get("raw_content") or ""

    def tier(url: str) -> str:
        own_site = _is_company_source(url, companies) or _on(urlparse(url).netloc.lower(), own)
        return "primary" if own_site else "secondary"

    return [Evidence(id="", url=r["url"], title=r.get("title", ""), tier=tier(r["url"]),
                     date=_published(r.get("published_date")),
                     text=(extracted.get(r["url"]) or r.get("content") or "")[:6000])
            for r in ranked]


async def gap_evidence(question: str, gaps: list[str], companies: list[Company], today: date, web: Web,
                       config: SearchConfig = SearchConfig()) -> list[Evidence]:
    """One targeted search per item the writer couldn't find (at most two), plus one extract."""
    names = " ".join(c.name for c in companies)
    searches = [SearchRequest(purpose="fill a gap", query=f"{names} {gap}"[:200]) for gap in gaps[:2]]
    return await web_evidence(question, Plan(metrics=gaps, searches=searches), companies, today, web, config)


def number_evidence(items: list[Evidence]) -> list[Evidence]:
    for i, item in enumerate(items, start=1):
        item.id = f"E{i}"
    return items


def to_dicts(items: list[Evidence]) -> list[dict]:
    return [asdict(e) for e in items]
