"""Scorers: answer correctness, citation support and source quality.

The judge is a different model family (NVIDIA Nemotron) from the agents under test (DeepSeek),
so no agent grades its own output. On the user-graded sample it agreed with the user on 8 of 9.
(The first choice, Qwen3.5-397B, also 8/9, was withdrawn from Nebius on 2026-10-03.)
"""

from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Literal
from urllib.parse import urlparse

from dotenv import load_dotenv
from langchain_nebius import ChatNebius
from pydantic import BaseModel, Field, model_validator

load_dotenv()

JUDGE_MODEL = "nvidia/Nemotron-3-Ultra-550b-a55b"
URL_RE = re.compile(r"https?://[^\s\)\]>\"'`,]+")
CONTENT_CHARS = 200_000   # per URL kept in the index; judges see only the passages relevant to the answer
SOURCE_CHARS = 6000       # per cited source shown to the citation judge


# ---------- judge output schemas ----------

class Point(BaseModel):
    point: str = Field(description="One grading requirement from the rule, phrased as what a good answer does; "
                                   "a fail condition becomes what the answer must avoid, e.g. 'Does not use Q3'")
    optional: bool = Field(default=False, description="True if the rule marks this item optional")
    met: bool = Field(description="True if the answer satisfies the point (for a fail condition: avoids that failure)")
    note: str = Field(description="Short reason, quoting the agent's value where relevant")


class Correctness(BaseModel):
    points: list[Point]
    verdict: Literal["correct", "partial", "incorrect"] = Field(
        description="Your overall verdict; code recomputes it from the required points")
    rationale: str

    @model_validator(mode="after")
    def has_points(self):
        if not self.points:
            raise ValueError("Correctness requires rubric points")
        return self


def verdict(result: Correctness) -> tuple[str, float]:
    """(verdict, score) from the required points: optional items never block "correct". When some but not all
    required points are met, the judge's "incorrect" (the core answer is wrong) stands; otherwise "partial"."""
    required = [p for p in result.points if not p.optional] or result.points
    met = sum(p.met for p in required)
    if met == len(required):
        return "correct", 1.0
    if met == 0 or result.verdict == "incorrect":
        return "incorrect", met / len(required)
    return "partial", met / len(required)


class Claim(BaseModel):
    claim: str = Field(description="One factual claim from the answer, in a few words")
    numeric: bool = Field(description="True if the claim states a number, date or percentage")
    cited_url: str | None = Field(description="URL the answer cites for this claim, or null")
    reason: str = Field(description="The evidence; for a calculation, the cited inputs, formula and checked result")
    supported: bool | None = Field(description="Whether the retrieved text for cited_url supports the claim; null if uncited or not retrieved")


class Citations(BaseModel):
    claims: list[Claim]


class CellValue(BaseModel):
    index: int
    found: bool = Field(description="True only if the answer gives this exact entity, period and metric")
    value: float | str | None = Field(description="The answer's value converted to the requested unit (text cells: the text)")
    note: str = ""


class CellExtraction(BaseModel):
    cells: list[CellValue]


def _judge(schema, prompt: str, retries: int = 4, model: str = JUDGE_MODEL):
    llm = ChatNebius(model=model, temperature=0, timeout=240).with_structured_output(schema, method="function_calling")
    error = None
    for attempt in range(retries):
        if attempt:
            time.sleep(10 * attempt)  # transient provider errors (5xx) clear after a short wait
        try:
            result = llm.invoke(prompt)
            if result is not None:
                return result
            error = "no structured output"
            # The judge sometimes answers in prose instead of calling the function; ask explicitly.
            prompt += "\n\nReturn the grade only by calling the provided function, not as plain text."
        except Exception as exc:  # malformed judge output: ask again, saying what was wrong
            error = exc
            prompt += f"\n\nYour previous reply could not be used ({str(exc)[:300]}). Call the function again with valid fields."
    raise RuntimeError(f"judge failed after {retries} attempts: {error}")


# ---------- sources ----------

def norm_url(url: str) -> str:
    p = urlparse(url.strip().rstrip(".,;"))
    return (p.netloc.lower().removeprefix("www.") + p.path.rstrip("/")).lower()


QUOTED = re.compile(r"^Quoted: .*?\n---\n", re.S)  # our agent's records list its quotes first; judges get source text only


def retrieved_index(tool_results: list[dict]) -> dict[str, dict]:
    """Normalized URL -> what the agent retrieved from it (content merged if a URL appears twice)."""
    idx: dict[str, dict] = {}
    for payload in tool_results:
        for r in (payload or {}).get("results", []) or []:
            if not r.get("url"):
                continue
            key = norm_url(r["url"])
            entry = idx.setdefault(key, {"url": r["url"], "title": r.get("title", ""),
                                         "published_date": r.get("published_date"), "content": ""})
            text = QUOTED.sub("", r.get("content") or "")
            entry["content"] = (entry["content"] + "\n" + text).strip()[:CONTENT_CHARS]
    return idx


def excerpts(retrieved: dict[str, dict], answer: str, chars: int, limit: int | None = None,
             cited_only: bool = False) -> list[dict]:
    """The sources a judge sees: those the answer cites first, each cut to the passages most relevant to the answer
    (the same ranking for every agent), so a long page doesn't push the supporting text out of view."""
    from agents.research import terms, top_passages

    cited = [k for k in dict.fromkeys(norm_url(u) for u in URL_RE.findall(answer)) if k in retrieved]
    keys = cited if cited_only else cited + [k for k in retrieved if k not in cited]
    query = terms(answer)
    out = []
    for k in keys[:limit]:
        r = retrieved[k]
        text = r.get("content", "")
        if len(text) > chars:
            text = top_passages(text, query, k=max(1, chars // 1500))[:chars]
        out.append({**r, "content": text})
    return out


def primary_hosts(rows: list[dict]) -> set[str]:
    """SEC plus every host used as a primary source in the reference answers."""
    hosts = {"sec.gov"}
    for row in rows:
        for ev in row.get("evidence") or []:
            if ev.get("source_type") == "primary":
                hosts.add(urlparse(ev["url"]).netloc.lower().removeprefix("www."))
    return hosts


def is_primary(url: str, hosts: set[str]) -> bool:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return host in hosts or host.endswith(".sec.gov") or host.split(".")[0] in {"investor", "investors", "ir"}


# ---------- scorers ----------

TYPE_RULES = {
    "abstain": "- This is an abstain question: the core requirement is met only if the agent clearly says the figure "
               "is not available/disclosed and presents no number as an actual reported result.",
    "clarify": "- This is a clarify question: the core requirement is met only if the agent asks a clarifying question "
               "(naming the plausible options where relevant) and presents no figures as the answer.",
}


def score_correctness(row: dict, answer: str, retrieved: dict[str, dict], judge: str = JUDGE_MODEL) -> dict:
    if not answer.strip():
        return {"score": 0.0, "verdict": "incorrect", "points": [], "rationale": "No answer produced."}
    if row["time_sensitivity"] == "dynamic":
        reference = (
            "This question is TIME-SENSITIVE. Grade reference-free against the grading rubric, using the agent's "
            f"retrieved sources for recency and support. The snapshot answer (as of {row.get('as_of')}) is context "
            "only; do not require an exact match.\n\n"
            f"Snapshot answer (context): {row.get('answer')}\n\n"
            "Agent's retrieved sources (cited ones first; passages most relevant to the answer):\n"
            + json.dumps(excerpts(retrieved, answer, chars=3000, limit=15), ensure_ascii=False))
    else:
        reference = (f"Verified reference answer: {row.get('answer')}\n"
                     f"Reference facts: {json.dumps([e.get('facts') for e in row.get('evidence') or []], ensure_ascii=False)}\n"
                     f"Reference calculations: {json.dumps(row.get('calculations'), ensure_ascii=False)}")
    prompt = f"""You are grading a financial research agent's answer for an analyst. Be strict and literal.

Question: {row['question']}
Answer type: {row['answer_type']}
Grading rule: {row['grading']}
Failure mode this question tests: {row['failure_mode']}

{reference}

Agent's answer:
<<<
{answer}
>>>

Instructions:
- Split the grading rule into its individual requirements and judge each as met or not met. Items the rule
  calls optional get optional=true; they never affect the verdict. Write each fail condition as a point the
  answer must avoid ("Does not present Q3 as the latest quarter"): met=true when the answer avoids it.
- Judge only the requirements written in the grading rule (and its fail conditions); add none of your own.
  Details given in parentheses or as evidence (dates, filing names, sources) help you check a requirement;
  they are not separate requirements unless the rule says they must be stated.
- Numbers: apply the stated tolerance. Wrong fiscal period, unit, scale or entity means not met even if a number is close.
- When checking a figure against the agent's sources, use the source the answer cites for it (match by URL and title).
{TYPE_RULES.get(row["answer_type"], "")}
- verdict = correct if every requirement is met, partial if some, incorrect if none or the core answer is wrong."""
    result = _judge(Correctness, prompt, model=judge)
    final, score = verdict(result)
    return {"score": round(score, 3), **result.model_dump(), "verdict": final, "judge_verdict": result.verdict}


def _same_label(answer: str, reference: str) -> bool:
    """Text cells are fiscal period labels: equal if quarter and fiscal year match, however worded."""
    def key(text):
        for word, n in (("first", 1), ("second", 2), ("third", 3), ("fourth", 4)):
            text = re.sub(rf"\b{word}\s+(?:fiscal\s+)?quarter\b", f"Q{n}", text, flags=re.I)
        quarter = re.search(r"\bQ([1-4])\b", text, re.I)
        year = re.search(r"(?:FY|fiscal(?:\s+year)?)\s*'?(\d{2,4})", text, re.I) or re.search(r"\b(20\d{2})\b", text)
        if quarter and year:
            return quarter.group(1), year.group(1)[-2:]
        return re.sub(r"\W+", " ", text.lower()).strip()
    return key(answer) == key(reference)


def score_table(row: dict, answer: str, judge: str = JUDGE_MODEL) -> dict:
    """Table tasks: the judge only EXTRACTS each requested cell from the answer; code compares to the reference."""
    cells = row["cells"]
    if not answer.strip():
        return {"score": 0.0, "verdict": "incorrect", "points": [], "rationale": "No answer produced.",
                "cells_correct": 0, "cells_total": len(cells)}
    wanted = "\n".join(f"{i}. {c['entity']} | {c['period']} (period ending {c['period_end']}) | {c['metric']} | unit: {c['unit']}"
                       for i, c in enumerate(cells))
    prompt = f"""Extract values from a financial analyst's answer. Do not judge or correct them.

For each requested cell below, find the value the answer gives for exactly that company, period
and metric. Convert it to the requested unit (e.g. $96.2 billion -> 96200 for "USD millions";
a margin of 66.2% -> 66.2 for "%"). If the answer doesn't give that cell, or gives it only for a
different period, set found=false. Text cells: return the text the answer gives.

Requested cells:
{wanted}

Question: {row['question']}

Answer:
<<<
{answer}
>>>"""
    extracted = {c.index: c for c in _judge(CellExtraction, prompt, model=judge).cells}
    points, correct = [], 0
    for i, ref in enumerate(cells):
        got = extracted.get(i)
        if ref["unit"] == "text":
            ok = bool(got and got.found and _same_label(str(got.value), str(ref["value"])))
        else:
            try:
                ok = bool(got and got.found and abs(float(got.value) - float(ref["value"])) <= float(ref["tolerance"]) + 1e-9)
            except (TypeError, ValueError):
                ok = False
        correct += ok
        points.append({"point": f"{ref['entity']} {ref['period']} {ref['metric']} = {ref['value']} {ref['unit']}",
                       "met": ok, "note": f"answer: {got.value if got and got.found else 'missing'}"})
    score = correct / len(cells)
    verdict = "correct" if correct == len(cells) else "partial" if correct else "incorrect"
    return {"score": round(score, 3), "verdict": verdict, "points": points,
            "rationale": f"{correct}/{len(cells)} cells correct", "cells_correct": correct, "cells_total": len(cells)}


def score_citations(answer: str, retrieved: dict[str, dict], attempts: int = 3, judge: str = JUDGE_MODEL) -> dict:
    """Claim-level citation check against the text the agent retrieved.

    The judge sometimes leaves claims undecided even though their source was retrieved; it is asked
    again, and any that stay undecided are counted separately rather than as unsupported.
    """
    empty = {"claims": [], "numeric_claims": 0, "numeric_cited": 0, "cited": 0, "supported": 0, "not_retrieved": 0,
             "undecided": 0}
    if not answer.strip():
        return empty
    prompt = f"""List the factual claims in this answer (at most 15, most important first). For each, give the URL
the answer cites for it (inline or via a numbered source list), or null if none. If that URL appears in the
retrieved sources below, decide whether the retrieved text supports the claim; otherwise set supported to null.
Verify company, metric, period, units, accounting basis, actual versus guidance and publication date.
For a derived figure, check the cited inputs and compute the formula yourself; a calculated result need not
appear verbatim. Rounding allows half the last displayed digit (4.4% means 4.35-4.45%). Wrong arithmetic or
basis, missing inputs or inadequate evidence means false. Explain the evidence before deciding.

Answer:
<<<
{answer}
>>>

Retrieved sources the answer cites (what the agent saw; passages most relevant to the answer):
{json.dumps(excerpts(retrieved, answer, chars=SOURCE_CHARS, cited_only=True), ensure_ascii=False)[:120000]}"""
    for _ in range(attempts):
        out = []
        for c in _judge(Citations, prompt, model=judge).claims:
            in_retrieved = bool(c.cited_url) and norm_url(c.cited_url) in retrieved
            out.append({**c.model_dump(), "in_retrieved": in_retrieved, "supported": c.supported if in_retrieved else None})
        if not any(c["in_retrieved"] and c["supported"] is None for c in out):
            break
        prompt += ("\n\nFor EVERY claim whose cited URL is among the retrieved sources, set supported to true or "
                   "false after checking the text; null is only for claims whose URL was not retrieved.")
    numeric = [c for c in out if c["numeric"]]
    cited = [c for c in out if c["cited_url"]]
    return {"claims": out, "numeric_claims": len(numeric), "numeric_cited": sum(1 for c in numeric if c["cited_url"]),
            "cited": len(cited), "supported": sum(1 for c in cited if c["supported"] is True),
            "not_retrieved": sum(1 for c in cited if not c["in_retrieved"]),
            "undecided": sum(1 for c in cited if c["in_retrieved"] and c["supported"] is None)}


def evidence_recall(row: dict, retrieved: dict[str, dict]) -> dict:
    """Share of the reference answer's figures that appear anywhere in the text the agent retrieved.

    Deterministic (no judge): it measures retrieval, not writing. Figures are the numbers in the
    reference evidence facts; trivial ones (under 10 without decimals) are skipped as too common.
    """
    from agents.writer import grounded, numbers

    wanted = set()
    for ev in row.get("evidence") or []:
        for value in (ev.get("facts") or {}).values():
            for v, d in numbers(json.dumps(value) if not isinstance(value, str) else value):
                if d or abs(v) >= 10:
                    wanted.add((v, d))
    if not wanted:
        return {"figures": 0, "found": 0}
    found_numbers = [v for r in retrieved.values() for v, _ in numbers(r.get("content", ""))]
    found = sum(1 for v, d in wanted if grounded(v, d, found_numbers))
    return {"figures": len(wanted), "found": found}


def score_sources(answer: str, retrieved: dict[str, dict], hosts: set[str]) -> dict:
    cited = sorted({u.rstrip(".,;") for u in URL_RE.findall(answer)})
    return {"cited_urls": cited, "cited_primary": sum(is_primary(u, hosts) for u in cited),
            "retrieved": len(retrieved), "retrieved_primary": sum(is_primary(r["url"], hosts) for r in retrieved.values())}


def _majority(grades: list[dict]) -> dict:
    """The median grade by verdict, then score: with an odd number of votes this is the majority verdict when there is one."""
    rank = {"incorrect": 0, "partial": 1, "correct": 2}
    ordered = sorted(grades, key=lambda g: (rank[g["verdict"]], g["score"]))
    return {**ordered[len(ordered) // 2], "votes": [g["verdict"] for g in grades]}


def score_row(row: dict, output: dict, hosts: set[str], votes: int = 1, judge: str = JUDGE_MODEL) -> dict:
    """All scores for one answer. A judge failure is recorded (scored 0) rather than stopping the run.

    With votes > 1 the correctness judge runs that many times and the majority verdict is kept,
    because reference-free rubric grading varies from call to call. The correctness votes and the
    citation check are independent judge calls, so they run at the same time.
    """
    start = time.perf_counter()
    answer = output.get("answer") or ""
    retrieved = retrieved_index(output.get("tool_results") or [])
    scores = {"sources": score_sources(answer, retrieved, hosts), "recall": evidence_recall(row, retrieved)}

    def grade():
        return score_table(row, answer, judge) if row.get("cells") else score_correctness(row, answer, retrieved, judge)

    with ThreadPoolExecutor(max_workers=votes + 1) as pool:
        grades = [pool.submit(grade) for _ in range(votes)]
        citations = pool.submit(score_citations, answer, retrieved, judge=judge)
        try:
            results = [g.result() for g in grades]
            scores["correctness"] = results[0] if votes == 1 else _majority(results)
        except RuntimeError as exc:
            scores["correctness"] = {"score": 0.0, "verdict": "incorrect", "points": [],
                                     "rationale": f"JUDGE ERROR: {exc}"[:300], "judge_error": True}
        try:
            scores["citations"] = citations.result()
        except RuntimeError as exc:
            scores["citations"] = {"claims": [], "numeric_claims": 0, "numeric_cited": 0, "cited": 0, "supported": 0,
                                   "not_retrieved": 0, "judge_error": str(exc)[:300]}
    scores["judge_s"] = round(time.perf_counter() - start, 1)
    return scores
