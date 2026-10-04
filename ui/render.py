"""Chat rendering of a pipeline result: a citation after every statement, linked sources at the end.

Citation markers are "[n]", numbered by first use as in the CLI brief. Each marker links to its
source, opened at the quoted passage where the browser can find it, and shows the quote the
statement relies on when hovered. The evidence for the whole answer (every source with the
quotes and calculations behind each statement) is rendered separately for a side panel.
"""

from __future__ import annotations

import re
from datetime import date
from urllib.parse import quote, urlparse

from agents.pipeline import DISCLAIMER, body, citer

EVIDENCE = "Evidence panel"  # side panel name; the chat links every occurrence of it in an answer to the panel
TIERS = {"primary": "Primary source (SEC filing or the company)", "secondary": "Secondary source (news or third party)"}
TITLE_CHARS = 300


def _ids(item: dict) -> list[str]:
    """Sources behind a statement: its cited evidence, then any calculation inputs."""
    calc = item.get("calculation") or {}
    return list(dict.fromkeys(item["evidence_ids"] + [x["evidence_id"] for x in calc.get("inputs", [])]))


def _escape(text: str) -> str:
    """Show source text literally: no markdown emphasis, links, headings or math from filing punctuation."""
    return re.sub(r"([\\`*_\[\]<>#|~$])", r"\\\1", " ".join(text.split()))


def _number(value: float) -> str:
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,}"


def locate(url: str, quoted: str) -> str | None:
    """Link that opens a document scrolled to a prose quote (a URL text fragment); None for table rows,
    tagged XBRL values and very short quotes, which a browser can't find as written."""
    part = max(re.split(r"\[\.\.\.\]|\.\.\.|…", quoted), key=len).strip()
    words = part.split()
    if "|" in part or len(words) < 4 or urlparse(url).path.endswith("/"):
        return None
    enc = lambda s: quote(s, safe="").replace("-", "%2D")  # noqa: E731 - '-' and ',' are fragment syntax
    target = enc(part) if len(words) <= 10 else f"{enc(' '.join(words[:5]))},{enc(' '.join(words[-5:]))}"
    return f"{url}{':~:text=' if '#' in url else '#:~:text='}{target}"


def used(item: dict, source_id: str, source: dict) -> list[str]:
    """The quotes a statement takes from one source: its quotes found in that source, then calculation inputs."""
    calc = item.get("calculation") or {}
    return list(dict.fromkeys([q for q in item.get("quotes", []) if q in source["quotes"]]
                              + [x["quote"] for x in calc.get("inputs", []) if x["evidence_id"] == source_id]))


def _marker(sources: dict):
    """mark(n, source_id, statement): "[n]" linked to the source at the statement's first locatable quote,
    with the quotes it relies on as the hover text."""
    def mark(n: int, i: str, item: dict) -> str:
        s = sources[i]
        quotes = used(item, i, s)
        link = next((u for q in quotes if (u := locate(s["url"], q))), s["url"])
        hover = " · ".join(f"“{' '.join(q.split())[:TITLE_CHARS]}”" for q in quotes)
        hover = f"{hover} — {s['title']}" if hover else s["title"]
        return f'[[{n}]](<{link}> "{_title(hover)}")'
    return mark


def _title(text: str) -> str:
    """Hover text as a markdown link title; '|' is escaped too, or a quoted table row would split a table cell."""
    return re.sub(r'([\\"|])', r"\\\1", text)


def _statements(output: dict) -> list[dict]:
    """Every cited statement as shown in the answer."""
    out = [{**c, "label": c["text"]} for c in output["claims"]]
    out += [{**c, "label": f"{c['row']} | {c['column']}: {c['value']}"} for c in output.get("table", [])]
    out += [{**u, "label": f"Not available: {u['item']} ({u['reason']})", "quotes": []} for u in output["unavailable"]]
    return out


def evidence(question: str, today: date, order: list[str], sources: dict, statements: list[dict]) -> str:
    """Side panel for one answer: each source in citation order, with every statement citing it and the
    quotes and calculations behind that statement."""
    lines = [f"### {_escape(question)}", f"_As of {today} · {len(order)} source(s)_"]
    for n, i in enumerate(order, start=1):
        s = sources[i]
        lines += ["", f"#### [{n}] {_escape(s['title'] or s['url'])}",
                  f"{urlparse(s['url']).netloc} · {s['date'] or 'undated'} · {TIERS.get(s['tier'], s['tier'])} · "
                  f"[open ↗](<{s['url']}>)"]
        for item in statements:
            if i not in _ids(item):
                continue
            lines += ["", f"**{_escape(item['label'])}**"]
            calc = item.get("calculation")
            inputs = {x["quote"]: x for x in (calc or {}).get("inputs", []) if x["evidence_id"] == i}
            for q in used(item, i, s):
                link = locate(s["url"], q)
                note = f" — input `{inputs[q]['name']}` = {_number(inputs[q]['value'])}" if q in inputs else ""
                lines += ["", f"> {_escape(q)}{note}" + (f" [find in source ↗](<{link}>)" if link else "")]
            if calc:
                lines += ["", f"Calculated in code: `{calc['expression']}`"]
    return "\n".join(lines + ["", "---"])


def render(output: dict, today: date, question: str, rewritten: bool = False) -> tuple[str, str | None]:
    """(Markdown answer, Evidence panel markdown or None) for a pipeline result.

    `question` is what was researched; it's shown above the answer when `rewritten` from a follow-up.
    """
    header = [f"**Researched as:** {question}", ""] if rewritten else []
    if output.get("clarification"):
        return "\n".join(header + [output["clarification"]]), None
    sources = output["sources"]
    # Calculation inputs are cited too, so every figure behind a statement has a marker.
    result = {**output, "claims": [{**c, "evidence_ids": _ids(c)} for c in output["claims"]],
              "table": [{**c, "evidence_ids": _ids(c)} for c in output.get("table", [])]}
    cite, order = citer(sources, mark=_marker(sources), sep=" ", ascending=True)
    lines = header + body(result, cite)
    if output["removed"]:
        lines += ["", f"_{len(output['removed'])} draft statement(s) were withheld because they could not be verified "
                      "against the sources (listed under the **Write and verify** step)._"]
    if order:
        lines += ["", "**Sources**", ""]
        for n, i in enumerate(order, start=1):
            s = sources[i]
            lines.append(f"{n}. [{_escape(s['title'] or s['url'])}](<{s['url']}>) · {urlparse(s['url']).netloc}"
                         f" · {s['date'] or 'undated'} · {s['tier']}")
        lines += ["", f"Each citation opens its source; hover it for the quote. Open the {EVIDENCE} for the quotes and "
                      "calculations behind every statement."]
    lines += ["", f"_As of {today}. {DISCLAIMER}_"]
    panel = evidence(question, today, order, sources, _statements(result)) if order else None
    return "\n".join(lines), panel
