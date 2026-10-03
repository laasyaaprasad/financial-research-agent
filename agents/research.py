"""Collect evidence for a plan: SEC filing passages, XBRL facts and web results.

Every evidence item carries its source URL, publication/filing date, the period it
covers and a text body the writer must quote from. SEC data is free and preferred;
Tavily is used only for the plan's searches, at about 1 credit per search plus one
extract call.
"""

from __future__ import annotations

import asyncio
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

from agents import tracing
from agents.company import Company
from agents.edgar import ARCHIVES, EdgarClient, EdgarError
from agents.fiscal import Filing, filings_as_of
from agents.planner import Plan, SearchRequest

PASSAGE_CHARS = 1500
MAX_EXTRACT_URLS = 3
# Social and user-generated sites are not credible sources for an analyst brief.
EXCLUDED_DOMAINS = ["facebook.com", "linkedin.com", "x.com", "twitter.com", "instagram.com", "tiktok.com",
                    "reddit.com", "youtube.com", "quora.com"]


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


def _xbrl_evidence(company: Company, filings: list[Filing], query: list[str], client: EdgarClient) -> list[Evidence]:
    """Exact tagged values reported in the given filings, most relevant concepts first."""
    accessions = {f.accession: f for f in filings}
    rows: dict[str, list[tuple[float, str]]] = {}
    q = set(query)
    for namespace in client.companyfacts(company.cik).get("facts", {}).values():
        for concept, data in namespace.items():
            label = data.get("label") or concept
            relevance = len(q & set(terms(label + " " + re.sub(r"([a-z])([A-Z])", r"\1 \2", concept))))
            if not relevance:
                continue
            for unit, facts in data.get("units", {}).items():
                for fact in facts:
                    f = accessions.get(fact.get("accn"))
                    if not f:
                        continue
                    span = f"{fact['start']} to {fact['end']}" if fact.get("start") else f"as of {fact['end']}"
                    value = f"{fact['val']:,}" if isinstance(fact["val"], (int, float)) else str(fact["val"])
                    rows.setdefault(f.accession, []).append((relevance, f"{label} ({concept}): {value} {unit}, {span}"))
    out = []
    for acc, lines in rows.items():
        f = accessions[acc]
        best = [line for _, line in sorted(lines, key=lambda r: -r[0])[:40]]
        out.append(Evidence(id="", url=f"{ARCHIVES}/{int(company.cik)}/{acc.replace('-', '')}/",
                            title=f"{company.name} XBRL data tagged in {f.form} filed {f.filed}",
                            tier="primary", date=str(f.filed), text="\n".join(sorted(set(best)))))
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
    for company, filings in used_filings.values():
        evidence += _xbrl_evidence(company, [f for f in filings if f.form not in ("8-K", "6-K")], query, client)
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


async def web_evidence(question: str, plan: Plan, companies: list[Company], today: date, web: Web) -> list[Evidence]:
    if not plan.searches:
        return []

    async def search(s):
        params = {"query": s.query[:399], "topic": s.topic, "search_depth": "basic", "max_results": 5,
                  "end_date": str(today), "exclude_domains": EXCLUDED_DOMAINS}
        if s.days_back:
            params["start_date"] = str(today - timedelta(days=s.days_back))
        return await web.call("search", **params)

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
    top = [r["url"] for r in ranked[:MAX_EXTRACT_URLS]]
    response = await web.call("extract", urls=top, query=question[:399], chunks_per_source=5, extract_depth="basic")
    for r in response.get("results", []):
        extracted[r["url"]] = r.get("raw_content") or ""

    return [Evidence(id="", url=r["url"], title=r.get("title", ""),
                     tier="primary" if _is_company_source(r["url"], companies) else "secondary",
                     date=_published(r.get("published_date")),
                     text=(extracted.get(r["url"]) or r.get("content") or "")[:6000])
            for r in ranked]


async def gap_evidence(question: str, gaps: list[str], companies: list[Company], today: date, web: Web) -> list[Evidence]:
    """One targeted search per item the writer couldn't find (at most two), plus one extract."""
    names = " ".join(c.name for c in companies)
    searches = [SearchRequest(purpose="fill a gap", query=f"{names} {gap}"[:200]) for gap in gaps[:2]]
    return await web_evidence(question, Plan(metrics=gaps, searches=searches), companies, today, web)


def number_evidence(items: list[Evidence]) -> list[Evidence]:
    for i, item in enumerate(items, start=1):
        item.id = f"E{i}"
    return items


def to_dicts(items: list[Evidence]) -> list[dict]:
    return [asdict(e) for e in items]
