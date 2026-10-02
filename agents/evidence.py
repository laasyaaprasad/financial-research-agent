"""Source-bound evidence with explicit numeric units, periods and dates."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from typing import Literal

from pydantic import Field, model_validator

from agents.company import ALIASES, normalized
from agents.schemas import Entity, Period, Record, Resolution


def canonical_url(url: str) -> str:
    p = urlsplit(url.strip())
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:
        raise ValueError('Evidence requires a public HTTP URL')
    query = [(k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith('utm_')]
    return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/'),urlencode(query),''))


def identity(prefix: str, data) -> str:
    return prefix + hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:12]


def published_day(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        try:
            return parsedate_to_datetime(value).date()
        except (TypeError, ValueError):
            return None


def names(entity: Entity) -> set[str]:
    values = {entity.requested_name, entity.company_name or '', entity.ticker or ''}
    values.update(k for k,v in ALIASES.items() if v == entity.ticker)
    legal = re.sub(r'\b(?:inc|corp|corporation|company|co|ltd|limited|plc|incorporated)\b', '', (entity.company_name or '').lower())
    values.add(re.sub(r'[^a-z0-9 ]', '', legal).strip())
    tokens = legal.split()
    if len(tokens) >= 2 and tokens[0].lower() in {'novo','taiwan'}:
        values.add(' '.join(tokens[:2]))
    if tokens and len(tokens[0]) >= 4 and tokens[0].lower() not in {'the','taiwan','novo'}:
        values.add(tokens[0])
    return {v.lower().strip() for v in values if len(v.strip()) >= 3}


def matching_entities(title: str, content: str, url: str, resolution: Resolution) -> list[Entity]:
    host = (urlsplit(url).hostname or '').lower()
    sec = host == 'sec.gov' or host.endswith('.sec.gov')
    archive = re.search(r'/edgar/data/(\d+)/',url,re.I)
    api_cik = re.search(r'CIK(\d{10})',url,re.I)
    cik = (archive or api_cik).group(1).lstrip('0') if archive or api_cik else None
    text = (title+' '+content).lower()
    result = []
    for entity in resolution.entities:
        if sec and cik:
            if entity.cik and entity.cik.lstrip('0') == cik:
                result.append(entity)
            continue
        if any(re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',text) for name in names(entity)):
            result.append(entity)
    return result


def source_tier(url: str, entities: list[Entity]) -> str:
    host = (urlsplit(url).hostname or '').lower()
    if host == 'sec.gov' or host.endswith('.sec.gov'):
        return 'primary'
    labels = host.removeprefix('www.').split('.')
    root = labels[-2] if len(labels) >= 2 else labels[0]
    brands = {normalized(name) for e in entities for name in names(e)}
    # An 'ir'/'investor' prefix alone never grants primary status, nor does a
    # lookalike suffix. Company domains must match the resolved reporting brand.
    return 'primary' if normalized(root) in brands else 'secondary'


class Source(Record):
    id: str
    url: str
    title: str
    tier: Literal['primary','secondary']
    basis: Literal['page','snippet']
    content: str
    company_tickers: list[str] = Field(default_factory=list)
    published_date: date | None = None
    as_of: date
    tavily_request_ids: list[str] = Field(default_factory=list)
    relevance_score: float | None = None
    origin: Literal['search','extract','sec_xbrl'] = 'search'


class Fact(Record):
    id: str
    source_id: str
    description: str
    value: float | None = None
    unit: str | None = None
    period: Period | None = None
    as_of: date
    quote: str

    @model_validator(mode='after')
    def complete_numeric(self):
        if self.value is not None and (self.period is None or not self.unit):
            raise ValueError('Numeric evidence requires a period and unit')
        return self


class Note(Record):
    researcher: str
    text: str
    source_ids: list[str]


class EvidenceBundle(Record):
    question: str
    as_of: date
    sources: list[Source]
    facts: list[Fact]
    notes: list[Note]
    warnings: list[str]
    tavily_credits: float
    tokens: dict[str,int]


class EvidenceStore:
    def __init__(self, resolution: Resolution, as_of: date):
        self.resolution,self.as_of=resolution,as_of
        self.sources: dict[str, Source] = {}
        self.facts: dict[str, Fact] = {}
        self._parts: dict[str, set[str]] = {}

    def add_source(self, url: str, title: str, content: str, *, basis='snippet', published_date=None,
                   request_id=None, score=None, origin='search') -> Source | None:
        url = canonical_url(url)
        published = published_day(published_date)
        if published and published > self.as_of:
            return None
        entities = matching_entities(title,content,url,self.resolution)
        if not entities:
            return None
        sid = identity('S',url)
        source = Source(id=sid,url=url,title=title,tier=source_tier(url,entities),basis=basis,content=content,
                        company_tickers=sorted({e.ticker for e in entities if e.ticker}),as_of=self.as_of,
                        published_date=published,tavily_request_ids=[request_id] if request_id else [],
                        relevance_score=score,origin=origin)
        old=self.sources.get(sid)
        if old:
            self._parts[sid].add(content)
            old.content='\n\n'.join(sorted(self._parts[sid]))
            if basis=='page': old.basis='page'
            if request_id and request_id not in old.tavily_request_ids: old.tavily_request_ids.append(request_id)
            old.company_tickers=sorted(set(old.company_tickers+source.company_tickers))
            old.title=min(old.title,title)
            dates=[d for d in (old.published_date,published) if d]
            old.published_date=max(dates) if dates else None
            scores=[s for s in (old.relevance_score,score) if s is not None]
            old.relevance_score=max(scores) if scores else None
            ranks={'search':0,'extract':1,'sec_xbrl':2}
            if ranks[origin] > ranks[old.origin]: old.origin=origin
            return old
        self.sources[sid]=source
        self._parts[sid]={content}
        return source

    def add_fact(self, source: Source, description: str, quote: str, *, value=None,unit=None,period=None) -> Fact:
        normalize=lambda t: re.sub(r'\s+',' ',t).strip().lower()
        if not quote or normalize(quote) not in normalize(source.content):
            raise ValueError('Evidence quote is not in the source')
        if value is not None:
            numbers=[]
            for token in re.findall(r'\(?\s*[$€£]?\s*-?\d[\d,]*(?:\.\d+)?\)?',quote):
                number=float(re.sub(r'[^\d.\-]','',token))
                numbers.append(-abs(number) if token.strip().startswith('(') and token.endswith(')') else number)
            if not any(abs(n-value) <= max(1e-8, abs(value)*1e-8) for n in numbers):
                raise ValueError('Numeric evidence must copy a displayed number; conversions belong in calculations')
        fid=identity('F',[source.id,description,value,unit,period.model_dump(mode='json') if period else None,quote])
        fact=Fact(id=fid,source_id=source.id,description=description,quote=quote,value=value,unit=unit,period=period,as_of=self.as_of)
        self.facts[fid]=fact
        return fact
