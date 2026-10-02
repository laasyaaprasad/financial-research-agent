"""Scorers for the golden set: correctness, citations and source quality.

The judge is a different model family from the agents under test (DeepSeek on Nebius vs.
Kimi), so an agent never grades its own output.
"""

from __future__ import annotations

import json
import re
from typing import Literal
from urllib.parse import urlparse

from dotenv import load_dotenv
from langchain_nebius import ChatNebius
from pydantic import BaseModel, Field

load_dotenv()

JUDGE_MODEL = "deepseek-ai/DeepSeek-V4-Pro"
URL_RE = re.compile(r"https?://[^\s\)\]>\"'`,]+")


# ---------- judge output schemas ----------

class Point(BaseModel):
    point: str = Field(description="One grading requirement, taken from the grading rule")
    met: bool
    note: str = Field(description="Short reason, quoting the agent's value where relevant")


class Correctness(BaseModel):
    points: list[Point]
    verdict: Literal["correct", "partial", "incorrect"]
    rationale: str


class Claim(BaseModel):
    claim: str = Field(description="One factual claim from the answer, in a few words")
    numeric: bool = Field(description="True if the claim states a number, date or percentage")
    cited_url: str | None = Field(description="URL the answer cites for this claim, or null")
    supported: bool | None = Field(
        description="Whether the retrieved text for cited_url supports the claim; null if no citation or the URL was not retrieved"
    )


class Citations(BaseModel):
    claims: list[Claim]


# ---------- helpers ----------

def _judge():
    return ChatNebius(model=JUDGE_MODEL, temperature=0)


def _structured(schema, prompt: str, retries: int = 2):
    llm = _judge().with_structured_output(schema)
    last = None
    for _ in range(retries + 1):
        try:
            return llm.invoke(prompt)
        except Exception as exc:  # judge returned malformed output; retry
            last = exc
    raise last


def norm_url(url: str) -> str:
    p = urlparse(url.strip().rstrip(".,;"))
    return (p.netloc.lower().removeprefix("www.") + p.path.rstrip("/")).lower()


def retrieved_index(tool_results: list[dict]) -> dict[str, dict]:
    """Map normalized URL -> retrieved result (title, content, date)."""
    idx = {}
    for payload in tool_results:
        for r in (payload or {}).get("results", []) or []:
            if r.get("url"):
                idx[norm_url(r["url"])] = {
                    "url": r["url"],
                    "title": r.get("title", ""),
                    "published_date": r.get("published_date"),
                    "content": (r.get("content") or "")[:1500],
                }
    return idx


def _primary_hosts(golden: list[dict]) -> set[str]:
    hosts = {"sec.gov"}
    for row in golden:
        for ev in row.get("evidence") or []:
            if ev.get("source_type") == "primary":
                hosts.add(urlparse(ev["url"]).netloc.lower().removeprefix("www."))
    return hosts


def is_primary(url: str, primary_hosts: set[str]) -> bool:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return (
        host in primary_hosts
        or host.endswith(".sec.gov")
        or host.split(".")[0] in {"investor", "investors", "ir"}
    )


# ---------- scorers ----------

def score_correctness(row: dict, answer: str, retrieved: dict[str, dict]) -> dict:
    if not answer.strip():
        return {"score": 0.0, "verdict": "incorrect", "points": [], "rationale": "No answer produced."}

    if row["time_sensitivity"] == "dynamic":
        reference_block = (
            "This question is TIME-SENSITIVE. Grade reference-free against the grading rubric, using the "
            "agent's retrieved sources below for recency and support. The snapshot answer is context only "
            f"(as of {row.get('as_of', '2026-10-01')}); do not require an exact match to it.\n\n"
            f"Snapshot answer (context): {row.get('answer')}\n\n"
            f"Agent's retrieved sources:\n{json.dumps(list(retrieved.values())[:15], ensure_ascii=False)[:12000]}"
        )
    else:
        reference_block = (
            f"Verified reference answer: {row.get('answer')}\n"
            f"Reference facts: {json.dumps([e.get('facts') for e in row.get('evidence') or []], ensure_ascii=False)}\n"
            f"Reference calculations: {json.dumps(row.get('calculations'), ensure_ascii=False)}"
        )

    prompt = f"""You are grading a financial research agent's answer for an analyst. Be strict and literal.

Question: {row['question']}
Answer type: {row['answer_type']}
Grading rule: {row['grading']}
Failure mode this question tests: {row['failure_mode']}

{reference_block}

Agent's answer:
<<<
{answer}
>>>

Instructions:
- Split the grading rule into its individual requirements and judge each one as met or not met.
- Numbers: apply the stated tolerance. Wrong fiscal period, wrong unit or scale, or wrong entity means not met even if a number is close.
- Abstain questions: the requirement is met only if the agent clearly says the figure is not available/disclosed, and does not present any number as an actual reported result.
- verdict = correct if all requirements are met, partial if some, incorrect if none or the core answer is wrong."""
    result = _structured(Correctness, prompt)
    met = sum(p.met for p in result.points)
    score = met / len(result.points) if result.points else 0.0
    return {"score": round(score, 3), **result.model_dump()}


def score_citations(answer: str, retrieved: dict[str, dict]) -> dict:
    if not answer.strip():
        return {"claims": [], "numeric_claims": 0, "numeric_cited": 0, "cited": 0, "supported": 0, "not_retrieved": 0}

    prompt = f"""List the factual claims in this answer (at most 15, most important first). For each, give the URL
the answer cites for it (inline or in a sources list clearly tied to the claim), or null if none.
Then, if that URL appears in the retrieved sources below, decide whether the retrieved text supports the claim
(numbers must match within rounding). If the URL is not in the retrieved sources, set supported to null.

Answer:
<<<
{answer}
>>>

Retrieved sources (what the agent actually saw):
{json.dumps(list(retrieved.values()), ensure_ascii=False)[:20000]}"""
    claims = _structured(Citations, prompt).claims

    out = []
    for c in claims:
        in_retrieved = bool(c.cited_url) and norm_url(c.cited_url) in retrieved
        supported = c.supported if in_retrieved else None
        out.append({**c.model_dump(), "in_retrieved": in_retrieved, "supported": supported})

    numeric = [c for c in out if c["numeric"]]
    cited = [c for c in out if c["cited_url"]]
    return {
        "claims": out,
        "numeric_claims": len(numeric),
        "numeric_cited": sum(1 for c in numeric if c["cited_url"]),
        "cited": len(cited),
        "supported": sum(1 for c in cited if c["supported"] is True),
        "not_retrieved": sum(1 for c in cited if not c["in_retrieved"]),
    }


def score_sources(answer: str, retrieved: dict[str, dict], primary_hosts: set[str]) -> dict:
    cited = sorted({u.rstrip(".,;") for u in URL_RE.findall(answer)})
    return {
        "cited_urls": cited,
        "cited_primary": sum(is_primary(u, primary_hosts) for u in cited),
        "retrieved": len(retrieved),
        "retrieved_primary": sum(is_primary(r["url"], primary_hosts) for r in retrieved.values()),
    }


def score_row(row: dict, output: dict, primary_hosts: set[str]) -> dict:
    answer = output.get("answer") or ""
    retrieved = retrieved_index(output.get("tool_results") or [])
    return {
        "correctness": score_correctness(row, answer, retrieved),
        "citations": score_citations(answer, retrieved),
        "sources": score_sources(answer, retrieved, primary_hosts),
    }
