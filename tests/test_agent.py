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

    def __init__(self, reports, fy_label_offset=0, fiscal_year_end=None):
        self.reports = reports  # (form, report_date, filed)
        self.offset = fy_label_offset
        self.fiscal_year_end = fiscal_year_end

    def submissions(self, cik):
        rows = sorted(self.reports, key=lambda r: r[2], reverse=True)
        return {"name": "SYNTHETIC CO", "tickers": [], "fiscalYearEnd": self.fiscal_year_end, "filings": {"recent": {
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


def test_calendar_projects_53_week_year_from_sec_fiscal_year_end():
    # Saturday nearest Sept 30: FY2025 ended Sept 27, 2025; FY2026 runs 53 weeks to Oct 3, 2026.
    reports = [("10-K", "2025-09-27", "2025-11-15"), ("10-Q", "2025-12-27", "2026-02-01"),
               ("10-Q", "2026-03-28", "2026-05-01"), ("10-Q", "2026-06-27", "2026-08-01")]
    periods = {p.label: p for p in calendar(FakeEdgar(reports, fiscal_year_end="1003"), "1", date(2026, 10, 3))}
    assert periods["FY2026"].start == date(2025, 9, 28) and periods["FY2026"].end == date(2026, 10, 3)
    assert periods["Q4 FY2026"].status == "not yet reported (period still in progress)"
    # Without SEC's fiscal year end the projection keeps 52 weeks.
    periods = {p.label: p for p in calendar(FakeEdgar(reports), "1", date(2026, 10, 3))}
    assert periods["FY2026"].end == date(2026, 9, 26)


# ---------- company resolution ----------

class FakeRegistry(FakeEdgar):
    """A filer missing from the ticker list, found only by EDGAR company search."""

    def tickers(self):
        return {}

    def company_search(self, name):
        return ["81"]


def _mentions(monkeypatch, **fields):
    import agents.company as company
    monkeypatch.setattr(company, "structured", lambda *a, **k: (company.Mentions(**fields), {"input": 1, "output": 1}))
    return company


def test_resolve_finds_filers_without_a_ticker(monkeypatch):
    company = _mentions(monkeypatch, companies=[{"name": "Employee Owned Grocer"}])
    reports = [("10-K", "2025-12-27", "2026-02-25"), ("10-Q", "2026-06-27", "2026-08-03")]
    companies, clarification, _ = company.resolve("q2 sales", date(2026, 10, 3), FakeRegistry(reports))
    assert clarification is None and companies[0].resolved and companies[0].cik == "81"
    assert companies[0].ticker == "CIK81"


def test_resolve_rejects_filers_that_stopped_reporting(monkeypatch):
    company = _mentions(monkeypatch, companies=[{"name": "Taken Private Co"}])
    reports = [("10-K", "2024-08-31", "2024-10-15"), ("10-Q", "2025-05-31", "2025-06-26")]
    companies, _, _ = company.resolve("fq3 comps", date(2026, 10, 3), FakeRegistry(reports))
    assert not companies[0].resolved and "no longer files" in companies[0].reason


def test_clarification_short_circuits_research(monkeypatch):
    import agents.pipeline as pipeline
    monkeypatch.setattr(pipeline, "resolve", lambda *a, **k: ([], "Which company do you mean?", {"input": 1, "output": 1}))
    monkeypatch.setattr(pipeline, "plan", lambda *a, **k: pytest.fail("planned research for an unclear question"))
    out = pipeline.run("what was revenue last quarter?", today=date(2026, 10, 3), live_web=False)
    assert out["clarification"] == "Which company do you mean?" and out["tavily_credits"] == 0
    assert "**Clarification needed:** Which company do you mean?" in out["answer"]


def test_render_states_interpretation_and_scope():
    from agents.pipeline import render
    result = {"claims": [{"text": "Revenue was $10 million.", "evidence_ids": ["E1"]}], "unavailable": [], "removed": [],
              "assumptions": ["No period given: used Q2 FY2026, the latest reported quarter."],
              "out_of_scope": ["Buy recommendation: investment advice is out of scope."]}
    evidence = {"E1": {"title": "10-Q", "url": "https://www.sec.gov/x", "date": "2026-08-01", "tier": "primary"}}
    text = render("x rev, buy?", date(2026, 10, 3), result, evidence)
    assert "**Interpreted as:** No period given" in text
    assert "**Outside this tool's scope**\n- Buy recommendation" in text


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
    for name in ("golden.jsonl", "test_heldout.jsonl", "test_hard.jsonl", "edge_dev.jsonl", "test_edge.jsonl",
                 "web_dev.jsonl", "test_web.jsonl"):
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


# ---------- tables ----------

def test_table_rendering_pivots_cells_with_citations():
    from agents.pipeline import _table
    cells = [{"row": "Q1 FY2026", "column": "Revenue (USD m)", "value": "100", "evidence_ids": ["E1"]},
             {"row": "Q1 FY2026", "column": "Margin (%)", "value": "20.0", "evidence_ids": ["E1"]},
             {"row": "Q2 FY2026", "column": "Revenue (USD m)", "value": "110", "evidence_ids": ["E2"]}]
    lines = _table(cells, lambda cell: "".join(f"[{i[1:]}]" for i in cell["evidence_ids"]))
    assert lines[0] == "| | Revenue (USD m) | Margin (%) |"
    assert lines[2] == "| Q1 FY2026 | 100 [1] | 20.0 [1] |"
    assert lines[3] == "| Q2 FY2026 | 110 [2] | — |"


def test_xbrl_evidence_always_includes_core_lines():
    from agents.fiscal import Filing
    from agents.research import _xbrl_evidence, terms
    filing = Filing(form="10-Q", filed=date(2026, 5, 1), accession="0001-26-000001", url="u", report_date=date(2026, 3, 31))
    long_label = {"label": "Revenue from Contract with Customer, Excluding Assessed Tax",
                  "units": {"USD": [{"accn": filing.accession, "start": "2026-01-01", "end": "2026-03-31", "val": 1000}]}}
    noise = {f"OtherIncome{i}": {"label": f"Other Income Item {i}",
                                 "units": {"USD": [{"accn": filing.accession, "end": "2026-03-31", "val": i}]}} for i in range(40)}

    class Facts:
        def companyfacts(self, cik):
            return {"facts": {"us-gaap": {"RevenueFromContractWithCustomerExcludingAssessedTax": long_label, **noise}}}

    company = Company(requested="X", name="X Corp", ticker="XX", cik="1")
    text = _xbrl_evidence(company, [filing], terms("quarterly revenue and other income"), Facts())[0].text
    assert "RevenueFromContractWithCustomerExcludingAssessedTax" in text


def test_table_text_cells_match_on_fiscal_label():
    from evals.scorers import _same_label
    assert _same_label("Q3 FY2026, quarter ended August 31, 2026", "Q3 FY2026 (quarter ended Aug 31, 2026)")
    assert _same_label("third quarter of fiscal 2026", "Q3 FY2026")
    assert not _same_label("Q2 FY2026", "Q3 FY2026")
    assert not _same_label("Q3 FY2025", "Q3 FY2026")


def test_citation_check_asks_again_when_claims_are_left_undecided(monkeypatch):
    import evals.scorers as scorers
    url = "https://www.sec.gov/a.htm"
    replies = [[{"claim": "Revenue was $5 million.", "numeric": True, "cited_url": url, "reason": "", "supported": None}],
               [{"claim": "Revenue was $5 million.", "numeric": True, "cited_url": url, "reason": "", "supported": True}]]
    monkeypatch.setattr(scorers, "_judge", lambda schema, prompt, **_: schema(claims=replies.pop(0)))
    result = scorers.score_citations("Revenue was $5 million [1].", {scorers.norm_url(url): {"url": url, "content": "x"}})
    assert result["supported"] == 1 and result["undecided"] == 0 and not replies


# ---------- Tavily settings ----------

class FakeWeb:
    """Records Tavily calls; returns one result on the company's own site and one news result."""

    def __init__(self):
        self.calls = []

    async def call(self, operation, **params):
        self.calls.append((operation, params))
        if operation == "extract":
            return {"results": [{"url": u, "raw_content": "passage"} for u in params["urls"]]}
        return {"results": [{"url": "https://investors.acme.com/q2", "title": "Acme Q2", "content": "Acme results", "score": 0.9},
                            {"url": "https://news.example.com/acme", "title": "Acme news", "content": "Acme said", "score": 0.5}]}


def _web_evidence(config, monkeypatch, domains=("acme.com",)):
    import asyncio
    import agents.research as research
    monkeypatch.setattr(research, "official_domains", lambda name: domains)
    web = FakeWeb()
    plan = Plan(metrics=["guidance"], searches=[SearchRequest(purpose="p", query="Acme Q2 guidance call")])
    company = Company(requested="acme", name="Acme Corp", ticker="ACME", cik="1")
    items = asyncio.run(research.web_evidence("q", plan, [company], date(2026, 10, 3), web, config))
    return web.calls, items


def test_default_search_settings_are_unchanged(monkeypatch):
    from agents.research import EXCLUDED_DOMAINS, SearchConfig
    calls, items = _web_evidence(SearchConfig(), monkeypatch)
    assert calls[0] == ("search", {"query": "Acme Q2 guidance call", "search_depth": "basic", "max_results": 5,
                                   "end_date": "2026-10-03", "exclude_domains": EXCLUDED_DOMAINS, "topic": "general"})
    assert calls[1][0] == "extract" and items[0].text == "passage"


def test_advanced_search_uses_chunks_and_company_sites(monkeypatch):
    from agents.research import SearchConfig
    calls, items = _web_evidence(SearchConfig(depth="advanced", company_sites=True, finance_topic=True), monkeypatch)
    # Only one result came from the company's own site, so the open web is searched too; no extract call.
    assert [op for op, _ in calls] == ["search", "search"]
    own_site, open_web = calls[0][1], calls[1][1]
    assert own_site["include_domains"] == ["acme.com"] and "include_domains" not in open_web
    assert own_site["chunks_per_source"] == 3 and own_site["topic"] == "finance"
    assert items[0].tier == "primary" and items[1].tier == "secondary"


# ---------- matching web results to the company ----------

def _result(text):
    return {"title": text, "content": ""}


def test_company_match_uses_short_names_not_the_first_legal_word():
    from agents.research import _is_company_source, _mentions_company
    # The press uses the bracketed short name; the first legal word alone is an ordinary word.
    c = Company(requested="ejemtex", name="Industria Ejemplo de Tejidos, S.A. (Ejemtex)", resolved=False)
    assert _mentions_company(_result("Ejemtex first-half sales rise 7%"), [c])
    assert not _mentions_company(_result("La industria de telecomunicaciones crece"), [c])
    assert _is_company_source("https://www.ejemtex.com/en/press/h1-results", [c])
    assert not _is_company_source("https://www.telecom-news.es/industria", [c])


def test_company_match_ignores_common_first_words_and_other_companies_sites():
    from agents.research import _is_company_source, _mentions_company
    c = Company(requested="first acme", name="FIRST ACME BANK CORP /XX/", ticker="FAB", cik="1", aliases=["First Acme"])
    assert _mentions_company(_result("First Acme lifts net interest income outlook"), [c])
    assert not _mentions_company(_result("Bank earnings in the first quarter"), [c])
    assert _mentions_company(_result("Shares of FAB rose after the call"), [c])          # ticker, case-sensitive
    assert not _mentions_company(_result("a fab new product"), [c])
    assert _is_company_source("https://investor.firstacme.com/news", [c])
    assert not _is_company_source("https://investors.othercorp.com/news", [c])          # someone else's IR site
    assert not _is_company_source("https://www.bankrate.com/acme", [c])


def test_company_match_respects_word_boundaries_and_short_tickers():
    from agents.research import _is_company_source, _mentions_company
    c = Company(requested="f", name="ACME MOTOR CO", ticker="F", cik="2", aliases=["Acme"])
    assert _mentions_company(_result("Acme's quarterly EBIT beat"), [c])                 # apostrophe normalized
    assert not _mentions_company(_result("Acmeplex opens a new site; F grade for traffic"), [c])
    assert not _is_company_source("https://www.acmeplexnews.com/a", [c])               # short names match labels exactly
    assert _is_company_source("https://acme-global.com/ir", [c])


def test_company_match_handles_possessives_and_registry_names():
    from agents.research import _mentions_company
    c = Company(requested="acmes", name="ACMES COMPANIES INC", ticker="AQX", cik="3")  # registry form of "Acme's"
    assert _mentions_company(_result("Acme's second-quarter comparable sales fell"), [c])
    assert _mentions_company(_result("ACMES Companies reports results"), [c])


# ---------- failures never produce an empty answer ----------

def test_structured_thinks_less_after_a_timeout(monkeypatch):
    import agents.llm as llm
    from agents.writer import Review
    efforts = []

    class APITimeoutError(Exception):
        pass

    class FakeChat:
        def __init__(self, **kwargs):
            efforts.append(kwargs["reasoning_effort"])

        def with_structured_output(self, *a, **k):
            return self

        def invoke(self, *a, **k):
            if len(efforts) == 1:
                raise APITimeoutError("Request timed out.")
            return {"parsed": Review(checks=[]), "raw": type("Raw", (), {"usage_metadata": {}})()}

    monkeypatch.setattr(llm, "ChatNebius", FakeChat)
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    llm.structured(Review, "s", "u", reasoning="medium")
    assert efforts == ["medium", "low"]


def _writer_with(monkeypatch, draft_replies):
    import agents.writer as writer
    calls = []

    def fake(schema, system, user, *, reasoning="low", callbacks=None, retries=2):
        calls.append((schema.__name__, reasoning, len(user)))
        if schema is writer.Draft:
            reply = draft_replies.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return reply, {"input": 1, "output": 1}
        return writer.Review(checks=[]), {"input": 1, "output": 1}

    monkeypatch.setattr(writer, "structured", fake)
    long_text = "\n".join(f"Paragraph {i} about other matters." + " filler" * 200 for i in range(30))
    evidence = [Evidence(id="E1", url="u", title="t", tier="primary", date=None,
                         text=long_text + "\nRevenue was $5 million in the quarter.\n" + long_text)]
    result = writer.write("What was revenue in the quarter?", date(2026, 10, 3), [], evidence)
    return result, calls


def test_writer_retries_with_shorter_evidence_after_a_failure(monkeypatch):
    from agents.writer import Claim, Draft
    good = Draft(claims=[Claim(text="Revenue was $5 million.", evidence_ids=["E1"], quotes=["Revenue was $5 million"])])
    result, calls = _writer_with(monkeypatch, [ValueError("Draft: timed out"), good])
    (_, first_effort, first_len), (_, second_effort, second_len) = calls[0], calls[1]
    assert (first_effort, second_effort) == ("medium", "low") and second_len < first_len / 3
    assert [c["text"] for c in result["claims"]] == ["Revenue was $5 million."]  # still checked against full evidence


def test_writer_reports_failure_instead_of_raising(monkeypatch):
    result, _ = _writer_with(monkeypatch, [ValueError("timed out"), ValueError("timed out again")])
    assert result["claims"] == [] and "timed out" in result["draft_failed"]


def test_planner_fallback_uses_latest_reported_period():
    from agents.planner import fallback
    reports = [("10-K", "2025-05-31", "2025-06-20"), ("10-Q", "2025-08-31", "2025-09-10"), ("8-K", "2025-12-18", "2025-12-18")]
    company = Company(requested="x", name="X Corp", ticker="XX", cik="1",
                      periods=calendar(FakeEdgar(reports), "1", date(2026, 1, 10)))
    private = Company(requested="y", name="Y Private", resolved=False)
    plan = fallback("x and y revenue", [company, private])
    assert [p.label for p in plan.answer_periods] == ["Q2 FY2026"]  # earnings release only, after the filed Q1
    assert [d.document for d in plan.documents] == ["earnings_release"]
    assert len(plan.searches) == 1 and plan.searches[0].query.startswith("Y Private")
    assert plan.assumptions and plan.availability_notes


def test_pipeline_keeps_first_answer_when_gap_rewrite_fails(monkeypatch):
    import asyncio
    import agents.pipeline as pipeline
    company = Company(requested="x", name="X Corp", ticker="XX", cik="1")
    ev = Evidence(id="", url="https://www.sec.gov/a", title="10-Q", tier="primary", date="2026-08-01", text="Revenue $5 million")
    extra = Evidence(id="", url="https://news.example.com/b", title="News", tier="secondary", date="2026-09-01", text="x")
    first = {"claims": [{"text": "Revenue was $5 million.", "evidence_ids": ["E1"], "quotes": ["Revenue $5 million"]}],
             "table": [], "removed": [], "missing": [], "semantic_check": True, "tokens": {"input": 1, "output": 1},
             "unavailable": [{"item": "guidance", "kind": "not_in_evidence", "reason": "not found", "evidence_ids": []}]}
    replies = [first, {"claims": [], "table": [], "unavailable": [], "removed": [], "missing": [], "semantic_check": False,
                       "tokens": {"input": 1, "output": 1}, "draft_failed": "timed out"}]

    async def no_web(*a, **k):
        return []

    async def gap(*a, **k):
        return [extra]

    monkeypatch.setattr(pipeline, "resolve", lambda *a, **k: ([company], None, {"input": 1, "output": 1}))
    monkeypatch.setattr(pipeline, "plan", lambda *a, **k: (Plan(metrics=["revenue"]), {"input": 1, "output": 1}))
    monkeypatch.setattr(pipeline, "sec_evidence", lambda *a, **k: [ev])
    monkeypatch.setattr(pipeline, "web_evidence", no_web)
    monkeypatch.setattr(pipeline, "gap_evidence", gap)
    monkeypatch.setattr(pipeline, "write", lambda *a, **k: replies.pop(0))
    out = pipeline.run("x revenue and guidance", today=date(2026, 10, 3), live_web=False)
    assert "Revenue was $5 million." in out["answer"] and out["error"] is None


def test_pipeline_explains_a_failed_company_step(monkeypatch):
    import agents.pipeline as pipeline

    def broken(*a, **k):
        raise ValueError("Mentions: model did not return valid structured output")

    monkeypatch.setattr(pipeline, "resolve", broken)
    out = pipeline.run("x revenue", today=date(2026, 10, 3), live_web=False)
    assert "**No answer.**" in out["answer"] and out["error"] and out["tavily_credits"] == 0


def test_company_match_keeps_short_official_names():
    from agents.research import _is_company_source, _mentions_company
    c = Company(requested="qz", name="QZ INC", ticker="QZQ", cik="4")       # two-letter official name
    d = Company(requested="4d", name="4D CO", ticker="FDX4", cik="5")        # name with a digit
    assert _mentions_company(_result("QZ Inc. raises its outlook"), [c]) and _is_company_source("https://www.qz.com/ir", [c])
    assert _mentions_company(_result("4D reports record revenue"), [d])
    e = Company(requested="ab", name="Alpha Beta Gamma Corp", ticker="ABG", cik="6", aliases=["AB"])  # 2-letter alias ignored
    assert not _mentions_company(_result("AB testing results"), [e])


# ---------- eval harness ----------

def test_baseline_search_cache_replays_without_calling_tavily(monkeypatch, tmp_path):
    from langchain_tavily import TavilySearch
    from agents.baseline import CachedTavilySearch
    monkeypatch.setenv("TAVILY_API_KEY", "dummy")
    calls = []

    def fake_run(self, query, run_manager=None, **kwargs):
        calls.append(query)
        return {"error": "Error 432: usage limit"} if query == "refused" else {"query": query, "results": []}

    monkeypatch.setattr(TavilySearch, "_run", fake_run)
    first, second = CachedTavilySearch(cache_dir=tmp_path), CachedTavilySearch(cache_dir=tmp_path)
    assert first._run("acme revenue", search_depth="advanced") == second._run("acme revenue", search_depth="advanced")
    assert calls == ["acme revenue"] and first.live_depths == ["advanced"] and second.live_depths == []
    first._run("refused"), second._run("refused")  # failed calls: not cached, not counted
    assert calls.count("refused") == 2 and first.live_depths == ["advanced"]


def test_usage_limit_is_detected_for_both_agents():
    from evals.run import usage_limit_hit
    baseline = {"tool_results": [{"raw": "{'error': ValueError(\"Error 432: This request exceeds your plan's set usage limit.\")}"}]}
    agent = {"tool_calls": [{"name": "tavily_search", "credits": 0, "error": "ValueError: Error 432: exceeds the usage limit"}]}
    ok = {"tool_results": [{"results": [{"content": "Revenue was $432 million"}]}], "tool_calls": [{"credits": 1}]}
    assert usage_limit_hit(baseline) and usage_limit_hit(agent) and not usage_limit_hit(ok)


def test_correctness_verdict_comes_from_required_points():
    from evals.scorers import Correctness, Point, verdict
    pt = lambda met, optional=False: Point(point="x", optional=optional, met=met, note="")
    # an unmet optional item doesn't block "correct", whatever the judge said overall
    assert verdict(Correctness(points=[pt(True), pt(False, optional=True)], verdict="partial", rationale="")) == ("correct", 1.0)
    assert verdict(Correctness(points=[pt(True), pt(False)], verdict="correct", rationale="")) == ("partial", 0.5)
    assert verdict(Correctness(points=[pt(True), pt(False)], verdict="incorrect", rationale="")) == ("incorrect", 0.5)
    assert verdict(Correctness(points=[pt(False)], verdict="partial", rationale="")) == ("incorrect", 0.0)


# ---------- grounding repairs ----------

def test_quotes_match_across_zero_width_table_spacers():
    from agents.writer import normalize, quote_found
    source = "Adjusted EBITDA\n$\n77,842\n​\n$\n73,841\n​\nAdjusted EBITDA margin"
    assert quote_found("Adjusted EBITDA $ 77,842 $ 73,841", [normalize(source)])


def test_spelled_out_numbers_count_as_printed():
    ev = {"E1": Evidence(id="E1", url="u", title="t", tier="primary", date=None,
                         text="a contractual commitment of $11.6 billion over seven years")}
    calc = Calculation(expression="total / years", decimals=2, inputs=[
        Input(name="total", value=11.6, evidence_id="E1", quote="commitment of $11.6 billion"),
        Input(name="years", value=7, evidence_id="E1", quote="over seven years")])
    claim = Claim(text="That is {result} billion a year.", evidence_ids=["E1"], quotes=[], calculation=calc)
    assert check_claim(claim, ev) == (None, "That is 1.66 billion a year.")


def test_unquoted_number_gets_the_passage_that_prints_it():
    from agents.writer import attach_quotes
    ev = {"E1": Evidence(id="E1", url="u", title="t", tier="primary", date=None,
                         text="Revenue of $321.1 million, up 9%\nGAAP Operating Margin of 10.2% and Non-GAAP Operating Margin 29.4%")}
    claim = Claim(text="Non-GAAP operating margin was 29.4%.", evidence_ids=["E1"], quotes=["GAAP Operating Margin of 10.2%"])
    assert check_claim(claim, ev)[0]  # the figure isn't in the writer's quote
    attach_quotes(claim, ev)
    assert len(claim.quotes) == 2 and check_claim(claim, ev)[0] is None
    other = Claim(text="Non-GAAP operating margin was 31.5%.", evidence_ids=["E1"], quotes=["Operating Margin of 10.2%"])
    attach_quotes(other, ev)  # a figure the source doesn't print gets no quote, and still fails
    assert len(other.quotes) == 1 and check_claim(other, ev)[0]


def test_words_starting_like_months_are_not_dates():
    assert numbers("Non-GAAP Operating Margin 29.4% and Marketing 5") == [(29.4, 1), (5.0, 0)]
    assert numbers("quarter ended Sept. 3 and Dec 31, 2026") == []
