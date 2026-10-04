"""Offline tests for the chat rendering and the conversation summary (no network, no model calls, no Chainlit)."""

import re
from datetime import date

from agents.followup import standalone, turn
from ui.render import EVIDENCE, locate, render

RELEASE = "https://www.sec.gov/Archives/edgar/data/1/0001/q.htm"
SOURCES = {
    "E1": {"url": RELEASE, "title": "X Corp 10-Q for Q2 FY2026", "date": "2026-08-01", "tier": "primary",
           "quotes": ["Total revenue | $ | 110", "Revenue grew because of higher volume in every region"]},
    "E2": {"url": "https://www.sec.gov/Archives/edgar/data/1/0002/", "title": "X Corp XBRL data tagged in 10-Q",
           "date": "2026-05-01", "tier": "primary", "quotes": ["Revenues (Revenues): 100 USD"]},
    "E3": {"url": "https://news.example.com/a", "title": "Report [exclusive]", "date": None, "tier": "secondary",
           "quotes": []},
}
CALC = {"expression": "(rev / prior - 1) * 100", "decimals": 1, "inputs": [
    {"name": "rev", "value": 110.0, "evidence_id": "E1", "quote": "Total revenue | $ | 110"},
    {"name": "prior", "value": 100.0, "evidence_id": "E2", "quote": "Revenues (Revenues): 100 USD"}]}
OUTPUT = {
    "claims": [
        {"text": "Revenue was $110 million in Q2 FY2026.", "evidence_ids": ["E1"],
         "quotes": ["Total revenue | $ | 110"], "calculation": None},
        {"text": "Revenue grew 10.0% year over year.", "evidence_ids": ["E1"], "quotes": [], "calculation": CALC},
        {"text": "Management attributed growth to volume.", "evidence_ids": ["E1"],
         "quotes": ["Revenue grew because of higher volume in every region"], "calculation": None},
    ],
    "table": [], "unavailable": [{"item": "Q3 revenue", "reason": "not reported yet", "evidence_ids": ["E3"]}],
    "removed": [{"text": "x", "problem": "y"}], "assumptions": ["Latest quarter: Q2 FY2026."], "out_of_scope": [],
    "semantic_check": True, "sources": SOURCES, "companies": [{"name": "X Corp", "ticker": "XX", "resolved": True}],
}
TODAY = date(2026, 10, 4)


def test_every_statement_cites_its_sources_with_links_and_quotes():
    content, _ = render(OUTPUT, TODAY, "How did X Corp do?")
    lines = content.splitlines()
    first = next(line for line in lines if line.startswith("- Revenue was"))
    assert first == f'- Revenue was $110 million in Q2 FY2026. [[1]](<{RELEASE}> "“Total revenue \\| $ \\| 110” — X Corp 10-Q for Q2 FY2026")'
    # A calculation cites the sources of its inputs too, even when the claim lists only one.
    growth = next(line for line in lines if line.startswith("- Revenue grew"))
    assert "[[1]](" in growth and '[[2]](<https://www.sec.gov/Archives/edgar/data/1/0002/> "“Revenues (Revenues): 100 USD”' in growth
    # A prose quote opens the document at the passage.
    volume = next(line for line in lines if line.startswith("- Management"))
    assert f"[[1]](<{RELEASE}#:~:text=Revenue%20grew%20because%20of%20higher%20volume%20in%20every%20region>" in volume
    assert '- Q3 revenue: not reported yet [[3]](<https://news.example.com/a> "Report [exclusive]")' in lines


def test_sources_are_listed_with_links_at_the_end():
    content, _ = render(OUTPUT, TODAY, "How did X Corp do?")
    sources = content.split("**Sources**")[1]
    assert f"1. [X Corp 10-Q for Q2 FY2026](<{RELEASE}>) · www.sec.gov · 2026-08-01 · primary" in sources
    assert "3. [Report \\[exclusive\\]](<https://news.example.com/a>) · news.example.com · undated · secondary" in sources
    assert f"Open the {EVIDENCE} for" in sources
    assert "_1 draft statement(s) were withheld" in content and content.endswith(
        "_As of 2026-10-04. Draft for analyst review. Every figure is quoted from the cited source or computed in code "
        "from quoted inputs; claims that failed verification were removed._")


def test_evidence_panel_shows_each_statement_with_its_quotes_and_calculation():
    _, panel = render(OUTPUT, TODAY, "How did X Corp do?")
    release, tagged, news = panel.split("#### ")[1:]
    assert release.startswith("[1] X Corp 10-Q for Q2 FY2026\nwww.sec.gov · 2026-08-01 · Primary source")
    assert "> Total revenue \\| \\$ \\| 110" in release   # source punctuation shown literally
    assert "**Revenue grew 10.0% year over year.**" in release and "— input `rev` = 110" in release
    assert "Calculated in code: `(rev / prior - 1) * 100`" in release
    assert "[find in source ↗](<" + RELEASE + "#:~:text=" in release
    assert "— input `prior` = 100" in tagged and "Management attributed" not in tagged
    assert "**Not available: Q3 revenue (not reported yet)**" in news
    assert panel.startswith("### How did X Corp do?\n_As of 2026-10-04 · 3 source(s)_")


def test_locate_links_prose_quotes_only():
    url = "https://www.sec.gov/a/q.htm"
    assert locate(url, "Revenue grew because of higher volume") == \
        "https://www.sec.gov/a/q.htm#:~:text=Revenue%20grew%20because%20of%20higher%20volume"
    assert locate(url, "Total revenue | $ | 110") is None             # table row
    assert locate("https://www.sec.gov/a/", "Revenues of the company were 100 USD") is None  # folder (tagged data)
    assert locate(url, "short quote") is None
    long = locate(url + "#part", "one two three four five six seven eight nine ten eleven-twelve")
    assert long == url + "#part:~:text=one%20two%20three%20four%20five,seven%20eight%20nine%20ten%20eleven%2Dtwelve"


def test_table_cells_keep_their_columns():
    cell = {"row": "Q2 FY2026", "column": "Revenue (USD m)", "value": "110", "evidence_ids": ["E1"],
            "quotes": ["Total revenue | $ | 110"], "calculation": None}
    content, _ = render({**OUTPUT, "claims": [], "unavailable": [], "table": [cell]}, TODAY, "q")
    row = next(line for line in content.splitlines() if line.startswith("| Q2 FY2026"))
    assert len(re.findall(r"(?<!\\)\|", row)) == 3   # the quoted table row's pipes are escaped


def test_markers_are_numbered_by_first_use_and_listed_ascending():
    claims = [{"text": "A.", "evidence_ids": ["E2"], "quotes": [], "calculation": None},
              {"text": "B.", "evidence_ids": ["E1", "E2"], "quotes": [], "calculation": None}]
    content, _ = render({**OUTPUT, "claims": claims, "unavailable": []}, TODAY, "q")
    second = next(line for line in content.splitlines() if line.startswith("- B."))
    assert second.index("[[1]]") < second.index("[[2]]") and "[[2]](<https://www.sec.gov/Archives/edgar/data/1/0001/q.htm>" in second


def test_hover_text_cannot_break_the_link():
    out = {**OUTPUT, "claims": [{"text": "CEO said growth was strong.", "evidence_ids": ["E1"], "calculation": None,
                                 "quotes": ['He said "growth was strong" \\ here']}],
           "unavailable": [], "sources": {"E1": {**SOURCES["E1"], "quotes": ['He said "growth was strong" \\ here']}}}
    content, _ = render(out, TODAY, "q")
    assert '"“He said \\"growth was strong\\" \\\\ here” — X Corp 10-Q for Q2 FY2026")' in content


def test_clarification_and_rewritten_question():
    out = {**OUTPUT, "clarification": "Which company do you mean?", "sources": {}}
    content, panel = render(out, TODAY, "What was revenue for the airline?", rewritten=True)
    assert content == "**Researched as:** What was revenue for the airline?\n\nWhich company do you mean?"
    assert panel is None


def test_turn_summarizes_what_follow_ups_may_refer_to():
    summary = turn("and margins?", "What were X Corp's margins in Q2 FY2026?", OUTPUT)
    assert summary.splitlines()[:3] == ["Analyst: and margins?", "Researched as: What were X Corp's margins in Q2 FY2026?",
                                        "About: X Corp (XX)"]
    assert "Interpretation: Latest quarter: Q2 FY2026." in summary and "Not available: Q3 revenue" in summary
    asked = turn("revenue last quarter", "revenue last quarter", {**OUTPUT, "clarification": "Which company?"})
    assert asked == "Analyst: revenue last quarter\nAssistant asked: Which company?"


def test_first_message_is_researched_as_typed_without_a_model_call():
    assert standalone("What was X Corp's revenue?", [], TODAY) == ("What was X Corp's revenue?", {})
