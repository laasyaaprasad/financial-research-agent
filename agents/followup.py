"""Turn an analyst's chat message into a standalone research question, using the conversation so far.

The pipeline researches one self-contained question at a time. In a chat, analysts ask
follow-ups ("and the prior quarter?", "how does that compare with its closest peer?") and
answer the clarification questions the pipeline asks. One model call rewrites the message;
it never answers it, so every figure still comes from the cited pipeline.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from agents.llm import structured

MAX_TURNS = 3       # earlier turns shown to the model
MAX_STATEMENTS = 8  # answer statements kept per turn


class Rewrite(BaseModel):
    question: str | None = Field(description="The latest message as one self-contained research question; "
                                 "null only if it is not a research request")


PROMPT = """You turn a financial analyst's latest chat message into one self-contained research question
about companies. Do not answer it.
- Fill in what the message leaves to the conversation: a company referred to as "it", "they" or "the
  company"; a metric or period carried over ("and the prior quarter?", "what about margins?"); "compare it
  with <another company>". Use the company names and fiscal period labels the earlier turns used.
- If the assistant asked a clarification question, combine the analyst's earlier question with this reply.
- A message that is already self-contained, or starts a new topic, is returned unchanged.
- Keep the analyst's wording and scope: add only what the conversation implies, never a company, metric
  or period it doesn't. Requests the assistant will decline (advice, price targets, estimates) are still
  rewritten; the assistant declines them itself.
- Return null only when the message is not a request for research at all: a greeting, thanks, or a
  question about this assistant."""


def turn(message: str, question: str, output: dict) -> str:
    """One finished turn as later messages may refer to it: the question researched and the answer's main points."""
    lines = [f"Analyst: {message}"]
    if question != message:
        lines.append(f"Researched as: {question}")
    if output.get("clarification"):
        return "\n".join(lines + [f"Assistant asked: {output['clarification']}"])
    companies = ", ".join(f"{c['name']} ({c['ticker']})" for c in output["companies"] if c["resolved"])
    lines.append(f"About: {companies or 'no resolved company'}")
    lines += [f"Interpretation: {a}" for a in output.get("assumptions", [])]
    statements = ([c["text"] for c in output["claims"]]
                  + [f"{c['row']} | {c['column']}: {c['value']}" for c in output.get("table", [])]
                  + [f"Not available: {u['item']}" for u in output["unavailable"]])
    lines += [f"Answer: {s[:200]}" for s in statements[:MAX_STATEMENTS]]
    return "\n".join(lines)


def standalone(message: str, history: list[str], today: date, callbacks=None) -> tuple[str | None, dict]:
    """(The message as a self-contained question, or None if it isn't a research request; token usage).

    A first message has nothing to refer back to and is returned as it is, without a model call.
    """
    if not history:
        return message, {}
    user = (f"Today: {today}\n\nCONVERSATION SO FAR\n" + "\n\n".join(history[-MAX_TURNS:])
            + f"\n\nLATEST MESSAGE\n{message}")
    result, tokens = structured(Rewrite, PROMPT, user, reasoning="low", callbacks=callbacks)
    question = (result.question or "").strip()
    return question or None, tokens
