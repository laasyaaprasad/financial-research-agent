"""Regression cases from review, plus scope/ownership invariants.

The frozen validation questions are run separately with live inference. They are
not fed into this test suite or used to generate production date rules.
"""

from datetime import date

import pytest

from agents.company import resolve
from agents.edgar import EdgarClient
from agents.periods import explicit_periods
from agents.planner import PeriodChoice, PlanDraft, catalog_for, materialize, plan
from agents.schemas import Brief, Period
from evals.planner import load_rows, period_atoms, period_identity

TODAY = date(2026, 10, 1)


@pytest.fixture
def client():
    return EdgarClient('tests/fixtures/edgar', offline=True)


def scope(client, question, tickers):
    resolution = resolve('', client=client, mentions=tickers)
    catalog, calendars, _ = catalog_for(resolution, client, TODAY)
    return explicit_periods(question, resolution, calendars, catalog, TODAY)


@pytest.mark.parametrize('connector', ['through', 'to', '–', '-'])
def test_range_includes_middle_quarter(client, connector):
    periods = scope(client, f"Show Cisco revenue from Q3 FY2025 {connector} Q1 FY2026.", ['CSCO'])
    assert [p.label for p in periods] == ['Q3 FY2025', 'Q4 FY2025', 'Q1 FY2026']


@pytest.mark.parametrize('wording', ['FY2026 Q1 and Q2', 'Q1 and Q2 FY2026', 'Q1 FY2026 and Q2'])
def test_coordinated_quarters_share_only_explicit_year(client, wording):
    periods = scope(client, f"What was Microsoft revenue in {wording}?", ['MSFT'])
    assert [(p.start.isoformat(), p.end.isoformat()) for p in periods] == [
        ('2025-07-01', '2025-09-30'), ('2025-10-01', '2025-12-31')]


@pytest.mark.parametrize('wording', ['calendar Q1 2026', 'Q1 calendar 2026', 'calendar 2026 Q1'])
def test_explicit_calendar_dates_are_not_fiscal(client, wording):
    periods = scope(client, f"What was NVIDIA revenue for {wording}?", ['NVDA'])
    assert len(periods) == 1
    p = periods[0]
    assert (p.start, p.end, p.tickers) == (date(2026, 1, 1), date(2026, 3, 31), ['NVDA'])
    assert period_identity(p.label) == 'q12026'


@pytest.mark.parametrize('wording', ['first half of fiscal 2026', 'H1 FY2026'])
def test_half_year_is_six_months(client, wording):
    p, = scope(client, f"Give Microsoft revenue in the {wording}.", ['MSFT'])
    assert (p.start, p.end, p.label) == (date(2025, 7, 1), date(2025, 12, 31), '6M FY2026')


@pytest.mark.parametrize('wording', [
    'Compare Microsoft and Amazon: Amazon Q2 2026 versus Microsoft Q4 FY2026.',
    'Compare Q2 2026 for Amazon with Q4 FY2026 for Microsoft.',
])
def test_local_company_mentions_own_periods(client, wording):
    periods = scope(client, wording, ['MSFT', 'AMZN'])
    assert [(p.label, p.tickers) for p in periods] == [('Q2 2026', ['AMZN']), ('Q4 FY2026', ['MSFT'])]
    assert all(p.start == date(2026, 4, 1) and p.end == date(2026, 6, 30) for p in periods)


@pytest.mark.parametrize('wording', [
    'Microsoft revenue in the second quarter of fiscal 2026',
    'Microsoft revenue for the last six months of fiscal 2026',
    'Microsoft revenue for the first nine months of fiscal 2026',
    'Microsoft revenue in the last two quarters of fiscal 2026',
])
def test_partial_parse_defers_to_model_instead_of_annual(client, wording):
    assert scope(client, wording, ['MSFT']) is None


def test_fallback_remains_one_call_with_validated_catalog(client, monkeypatch):
    calls = []
    def fake(*args, **kwargs):
        calls.append(args)
        return PlanDraft(brief=Brief(metrics=['revenue'], answer_type='number', may_be_unreported=False),
                         periods=[PeriodChoice(keys=['MSFT:Q2 FY2026'])], edgar_fetches=[], searches=[]), {}
    monkeypatch.setattr('agents.planner.structured', fake)
    result = plan('Microsoft revenue in the second quarter of fiscal 2026',
                  resolve('', client=client, mentions=['MSFT']), TODAY, client=client)
    assert len(calls) == 1 and [p.label for p in result.periods] == ['Q2 FY2026']


def test_calendar_model_transform_checks_owner_and_part():
    catalog = {'x': Period(label='FY2025', start=date(2024, 7, 1), end=date(2025, 6, 30), tickers=['MSFT'])}
    p = materialize(PeriodChoice(transform='calendar_quarter', year=2025, part=1, tickers=['MSFT']), catalog, TODAY)
    assert (p.start, p.end) == (date(2025, 1, 1), date(2025, 3, 31))
    with pytest.raises(ValueError, match='unknown company'):
        materialize(PeriodChoice(transform='calendar_half', year=2025, part=1, tickers=['invented']), catalog, TODAY)
    with pytest.raises(ValueError, match='Invalid'):
        materialize(PeriodChoice(transform='calendar_quarter', year=2025, part=5), catalog, TODAY)


def test_calendar_range_and_discrete_comparison_differ(client):
    series = scope(client, 'NVIDIA revenue calendar Q1 2025 to Q3 calendar 2025', ['NVDA'])
    discrete = scope(client, 'NVIDIA revenue calendar Q1 2025 versus Q3 calendar 2025', ['NVDA'])
    assert [p.start for p in series] == [date(2025, 1, 1), date(2025, 4, 1), date(2025, 7, 1)]
    assert [p.start for p in discrete] == [date(2025, 1, 1), date(2025, 7, 1)]


def test_calendar_clauses_keep_local_owners(client):
    periods = scope(client, 'Compare Microsoft calendar Q1 2025 with Amazon calendar Q2 2025.', ['MSFT','AMZN'])
    assert [(p.tickers, p.start, p.end) for p in periods] == [
        (['MSFT'],date(2025,1,1),date(2025,3,31)), (['AMZN'],date(2025,4,1),date(2025,6,30))]


def test_multiple_half_year_clauses_defer(client):
    assert scope(client, 'Microsoft first half of calendar 2025 vs Amazon first half of fiscal 2026', ['MSFT','AMZN']) is None


def test_scoring_detects_ownership_even_when_dates_match():
    a = dict(label='Q2 2026', start='2026-04-01', end='2026-06-30', tickers=['AMZN'])
    b = dict(label='Q4 FY2026', start='2026-04-01', end='2026-06-30', tickers=['MSFT'])
    swapped = [dict(a, tickers=['MSFT']), dict(b, tickers=['AMZN'])]
    assert period_atoms([a, b]) != period_atoms(swapped)
    combined = [dict(a, tickers=['AMZN','GOOGL'])]
    assert period_atoms(combined) == period_atoms([a, dict(a, tickers=['GOOGL'])])
    assert period_atoms(combined) != period_atoms(combined + [a])


def test_regression_questions_have_complete_ownership_and_original_count():
    rows = load_rows('regression')
    assert len(rows) == 30
    assert all('tickers' in p for row in rows for p in row['expected_periods'])
    comparison = next(row for row in rows if row['id'] == 'G29')
    assert [p['tickers'] for p in comparison['expected_periods']] == [['AMZN','GOOGL'],['MSFT']]


def test_frozen_validation_hash_is_enforced():
    assert len(load_rows('validation')) == 18
