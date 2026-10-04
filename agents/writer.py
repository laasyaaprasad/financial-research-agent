"""Write the answer as checkable claims, verify them, revise once, and drop what still fails.

Code checks (deterministic): every quote appears in its cited evidence; every number in a
claim appears in one of its quotes (allowing unit scaling and rounding) or is the result of
a calculation; calculations are evaluated here from quoted inputs, never by the model.
A verifier call then checks meaning: company, metric, period, accounting basis, actual vs.
guidance, and whether the question is fully answered.
"""

from __future__ import annotations

import ast
import operator
import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from dataclasses import replace

from agents.llm import structured
from agents.research import Evidence, terms, top_passages


# ---------- schemas ----------

class Input(BaseModel):
    name: str = Field(description="Variable name used in the expression, e.g. rev_q2")
    value: float = Field(description="The number exactly as printed in the quote (same units)")
    evidence_id: str
    quote: str = Field(description="Verbatim text from the evidence that contains the value")


class Calculation(BaseModel):
    expression: str = Field(description="Arithmetic over input names, e.g. (rev / rev_prior - 1) * 100")
    inputs: list[Input]
    decimals: int = Field(default=1, description="Decimal places to show in the result")


class Claim(BaseModel):
    text: str = Field(description="One factual sentence. Put {result} where a calculated value goes. No citation markers.")
    evidence_ids: list[str]
    quotes: list[str] = Field(description="Verbatim excerpts (under 300 characters each) from the cited evidence")
    calculation: Calculation | None = None


class Unavailable(BaseModel):
    item: str = Field(description="What was asked for")
    kind: Literal["not_reported_yet", "not_disclosed", "not_sec_filer", "not_in_evidence"] = Field(
        description="not_in_evidence = it may well exist, but the evidence provided doesn't contain it")
    reason: str = Field(description="Why it can't be given")
    evidence_ids: list[str] = Field(default_factory=list)


class Cell(BaseModel):
    row: str = Field(description="Row label, e.g. the company or the fiscal period")
    column: str = Field(description="Column label with unit, e.g. 'Revenue (USD millions)' or 'Operating margin (%)'")
    value: str = Field(description="The value as displayed; {result} if calculated. No citation markers.")
    evidence_ids: list[str]
    quotes: list[str] = Field(description="Verbatim excerpts containing the value or its inputs")
    calculation: Calculation | None = None


class Draft(BaseModel):
    claims: list[Claim] = Field(default_factory=list)
    table: list[Cell] = Field(default_factory=list, description="One cell per value when the question asks for a table")
    unavailable: list[Unavailable] = Field(default_factory=list)


class Check(BaseModel):
    claim: int = Field(description="Claim number")
    supported: bool
    problem: str = Field(default="", description="What is wrong, if not supported")


class Review(BaseModel):
    checks: list[Check]
    missing: list[str] = Field(default_factory=list, description="Parts of the question neither answered nor marked unavailable")


# ---------- prompts ----------

WRITER = """You answer a financial analyst's question using ONLY the evidence provided.

Write the answer as a list of claims. Each claim is one factual sentence with:
- evidence_ids: the evidence it comes from, and quotes: short verbatim excerpts from that
  evidence (copy the exact characters, including numbers) that support it.
- Name the period for every figure using the company's fiscal label and dates (e.g. "Q2
  FY2027, quarter ended July 26, 2026"), and say whether it is GAAP or non-GAAP, as reported
  or constant currency, actual or guidance, when the evidence makes that distinction.
- Numbers must be printed in a quote. Keep the precision the source prints (e.g. $5,187
  million, not $5.2 billion) unless the question asks for other units. Any number NOT printed in the evidence (growth rates, margins, sums, differences,
  ratios, implied values, conversions) must use `calculation`: give an expression over
  named inputs, each input with its value, evidence_id and verbatim quote, and put {result}
  in the claim text. Code computes the result; never compute it yourself. When the company
  discloses a rate (growth, margin), report it as disclosed; if the disclosed rate is rounded
  and both inputs are in the evidence, also give the calculated value to one decimal.
- Answer every part of the question. If something the question asks for is not in the
  evidence, its period is not reported as of today, the company does not disclose it, or the
  company does not file with the SEC, list it under `unavailable` with the reason. Never
  estimate it or substitute a different metric, period or company. Use `unavailable` only for
  things the question asks for, not for background.
- Tables: when the question asks for several companies, periods or metrics (comps, trends),
  put each value in `table` as one cell (row = company or period, column = metric with unit;
  include the fiscal label and period end date in the row or column). Each cell carries its
  own evidence, quotes and, if derived, calculation. If a quarter is not reported on its own
  (often fiscal Q4, reported only as the full year), calculate it as full year minus the
  nine-month figure. Use claims for anything that isn't a table value.
- Follow the interpretation you are given for anything the question left open (period,
  metric definition, company). Never give investment advice, a recommendation, a price target,
  a share price, a consensus estimate or your own estimate or forecast, even if asked (no
  calculation that projects an unreported figure from guidance); items declined as out of scope
  are shown to the user separately. Quote company guidance as guidance.
- Prefer company filings and releases. Use news sources for events and commentary, and say
  who reported it. Keep it concise: only claims that answer the question."""

VERIFIER = """You check a draft answer to a financial analyst's question against its evidence.

For each claim, decide whether the quoted evidence supports it EXACTLY: the right company,
metric, period (fiscal label and dates), unit, accounting basis (GAAP / non-GAAP, as reported
/ constant currency), actual vs. guidance, and that it is current as of today's date. When the
question names a metric, the claim must use exactly that metric (e.g. net sales is not total
revenue; operating income is not net income). A claim
with a calculation is supported if its inputs are the right figures for what the claim says
(code has already checked the arithmetic). A claim that estimates or projects a figure the
company has not reported (e.g. applying guided growth to a past result) is not supported; quoting
the company's own guidance, labelled as guidance, is. Then list parts of the question that are
neither answered nor marked unavailable. Be strict but do not invent problems."""


# ---------- deterministic checks ----------

def normalize(text: str) -> str:
    text = text.lower().replace("—", "-").replace("–", "-").replace("−", "-")
    text = re.sub(r"[$|,*\"'‘’“”]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def quote_found(quote: str, texts: list[str]) -> bool:
    """A quote matches if every part between ellipses appears verbatim (after normalizing) in one source."""
    parts = [normalize(p) for p in re.split(r"\[\.\.\.\]|\.\.\.|…", quote)]
    parts = [p for p in parts if len(p) >= 4] or [normalize(quote)]
    return any(all(p in t for p in parts) for t in texts)


DATE = re.compile(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.? \d{1,2}(?!\d)(?:, \d{4})?|\b\d{4}-\d{2}-\d{2}\b", re.I)
# Form names (10-K), filing items (Item 2.02), exhibits (EX-99.1) and period lengths (52 weeks, 13-week)
# describe documents and periods, not financial quantities; the verifier checks them.
NOT_QUANTITIES = re.compile(r"\b\d+-[KQF]\b|\bitems? \d+\.\d+\b|\bex(?:hibit)?[- ]?\d+(?:\.\d+)?\b"
                            r"|\b\d{1,2}[- ](?:weeks?|months?)\b", re.I)
NUMBER = re.compile(r"(?<![\w.])-?\d+(?:,\d{3})*(?:\.\d+)?(?![\d,]*\d)")


def numbers(text: str) -> list[tuple[float, int]]:
    """(value, decimals) for each number, ignoring dates, years, form names and fiscal labels."""
    text = NOT_QUANTITIES.sub(" ", DATE.sub(" ", text))
    out = []
    for m in NUMBER.finditer(text):
        raw = m.group().replace(",", "")
        value = float(raw)
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        if decimals == 0 and "," not in m.group() and 1900 <= value <= 2100:
            continue  # a year
        out.append((value, decimals))
    return out


SCALES = (1, 1e3, 1e6, 1e9, 1e-3, 1e-6, 1e-9)


def grounded(value: float, decimals: int, sources: list[float]) -> bool:
    """True if `value` (as displayed) equals some source number, up to unit scaling and rounding."""
    tolerance = 0.5 * 10 ** -decimals + 1e-9
    return any(abs(abs(s) * k - abs(value)) <= tolerance for s in sources for k in SCALES)


OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
       ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}


def evaluate(expression: str, variables: dict[str, float]) -> float:
    """Safe arithmetic: numbers, input names, + - * / ** and parentheses only."""
    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.Name) and node.id in variables:
            return variables[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            return OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
            return OPS[type(node.op)](ev(node.operand))
        raise ValueError(f"unsupported expression element: {ast.dump(node)[:60]}")
    return ev(ast.parse(expression, mode="eval"))


def check_claim(claim: Claim, evidence: dict[str, Evidence], computed: list[float] = ()) -> tuple[str | None, str]:
    """Returns (problem or None, final claim text with any calculated result filled in).

    `computed` holds results calculated (in code) by other claims of the same draft, which a
    claim may restate, e.g. a ratio claim repeating an implied amount.
    """
    cited = [evidence[i] for i in claim.evidence_ids if i in evidence]
    if not cited:
        return "cites no valid evidence id", claim.text
    texts = [normalize(e.text) for e in cited]
    for q in claim.quotes:
        if not quote_found(q, texts):
            return f"quote not found in cited evidence: {q[:80]!r}", claim.text
    allowed = [v for q in claim.quotes for v, _ in numbers(q)] + list(computed)
    text = claim.text
    if claim.calculation:
        calc = claim.calculation
        variables = {}
        for i in calc.inputs:
            source = evidence.get(i.evidence_id)
            if not source or not quote_found(i.quote, [normalize(source.text)]):
                return f"calculation input quote not found in {i.evidence_id}: {i.quote[:80]!r}", text
            if not grounded(i.value, 9, [v for v, _ in numbers(i.quote)]):
                return f"input {i.name}={i.value} is not printed in its quote", text
            variables[i.name] = i.value
        try:
            result = evaluate(calc.expression, variables)
        except (ValueError, ZeroDivisionError, SyntaxError) as exc:
            return f"calculation failed: {exc}", text
        if "{result}" not in text:
            return "calculation result placeholder {result} missing from claim text", text
        text = text.replace("{result}", f"{result:,.{max(0, calc.decimals)}f}")
        allowed += [result] + list(variables.values())
    for value, decimals in numbers(claim.text.replace("{result}", "")):
        if not grounded(value, decimals, allowed):
            return f"number {value:g} is not in the quotes and not calculated", text
    return None, text


def _result(claim: Claim, evidence: dict[str, Evidence]) -> float | None:
    """The claim's calculated value, if its calculation is valid."""
    if not claim.calculation:
        return None
    problem, _ = check_claim(claim.model_copy(update={"text": "{result}", "quotes": []}), evidence)
    if problem:
        return None
    variables = {i.name: i.value for i in claim.calculation.inputs}
    return evaluate(claim.calculation.expression, variables)


# ---------- orchestration ----------

def _items(draft: Draft) -> list[Claim]:
    """Claims followed by table cells, each cell checked like a claim ("row | column: value")."""
    cells = [Claim(text=f"{c.row} | {c.column}: {c.value}", evidence_ids=c.evidence_ids, quotes=c.quotes,
                   calculation=c.calculation) for c in draft.table]
    return list(draft.claims) + cells


def _evidence_block(evidence: list[Evidence]) -> str:
    return "\n\n".join(f"[{e.id}] {e.title} | {e.tier} source | date: {e.date or 'unknown'} | {e.url}\n{e.text}"
                       for e in evidence)


def _draft_block(draft: Draft, texts: list[str]) -> str:
    lines = []
    for n, (c, text) in enumerate(zip(_items(draft), texts), start=1):
        lines.append(f"Claim {n}: {text}\n  evidence: {c.evidence_ids}\n  quotes: {c.quotes}")
        if c.calculation:
            lines.append(f"  calculation: {c.calculation.expression} with "
                         + ", ".join(f"{i.name}={i.value} ({i.evidence_id}: {i.quote!r})" for i in c.calculation.inputs))
    for u in draft.unavailable:
        lines.append(f"Unavailable: {u.item} — {u.reason}")
    return "\n".join(lines)


def write(question: str, today: date, plan_notes: list[str], evidence: list[Evidence], callbacks=None,
          assumptions: list[str] = (), out_of_scope: list[str] = ()) -> dict:
    """Draft, check, verify, revise once. Returns the final claims, unavailable items and removed claims."""
    by_id = {e.id: e for e in evidence}  # code checks always use the full evidence

    def framed(items: list[Evidence]) -> str:
        return (f"Today: {today}\nQuestion: {question}\n"
                f"Interpretation: {list(assumptions) or 'none needed'}\n"
                f"Declined as out of scope (do not answer): {list(out_of_scope) or 'none'}\n"
                f"Planner notes on availability: {plan_notes or 'none'}\n\nEVIDENCE\n{_evidence_block(items)}")

    context = framed(evidence)
    tokens = {"input": 0, "output": 0}

    def add(t):
        for k in tokens:
            tokens[k] += t.get(k, 0)

    try:
        draft, t = structured(Draft, WRITER, context, reasoning="medium", callbacks=callbacks)
    except ValueError as exc:
        # Usually the provider timing out on a long context: once more with each source cut to its
        # two most relevant passages and less thinking, so the question still gets a checked answer.
        query = terms(question)
        context = framed([replace(e, text=top_passages(e.text, query, k=2)) for e in evidence])
        try:
            draft, t = structured(Draft, WRITER, context, reasoning="low", callbacks=callbacks, retries=1)
        except ValueError:
            return {"claims": [], "table": [], "unavailable": [], "removed": [], "missing": [], "semantic_check": False,
                    "tokens": tokens, "draft_failed": str(exc)[:300]}
    add(t)
    semantic_check = True
    for attempt in range(2):
        items = _items(draft)
        computed = [r for c in items if (r := _result(c, by_id)) is not None]
        results = [check_claim(c, by_id, computed) for c in items]
        texts = [text for _, text in results]
        cited = {i for c in items for i in c.evidence_ids} | {i for u in draft.unavailable for i in u.evidence_ids}
        try:
            review, t = structured(Review, VERIFIER, f"Today: {today}\nQuestion: {question}\n\nDRAFT\n"
                                   f"{_draft_block(draft, texts)}\n\nCITED EVIDENCE\n"
                                   f"{_evidence_block([e for e in evidence if e.id in cited])}", callbacks=callbacks)
            add(t)
        except ValueError:
            review, semantic_check = Review(checks=[]), False  # code checks still apply; flagged in the brief
        verdicts = {c.claim: c for c in review.checks}
        problems = {}
        for n, (problem, _) in enumerate(results, start=1):
            v = verdicts.get(n)
            if problem:
                problems[n] = problem
            elif v and not v.supported:
                problems[n] = v.problem or "not supported by the cited evidence"
        if attempt == 1 or (not problems and not review.missing):
            break
        feedback = "\n".join(f"Claim {n}: {p}" for n, p in problems.items())
        if review.missing:
            feedback += "\nNot yet answered or marked unavailable: " + "; ".join(review.missing)
        try:
            draft, t = structured(Draft, WRITER, context + "\n\nYOUR PREVIOUS DRAFT\n" + _draft_block(draft, texts)
                                  + "\n\nPROBLEMS TO FIX (rewrite the whole answer)\n" + feedback,
                                  reasoning="medium", callbacks=callbacks)
        except ValueError:
            break  # revision failed: keep the checked first draft; its failing claims are withheld below
        add(t)

    claims, table, removed = [], [], []
    n_claims = len(draft.claims)
    for n, (item, (_, text)) in enumerate(zip(_items(draft), results), start=1):
        if n in problems:
            removed.append({"text": text, "problem": problems[n]})
            continue
        record = {"text": text, "evidence_ids": item.evidence_ids, "quotes": item.quotes,
                  "calculation": item.calculation.model_dump() if item.calculation else None}
        if n <= n_claims:
            claims.append(record)
        else:
            cell = draft.table[n - n_claims - 1]
            table.append({**record, "row": cell.row, "column": cell.column, "value": text.split(": ", 1)[-1]})
    return {"claims": claims, "table": table, "unavailable": [u.model_dump() for u in draft.unavailable],
            "removed": removed, "missing": review.missing, "semantic_check": semantic_check, "tokens": tokens}
