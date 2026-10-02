"""Meaningful retrieval invariants; all service calls are simulated offline."""

import asyncio
from contextlib import nullcontext
from datetime import date

import pytest
from pydantic import ValidationError

from agents.evidence import EvidenceStore, Fact, canonical_url, source_tier
from agents.researchers import NoteDraft, FactDraft, research, replay
from agents.retrieval import Retrieval
from agents.schemas import Brief, Entity, Period, ResearchPlan, Resolution, Search

TODAY=date(2026,10,1)
COMPANY=Entity(requested_name='Acme',status='resolved',ticker='ACME',cik='0000000001',company_name='Acme Inc.',fiscal_year_end='1231')
RESOLUTION=Resolution(entities=[COMPANY])
PERIOD=Period(label='FY2025',start=date(2025,1,1),end=date(2025,12,31),tickers=['ACME'],reported=True,basis='filing')


@pytest.fixture(autouse=True)
def disable_tracing(monkeypatch):
    monkeypatch.setenv('LANGFUSE_PUBLIC_KEY','')
    monkeypatch.setenv('LANGFUSE_SECRET_KEY','')


class FakeTavily:
    def __init__(self): self.calls=[]
    async def search(self, **p):
        self.calls.append(('search',p));await asyncio.sleep(0)
        return dict(request_id='search-'+p['query'],usage={'credits':1},results=[
            dict(url='https://investor.acme.com/earnings',title='Acme earnings',content='Acme revenue was $100 million in FY2025.',score=.9),
            dict(url='https://other.com/',title='Other company',content='Other revenue was $100 million.',score=.99),
            dict(url='https://acme.com/weak',title='Acme unrelated',content='Acme parking',score=.1),
            dict(url='https://acme.com/future',title='Acme future',content='Acme future revenue',score=.99,published_date='2027-01-01'),
        ])
    async def extract(self, **p):
        self.calls.append(('extract',p))
        return dict(request_id='extract-id',usage={'credits':1},results=[dict(url=u,raw_content='Acme revenue was $100 million in FY2025.') for u in p['urls']])
    async def map(self, **p):
        self.calls.append(('map',p))
        return dict(request_id='map-id',usage={'credits':1},results=['https://investor.acme.com/earnings'])


class FakeSEC:
    def __init__(self,*args): pass
    def submissions(self,cik): return {'filings':{'recent':{}}}
    def companyfacts(self,cik):
        return {'facts':{'us-gaap':{'Revenues':{'label':'Revenue','units':{'USD':[dict(start='2025-01-01',end='2025-12-31',filed='2026-02-01',val=100000000,accn='1')]}}}}}


def fake_note(schema,system,payload,**kwargs):
    import json
    data=json.loads(payload)
    source=next(s for s in data['sources'] if 'Acme revenue was' in s['content'])
    return NoteDraft(text=f"Revenue evidence [{source['id']}].",source_ids=[source['id']],facts=[
        FactDraft(source_id=source['id'],description='Revenue',quote='Acme revenue was $100 million in FY2025.',value=100,unit='USD million',period_index=0)
    ]), {'input':50,'output':20}


def test_filters_company_score_and_future_dates_and_replays_exactly(tmp_path,monkeypatch):
    fake=FakeTavily()
    original=Retrieval.__init__
    def injected(self,*args,**kwargs):
        if not kwargs.get('replay'): kwargs['client']=fake
        original(self,*args,**kwargs)
    monkeypatch.setattr(Retrieval,'__init__',injected)
    monkeypatch.setattr('agents.researchers.RecordingSEC',FakeSEC)
    monkeypatch.setattr('agents.researchers.structured',fake_note)
    plan=ResearchPlan(brief=Brief(metrics=['revenue'],answer_type='number',may_be_unreported=False),periods=[PERIOD],edgar_fetches=[],
                      searches=[Search(researcher=r,reason='test',query=f'Acme {r} FY2025 revenue') for r in ['financials','company']],search_budget=16,model='fake')
    bundle=asyncio.run(research('Acme revenue FY2025',RESOLUTION,plan,TODAY,tmp_path))
    assert {s.url for s in bundle.sources}=={'https://data.sec.gov/api/xbrl/companyfacts/CIK0000000001.json','https://investor.acme.com/earnings'}
    assert all(f.period and f.unit and f.as_of==TODAY for f in bundle.facts if f.value is not None)
    assert {f.value for f in bundle.facts}=={100,100000000}
    calls=len(fake.calls)
    monkeypatch.setattr('agents.researchers.structured',lambda *a,**kw:pytest.fail('Replay called a model'))
    result=replay(tmp_path)
    assert result==bundle and len(fake.calls)==calls


def test_parallel_budget_and_dedup_are_hard_limits(tmp_path):
    fake=FakeTavily();client=Retrieval(tmp_path,budget=2,client=fake)
    async def run():
        return await asyncio.gather(*(client.call('search',query=f'q{i}',search_depth='advanced') for i in range(6)))
    results=asyncio.run(run())
    assert len(fake.calls)<=2 and client.used<=2
    assert any(r.get('budget_exhausted') for r in results)
    second=Retrieval(tmp_path/'dedup',budget=2,client=fake)
    async def duplicate():
        return await asyncio.gather(*(second.call('search',query='same',search_depth='advanced') for _ in range(4)))
    before=len(fake.calls);responses=asyncio.run(duplicate())
    assert len(fake.calls)-before==1 and all(r==responses[0] for r in responses)


@pytest.mark.parametrize('url,tier',[
    ('https://investor.acme.com/results','primary'),('https://www.sec.gov/Archives/','primary'),
    ('https://investor.other.com/acme','secondary'),('https://acme.com.evil.org/','secondary'),
    ('https://acme-fans.com/','secondary'),
])
def test_hostname_tiers_do_not_trust_ir_prefix_or_lookalikes(url,tier):
    assert source_tier(url,[COMPANY])==tier


def test_wrong_sec_registrant_rejected_even_if_company_is_mentioned():
    store=EvidenceStore(RESOLUTION,TODAY)
    assert store.add_source('https://www.sec.gov/Archives/edgar/data/2/fund.htm','Acme investment','Acme revenue') is None


def test_url_dedup_and_merge_order_are_deterministic():
    def make(contents):
        store=EvidenceStore(RESOLUTION,TODAY)
        for content in contents:
            store.add_source('https://acme.com/results/?utm_source=x#heading','Acme',content)
        return list(store.sources.values())
    assert make(['Acme a','Acme b'])==make(['Acme b','Acme a'])
    assert canonical_url('https://acme.com/results/?utm_source=x#heading')=='https://acme.com/results'


def test_numeric_evidence_needs_unit_period_and_literal_quote():
    store=EvidenceStore(RESOLUTION,TODAY)
    source=store.add_source('https://acme.com/','Acme','Acme revenue was $100 million in FY2025.')
    with pytest.raises(ValidationError):
        store.add_fact(source,'Revenue','Acme revenue was $100 million in FY2025.',value=100)
    with pytest.raises(ValueError,match='displayed number'):
        store.add_fact(source,'Revenue','Acme revenue was $100 million in FY2025.',value=100000000,unit='USD',period=PERIOD)
    with pytest.raises(ValueError,match='quote'):
        store.add_fact(source,'Revenue','invented 100',value=100,unit='USD million',period=PERIOD)


def test_missing_replay_response_never_falls_back_to_network(tmp_path):
    client=Retrieval(tmp_path,replay=True)
    with pytest.raises(ValueError,match='Missing recorded'):
        asyncio.run(client.call('search',query='Acme'))


def test_retrieval_records_do_not_save_headers_or_credentials(tmp_path,monkeypatch):
    monkeypatch.setenv('TAVILY_API_KEY','fake-secret-value')
    fake=FakeTavily()
    async def injected(**p):
        return {'results':[],'usage':{'credits':1},'error':'fake-secret-value','headers':{'Authorization':'fake-secret-value'}}
    fake.search=injected
    client=Retrieval(tmp_path,client=fake)
    asyncio.run(client.call('search',query='Acme'))
    raw=next(tmp_path.glob('*.json')).read_text()
    assert 'fake-secret-value' not in raw and 'Authorization' not in raw


def test_current_filing_is_added_when_plan_only_requests_comparative():
    from agents.researchers import selected_filings
    from agents.schemas import EdgarFetch
    class Metadata:
        def submissions(self,cik):
            return {'filings':{'recent':dict(form=['10-K','10-K'],reportDate=['2025-12-31','2024-12-31'],
                filingDate=['2026-02-01','2025-02-01'],accessionNumber=['1-26-1','1-25-1'],primaryDocument=['current.htm','prior.htm'])}}
    plan=ResearchPlan(brief=Brief(metrics=['revenue'],answer_type='number',may_be_unreported=False),periods=[PERIOD],
                     edgar_fetches=[EdgarFetch(ticker='ACME',cik=COMPANY.cik,form='10-K',period_end=date(2024,12,31),item='comparative')],
                     searches=[],search_budget=0,model='fake')
    docs=selected_filings(plan,RESOLUTION,Metadata(),TODAY)
    assert [d['url'].rsplit('/',1)[-1] for d in docs]==['current.htm','prior.htm']
    assert selected_filings(plan,RESOLUTION,Metadata(),date(2026,1,1))[0]['url'].endswith('prior.htm')


def test_quantity_question_does_not_accept_monetary_sales():
    from agents.researchers import add_xbrl
    store=EvidenceStore(RESOLUTION,TODAY)
    plan=ResearchPlan(brief=Brief(metrics=['unit sales'],answer_type='number',may_be_unreported=True),periods=[PERIOD],edgar_fetches=[],searches=[],search_budget=0,model='fake')
    add_xbrl(store,plan,RESOLUTION,FakeSEC())
    assert not store.facts


def test_negative_number_sign_is_not_silently_reversed():
    store=EvidenceStore(RESOLUTION,TODAY)
    source=store.add_source('https://acme.com/','Acme','Acme operating loss was ($12.5) million.')
    store.add_fact(source,'Operating loss','Acme operating loss was ($12.5) million.',value=-12.5,unit='USD million',period=PERIOD)
    with pytest.raises(ValueError,match='displayed number'):
        store.add_fact(source,'Operating loss','Acme operating loss was ($12.5) million.',value=12.5,unit='USD million',period=PERIOD)
