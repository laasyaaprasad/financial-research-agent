from datetime import date
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from agents.calendar import FiscalCalendar
from agents.company import resolve
from agents.edgar import EdgarClient, EdgarError
from agents.planner import FetchChoice, PeriodChoice, PlanDraft, SearchChoice, catalog_for, lookup_period, materialize, plan, required_researchers
from agents.periods import explicit_periods
from agents.schemas import Brief, Period, ResearchPlan, Search
from evals.planner import nebius_only_network, period_identity

TODAY = date(2026, 10, 1)
FIXTURES = Path(__file__).parent / "fixtures" / "edgar"


@pytest.fixture
def client():
    return EdgarClient(FIXTURES, offline=True)


@pytest.mark.parametrize("name,ticker,cik", [
    ("Facebook", "META", "0001326801"), ("GOOG", "GOOGL", "0001652044"),
    ("GOOGL", "GOOGL", "0001652044"), ("Honeywell Technologies", "HON", "0000773840"),
    ("Honeywell Aerospace", "HONA", "0002089271"), ("Novo Nordisk", "NVO", "0000353278"),
    ("Cisco", "CSCO", "0000858877"), ("NVIDIA", "NVDA", "0001045810"),
])
def test_company_from_sec(client, name, ticker, cik):
    e = resolve("", client=client, mentions=[name]).entities[0]
    assert (e.ticker, e.cik) == (ticker, cik)
    assert e.company_name == client.submissions(e.cik)["name"]
    assert e.fiscal_year_end == client.submissions(e.cik)["fiscalYearEnd"]


def test_classes_deduplicate_by_cik(client):
    r = resolve("", client=client, mentions=["GOOG", "GOOGL", "Amazon", "Azure"])
    assert [e.ticker for e in r.entities] == ["GOOGL", "AMZN", "MSFT"]


@pytest.mark.parametrize("name", ["Cargill", "OpenAI", "Unknown Holdings", "Reliance Industries"])
def test_no_guess_for_uncovered_or_ambiguous_company(client, name):
    e = resolve("", client=client, mentions=[name]).entities[0]
    assert e.status == "unresolved" and e.cik is None and e.ticker is None


@pytest.mark.parametrize("ticker,kind,year,quarter,start,end", [
    ("NVDA", "annual", 2026, None, "2025-01-27", "2026-01-25"),
    ("NVDA", "quarter", 2027, 2, "2026-04-27", "2026-07-26"),
    ("COST", "quarter", 2026, 4, "2026-05-11", "2026-08-30"),
    ("AAPL", "annual", 2023, None, "2022-09-25", "2023-09-30"),
    ("AAPL", "quarter", 2026, 4, "2026-06-28", "2026-09-26"),
    ("MU", "annual", 2026, None, "2025-08-29", "2026-09-03"),
    ("MU", "quarter", 2026, 4, "2026-05-29", "2026-09-03"),
    ("DE", "ytd", 2026, 3, "2025-11-03", "2026-08-02"),
    ("TGT", "quarter", 2026, 2, "2026-05-03", "2026-08-01"),
    ("WMT", "quarter", 2027, 2, "2026-05-01", "2026-07-31"),
    ("NVO", "annual", 2025, None, "2025-01-01", "2025-12-31"),
])
def test_exact_calendar_boundaries(client, ticker, kind, year, quarter, start, end):
    entity = resolve("", client=client, mentions=[ticker]).entities[0]
    period = FiscalCalendar(entity, client, TODAY).period(kind, year, quarter)
    assert period.start.isoformat() == start and period.end.isoformat() == end


def test_earnings_before_quarterly_filing(client):
    e = resolve("", client=client, mentions=["NKE"]).entities[0]
    p = FiscalCalendar(e, client, TODAY).period("quarter", 2027, 1)
    assert p.end == date(2026, 8, 31) and p.reported


def test_unreported_apple_and_no_future_leakage(client):
    e = resolve("", client=client, mentions=["AAPL"]).entities[0]
    cal = FiscalCalendar(e, client, TODAY)
    assert not cal.period("quarter", 2026, 4).reported
    assert all(r["filed"] <= TODAY.isoformat() for r in cal.rows)
    assert all(r["filingDate"] <= TODAY.isoformat() for r in cal.filings)


def test_derived_periods_and_dates():
    p = Period(label="Q1 FY2027", start=date(2026, 6, 1), end=date(2026, 8, 31), tickers=["ORCL"])
    catalog = {"p": p}
    ttm = materialize(PeriodChoice(keys=["p"], transform="ttm"), catalog, TODAY)
    nxt = materialize(PeriodChoice(keys=["p"], transform="next_twelve_months"), catalog, TODAY)
    news = materialize(PeriodChoice(transform="news_window", days=30), catalog, TODAY)
    comp = materialize(PeriodChoice(keys=["p"], transform="comp_window"), catalog, TODAY)
    assert (ttm.start, ttm.end) == (date(2025, 9, 1), date(2026, 8, 31))
    assert (nxt.start, nxt.end) == (date(2026, 9, 1), date(2027, 8, 31))
    assert (news.start, news.end) == (date(2026, 9, 2), TODAY)
    assert (comp.end-comp.start).days == 90


def test_unknown_key_and_disjoint_union_fail():
    with pytest.raises(ValueError, match="Unknown"):
        materialize(PeriodChoice(keys=["invented"]), {}, TODAY)
    catalog = {"a": Period(label="a", start=date(2026, 1, 1), end=date(2026, 3, 31)),
               "b": Period(label="b", start=date(2026, 7, 1), end=date(2026, 9, 30))}
    with pytest.raises(ValueError, match="non-contiguous"):
        materialize(PeriodChoice(keys=["a", "b"], transform="union"), catalog, TODAY)


def test_multi_company_union_keeps_ownership():
    catalog = {t: Period(label="Q2 2026", start=date(2026, 4, 1), end=date(2026, 6, 30), tickers=[t])
               for t in ["AMZN", "GOOGL"]}
    p = materialize(PeriodChoice(keys=list(catalog), transform="union"), catalog, TODAY)
    assert p.tickers == ["AMZN", "GOOGL"]


@pytest.mark.parametrize("budget", [0, 1, 2, 16])
def test_one_planning_call_and_hard_budget(client, monkeypatch, budget):
    calls = []
    def fake(schema, system, user, **kwargs):
        calls.append(user)
        return PlanDraft(brief=Brief(metrics=["revenue"], answer_type="number", may_be_unreported=False),
                         periods=[PeriodChoice(keys=["NVDA:FY2026"])], edgar_fetches=[],
                         searches=[SearchChoice(researcher="financials", reason="primary check", intent="a"*250)]), {}
    monkeypatch.setattr("agents.planner.structured", fake)
    entities = resolve("", client=client, mentions=["NVDA"])
    result = plan("What was NVIDIA's revenue?", entities, TODAY, budget, client=client)
    assert len(calls) == 1
    assert sum(s.credits for s in result.searches) <= budget
    assert all(len(s.query) < 400 for s in result.searches)
    assert "verified_by_human" not in calls[0] and "expected_periods" not in calls[0]


def test_future_actual_fetch_omitted_and_flagged(client, monkeypatch):
    def fake(*args, **kwargs):
        return PlanDraft(brief=Brief(metrics=["revenue"], answer_type="number", may_be_unreported=False),
                         periods=[PeriodChoice(keys=["AAPL:Q4 FY2027"])],
                         edgar_fetches=[FetchChoice(key="AAPL:Q4 FY2027", form="10-Q", item="revenue")], searches=[]), {}
    monkeypatch.setattr("agents.planner.structured", fake)
    result = plan("Apple future revenue", resolve("", client=client, mentions=["AAPL"]), TODAY, client=client)
    assert result.brief.may_be_unreported and not result.edgar_fetches


def test_offline_cache_missing_and_host_allowlist(tmp_path):
    c = EdgarClient(tmp_path, offline=True)
    with pytest.raises(EdgarError, match="No saved"):
        c.tickers()
    with pytest.raises(EdgarError, match="Only SEC"):
        c.get("https://example.com/")


def test_client_caches_public_body_not_headers(tmp_path, monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "test test@example.com")
    c = EdgarClient(tmp_path, transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"ok": True})))
    assert c.tickers() == {"ok": True}
    assert all("test@example.com" not in p.read_text() for p in tmp_path.iterdir())
    assert EdgarClient(tmp_path, offline=True).tickers() == {"ok": True}


def test_schema_rejects_over_budget_and_long_query():
    with pytest.raises(ValidationError):
        Search(researcher="news", reason="test", query="a"*400)
    with pytest.raises(ValidationError):
        ResearchPlan(brief=Brief(metrics=[], answer_type="text", may_be_unreported=False), periods=[],
                     edgar_fetches=[], searches=[Search(researcher="news",reason="test",query="test")],
                     search_budget=1, model="test")


def test_fiscal_label_comparison_does_not_hide_calendar_error():
    assert period_identity("Q2 FY2027") != period_identity("Q2 2027")
    assert period_identity("9M FY2027 implied") != period_identity("9M FY2027 actual")
    assert period_identity("Microsoft Q4 FY2026") == period_identity("Q4 FY2026")


@pytest.mark.parametrize("question,ticker,identities", [
    ("What was NVIDIA's revenue in fiscal 2024 and its YoY growth?", "NVDA", ["fy2024", "fy2023"]),
    ("Show Cisco's revenue in Q3 FY2025 through Q1 FY2026.", "CSCO", ["q3fy2025", "q4fy2025", "q1fy2026"]),
    ("What was Microsoft's Q2 FY2025 disclosed YoY growth?", "MSFT", ["q2fy2025"]),
    ("What was Apple's revenue for the September 2025 quarter?", "AAPL", ["q4fy2025"]),
    ("Give NVIDIA's first three quarters of FY2026 implied revenue vs the first three quarters of FY2025.", "NVDA", ["9mfy2026:implied", "9mfy2025:actual"]),
    ("For Micron fiscal 2025, give each quarter's gross margin and full-year revenue growth.", "MU", ["q1fy2025", "q2fy2025", "q3fy2025", "q4fy2025", "fy2025", "fy2024"]),
])
def test_question_period_rules_on_other_years(client, question, ticker, identities):
    r = resolve("", client=client, mentions=[ticker])
    catalog, calendars, _ = catalog_for(r, client, TODAY)
    periods = explicit_periods(question, r, calendars, catalog, TODAY)
    assert [period_identity(p.label) for p in periods] == identities


def test_comparative_and_output_periods_are_separate(client, monkeypatch):
    def fake(*args, **kwargs):
        return PlanDraft(brief=Brief(metrics=["revenue"], answer_type="number", may_be_unreported=False),
                         periods=[PeriodChoice(keys=["invented"])], edgar_fetches=[], searches=[]), {}
    monkeypatch.setattr("agents.planner.structured", fake)
    result = plan("NVIDIA revenue for fiscal 2024 and fiscal 2023", resolve("", client=client, mentions=["NVDA"]), TODAY, client=client)
    assert [p.label for p in result.periods] == ["FY2024", "FY2023"]
    assert {s.researcher for s in result.searches} == {"financials"}


def test_unprefixed_catalog_lookup_must_be_unique():
    p = Period(label="Q2 2026", start=date(2026, 4, 1), end=date(2026, 6, 30))
    assert lookup_period("Q2 2026", {"AMZN:Q2 2026": p}) == p
    with pytest.raises(ValueError, match="ambiguous"):
        lookup_period("Q2 2026", {"AMZN:Q2 2026": p, "GOOGL:Q2 2026": p})


def test_required_researchers_for_comparison_and_unknown_period(client):
    r = resolve("", client=client, mentions=["Amazon", "Microsoft"])
    b = Brief(metrics=["capex guide"], answer_type="text", may_be_unreported=False)
    assert required_researchers("What are these companies currently guiding for capex?", r, b) == {"company", "news", "industry"}
    assert required_researchers("What was Apple's revenue?", r, b.model_copy(update={"may_be_unreported": True})) >= {"financials", "news"}


def test_private_calendar_keeps_no_edgar_identity(client):
    r = resolve("", client=client, mentions=["Cargill"])
    catalog, calendars, _ = catalog_for(r, client, TODAY)
    p = explicit_periods("Cargill FY2025 10-K", r, calendars, catalog, TODAY)[0]
    assert not calendars and r.entities[0].cik is None
    assert p.start == date(2024, 6, 1) and p.end == date(2025, 5, 31)
    assert p.source_urls == ["https://www.cargill.com/sustainability/2025-impact-report"]


def test_ambiguous_name_remains_unresolved(client, monkeypatch):
    monkeypatch.setattr(client, "tickers", lambda: {
        "0": {"ticker": "ACM", "cik_str": 1, "title": "ACME HOLDINGS"},
        "1": {"ticker": "ACB", "cik_str": 2, "title": "ACME BANK"}})
    assert resolve("", client=client, mentions=["Acme"]).entities[0].status == "unresolved"


def test_search_share_class_is_canonicalized(client, monkeypatch):
    def fake(*args, **kwargs):
        return PlanDraft(brief=Brief(metrics=["repurchases"], answer_type="number", may_be_unreported=False),
                         periods=[PeriodChoice(keys=["GOOGL:Q2 2026"])], edgar_fetches=[],
                         searches=[SearchChoice(researcher="financials", reason="class breakdown", intent="repurchases", tickers=["GOOG"])]), {}
    monkeypatch.setattr("agents.planner.structured", fake)
    result = plan("Alphabet share repurchases Q2 2026", resolve("", client=client, mentions=["GOOGL"]), TODAY, client=client)
    assert "GOOGL" in result.searches[0].query


def test_benchmark_blocks_tavily_and_sec_network():
    with nebius_only_network():
        for url in ("https://api.tavily.com/search", "https://data.sec.gov/submissions/CIK0000320193.json"):
            with pytest.raises(AssertionError, match="forbids"):
                httpx.get(url)


def test_ended_but_unreported_period_has_no_actual_fetch(client, monkeypatch):
    def fake(*args, **kwargs):
        return PlanDraft(brief=Brief(metrics=["revenue"], answer_type="number", may_be_unreported=False),
                         periods=[], edgar_fetches=[FetchChoice(key="AAPL:Q4 FY2026", form="10-Q", item="revenue")], searches=[]), {}
    monkeypatch.setattr("agents.planner.structured", fake)
    result = plan("Apple revenue for the September 2026 quarter", resolve("", client=client, mentions=["AAPL"]), TODAY, client=client)
    assert not result.edgar_fetches and result.brief.may_be_unreported
    assert {s.researcher for s in result.searches} >= {"financials", "news"}


def test_expired_live_cache_refreshes_but_offline_snapshot_does_not(tmp_path, monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "test test@example.com")
    count = []
    def respond(request):
        count.append(request.url)
        return httpx.Response(200, json={"version": len(count)})
    c = EdgarClient(tmp_path, transport=httpx.MockTransport(respond), max_age_s=0)
    assert c.tickers() == {"version": 1}
    assert c.tickers() == {"version": 2}
    assert EdgarClient(tmp_path, offline=True).tickers() == {"version": 2}


def test_benchmark_also_blocks_sdk_http_transport():
    httpx2 = pytest.importorskip("httpx2")
    with nebius_only_network(), pytest.raises(AssertionError, match="forbids"):
        httpx2.get("https://api.tavily.com/search")
