"""One chat turn: a follow-up is rewritten into a standalone question, researched by the pipeline and rendered.

Each turn is one trace in the chat's Langfuse session, under the signed-in name. The trace's input is the
analyst's message and its output is the reply exactly as the chat shows it (the cited answer, the help text,
or the failure), so Langfuse's session view replays the conversation as the analyst saw it. No Chainlit here,
so the turn can be tested offline.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from agents import tracing
from agents.followup import standalone, turn
from agents.pipeline import run
from ui.render import render

HELP = ("I research SEC-reporting companies and cite a source for every statement. Ask about reported results, "
        "calculations over them (growth, margins, trailing twelve months), guidance, management commentary, recent "
        "developments, or a comparison table across companies or periods. Follow-up questions can refer to earlier "
        "answers. I don't give investment advice, price targets, share prices or consensus estimates.")


class Stopped(Exception):
    pass


@dataclass
class Reply:
    content: str               # the answer, or the help text when the message isn't a research request
    panel: str | None = None   # the answer's Evidence panel
    turn: str | None = None    # the turn as later messages may refer to it; None when nothing was researched
    trace_id: str | None = None


def describe(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"[:300]


def failure(error: str) -> str:
    return f"The research failed ({error}). Try again, or rephrase the question."


def research(message: str, history: list[str], today: date, live_web: bool, steps: Callable[[str, str | None], None],
             session: str, user: str | None) -> Reply:
    """The chat's reply to `message`. `steps(stage, detail)` shows progress and raises Stopped once the user stops."""
    with tracing.trace_question("agent", message, session, user=user, tags=["chat"]) as trace:
        try:
            question = message
            if history:
                steps("Read the conversation", None)
                with tracing.step("followup", turns=len(history)) as span:
                    question, _ = standalone(message, history, today, trace.callbacks)
                    tracing.set_output(span, question or "Not a research request")
                steps("Read the conversation", f"Researching: {question}" if question else "Not a research request")
            if question:
                output = run(question, today=today, callbacks=trace.callbacks, live_web=live_web, on_step=steps)
                trace.finish(output)
                content, panel = render(output, today, question, rewritten=question != message)
                reply = Reply(content, panel, turn(message, question, output), trace.trace_id)
            else:
                reply = Reply(HELP, trace_id=trace.trace_id)
        except Exception as exc:
            trace.reply("Stopped" if isinstance(exc, Stopped) else failure(describe(exc)))
            raise
        trace.reply(reply.content)
    tracing.flush()
    return reply
