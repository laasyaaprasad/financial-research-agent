"""Offline tests for the deterministic parts of the agent (no network, no model calls)."""

import json
import re
from datetime import date
from pathlib import Path

import pytest

from agents.company import Company
from agents.fiscal import calendar
from agents.planner import DocumentRequest, PeriodRef, Plan, SearchRequest, validate
from agents.research import Evidence, top_passages
from agents.writer import Calculation, Claim, Input, check_claim, evaluate, grounded, numbers

ROOT = Path(__file__).resolve().parent.parent


# ---------- numbers and calculations ----------

def test_numbers_ignore_dates_years_forms_and_fiscal_labels():
    text = ("Q2 FY2027 (quarter ended July 26, 2026, reported in the 10-Q and EX-99.1, Item 2.02): "
            "revenue $46,743 million, up 12.5%, September 2026 quarter")
    assert numbers(text) == [(46743.0, 0), (12.5, 1)]
    # A year followed by a comma, and period lengths, are not financial quantities.
    assert numbers("income of $5,907 million for fiscal 2026, the 52 weeks ended August 30, 2026, a 16-week quarter") \
        == [(5907.0, 0)]


@pytest.mark.parametrize("value,decimals,sources,ok", [
    (215.9, 1, [215938], True),       # millions restated as billions, rounded
    (215.94, 2, [215938], True),
    (215.8, 1, [215938], False),
    (0.81, 2, [0.81], True),
    (4619, 0, [-4619], True),          # parentheses/sign differences
    (12, 0, [11.78], True),            # 11.78 shown as 12
    (13, 0, [12.4], False),
])
def test_grounded_allows_scaling_and_rounding_only(value, decimals, sources, ok):
    assert grounded(value, decimals, sources) is ok


def test_evaluate_is_restricted_arithmetic():
    assert evaluate("(a / b - 1) * 100", {"a": 110, "b": 100}) == pytest.approx(10)
    with pytest.raises(ValueError):
        evaluate("__import__('os').system('ls')", {})
    with pytest.raises(ValueError):
        evaluate("a + c", {"a": 1})


EVIDENCE = {"E1": Evidence(id="E1", url="https://www.sec.gov/x", title="10-Q", tier="primary", date="2026-08-26",
                           text="Total revenue | $ | 46,743 | $ | 30,040\nNet income | 26,422 | 16,599")}


def test_claim_with_printed_numbers_passes():
    claim = Claim(text="Revenue was $46.7 billion in Q2 FY2027.", evidence_ids=["E1"], quotes=["Total revenue | $ | 46,743"])
    assert check_claim(claim, EVIDENCE)[0] is None


def test_claim_with_unprinted_number_fails():
    claim = Claim(text="Revenue grew 56% in Q2 FY2027.", evidence_ids=["E1"], quotes=["Total revenue | $ | 46,743"])
    problem, _ = check_claim(claim, EVIDENCE)
    assert "not in the quotes" in problem


def test_claim_with_invented_quote_fails():
    claim = Claim(text="Revenue was $46.7 billion.", evidence_ids=["E1"], quotes=["Revenue of $46.7 billion"])
    assert "quote not found" in check_claim(claim, EVIDENCE)[0]


def test_quote_matching_tolerates_ellipses_and_quotation_marks_only():
    from agents.writer import normalize, quote_found
    text = [normalize("Management said “underlying operating income growth was at the top end of guidance” for the quarter.")]
    assert quote_found('"underlying operating income growth was at the top end of guidance"', text)
    assert quote_found("Management said ... at the top end of guidance", text)
    assert not quote_found("operating income growth exceeded guidance", text)


def test_calculation_is_computed_in_code():
    calc = Calculation(expression="(rev / prior - 1) * 100", decimals=1, inputs=[
        Input(name="rev", value=46743, evidence_id="E1", quote="46,743"),
        Input(name="prior", value=30040, evidence_id="E1", quote="30,040")])
    claim = Claim(text="Revenue grew {result}% year over year.", evidence_ids=["E1"], quotes=["46,743 | $ | 30,040"], calculation=calc)
    problem, text = check_claim(claim, EVIDENCE)
    assert problem is None and text == "Revenue grew 55.6% year over year."


def test_calculation_input_must_be_printed():
    calc = Calculation(expression="rev * 2", inputs=[Input(name="rev", value=50000, evidence_id="E1", quote="46,743")])
    claim = Claim(text="Twice revenue is {result}.", evidence_ids=["E1"], quotes=["46,743"], calculation=calc)
    assert "not printed in its quote" in check_claim(claim, EVIDENCE)[0]


# ---------- fiscal calendar ----------

class FakeEdgar:
    """Submissions and XBRL facts for a synthetic filer."""

    def __init__(self, reports, fy_label_offset=0):
        self.reports = reports  # (form, report_date, filed)
        self.offset = fy_label_offset

    def submissions(self, cik):
        rows = sorted(self.reports, key=lambda r: r[2], reverse=True)
        return {"filings": {"recent": {
            "form": [r[0] for r in rows], "reportDate": [r[1] for r in rows], "filingDate": [r[2] for r in rows],
            "accessionNumber": [f"0000-{i}" for i in range(len(rows))], "primaryDocument": ["d.htm"] * len(rows),
            "items": ["2.02" if r[0] == "8-K" else "" for r in rows]}}}

    def companyfacts(self, cik):
        sub = self.submissions(cik)["filings"]["recent"]
        facts = [{"accn": a, "fp": "FY", "end": d, "fy": int(d[:4]) + self.offset}
                 for a, f, d in zip(sub["accessionNumber"], sub["form"], sub["reportDate"]) if f == "10-K"]
        return {"facts": {"us-gaap": {"Revenues": {"units": {"USD": facts}}}}}


def test_calendar_irregular_quarters_and_start_year_naming():
    # Retailer-style: fiscal year ends late Jan/early Feb, named for the year it starts in.
    reports = [("10-K", "2025-02-01", "2025-03-15"), ("10-Q", "2025-05-03", "2025-06-01"),
               ("10-Q", "2025-08-02", "2025-09-01"), ("10-Q", "2025-11-01", "2025-12-01"),
               ("10-K", "2026-01-31", "2026-03-15"), ("10-Q", "2026-05-02", "2026-06-01"),
               ("8-K", "2026-08-19", "2026-08-19")]
    periods = {p.label: p for p in calendar(FakeEdgar(reports, fy_label_offset=-1), "1", date(2026, 9, 1))}
    assert periods["FY2025"].end == date(2026, 1, 31) and periods["FY2025"].status == "filed"
    assert periods["Q1 FY2026"].start == date(2026, 2, 1) and periods["Q1 FY2026"].end == date(2026, 5, 2)
    q2 = periods["Q2 FY2026"]
    assert q2.end == date(2026, 8, 1) and q2.projected and q2.status.startswith("earnings release only")
    assert periods["Q3 FY2026"].status.startswith("not yet reported")


def test_calendar_month_end_quarters():
    reports = [("10-K", "2025-05-31", "2025-06-20"), ("10-Q", "2025-08-31", "2025-09-10"),
               ("10-Q", "2025-11-30", "2025-12-10"), ("10-Q", "2026-02-28", "2026-03-10"),
               ("10-K", "2026-05-31", "2026-06-20")]
    periods = {p.label: p for p in calendar(FakeEdgar(reports), "1", date(2026, 10, 1))}
    assert periods["Q4 FY2026"].start == date(2026, 3, 1)
    assert periods["Q1 FY2027"].end == date(2026, 8, 31) and periods["Q1 FY2027"].status.startswith("not yet reported (period ended")


# ---------- planner validation and passage ranking ----------

def test_planner_validation_drops_unknown_choices():
    reports = [("10-K", "2025-05-31", "2025-06-20"), ("10-Q", "2025-08-31", "2025-09-10")]
    company = Company(requested="X", name="X Corp", ticker="XX", cik="1",
                      periods=calendar(FakeEdgar(reports), "1", date(2025, 10, 1)))
    raw = Plan(metrics=["revenue"],
               answer_periods=[PeriodRef(ticker="XX", label="Q1 FY2026"), PeriodRef(ticker="XX", label="Q9 FY2030")],
               documents=[DocumentRequest(ticker="XX", period="Q1 FY2026", document="periodic_report"),
                          DocumentRequest(ticker="XX", period="Q2 FY2026", document="periodic_report")],
               searches=[SearchRequest(purpose="p", query=f"q{i}") for i in range(6)])
    plan = validate(raw, [company])
    assert [p.label for p in plan.answer_periods] == ["Q1 FY2026"]
    assert [d.period for d in plan.documents] == ["Q1 FY2026"]
    assert len(plan.searches) == 3
    assert any("Q9 FY2030" in n for n in plan.availability_notes)


def test_top_passages_keeps_relevant_text():
    filler = "\n".join(f"Boilerplate risk factor paragraph number {i} about general matters." for i in range(400))
    text = filler + "\nRemaining performance obligations were $664 billion.\n" + filler
    assert "664" in top_passages(text, ["remaining", "performance", "obligations"], k=3)


# ---------- no evaluation-set knowledge in production code ----------

def test_production_code_has_no_evaluation_companies():
    companies = set()
    for name in ("golden.jsonl", "test_heldout.jsonl"):
        path = ROOT / "evals" / name
        if path.exists():
            for line in path.read_text().splitlines():
                field = str(json.loads(line).get("company", ""))
                companies |= set(re.findall(r"\(([A-Z]{2,5})\b", field))            # tickers
                companies |= set(re.findall(r"\b[A-Z][a-zA-Z&]{3,}\b", field.split("(")[0]))  # name words
    companies -= {"January", "February", "March", "April", "June", "July", "August", "September", "October",
                  "November", "December", "Fiscal", "Private", "None"}
    generic = {"Inc.", "Corporation", "Company", "Corp", "Holdings", "Platforms", "Technologies", "Systems", "Group",
               "International", "Incorporated", "formerly", "private", "ticker", "filer", "only", "with", "Wholesale",
               "Class", "Semiconductor", "Communications", "Financial", "Services", "Brands", "Energy", "Health",
               "Industries", "Motors", "Airlines", "Foods", "Global", "Stores", "Software", "Networks", "Labs",
               "Resources", "Partners", "Pharmaceuticals", "Entertainment", "Media", "Devices", "Micro", "Capital",
               "Materials", "Products", "Solutions", "Cloud", "Data", "Digital", "Group", "Brand"}
    names = {c for c in companies if c not in generic}
    for path in (ROOT / "agents").glob("*.py"):
        if path.name == "baseline.py":
            continue
        source = path.read_text()
        found = [n for n in names if re.search(rf"\b{re.escape(n)}\b", source)]
        assert not found, f"{path.name} mentions evaluation companies: {found}"
