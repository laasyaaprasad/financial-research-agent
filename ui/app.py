"""Conversational front end for the research agent, built on Chainlit.

    uv run --group ui python -m ui

A message that follows up on the conversation is first rewritten into a standalone question,
then answered by the same pipeline as the CLI and the evals. Pipeline stages show as steps
while it runs; the answer cites a source after every statement and links the sources at the
end, and each answer's evidence (the quotes and calculations behind every statement) opens in
the side panel.
"""

from __future__ import annotations

import asyncio
import hmac
import os
import secrets
from datetime import date

import chainlit as cl
from chainlit.input_widget import Switch, TextInput
from chainlit.utils import utc_now

from agents import tracing
from agents.followup import standalone, turn
from agents.pipeline import run
from ui.render import EVIDENCE, render

HELP = ("I research SEC-reporting companies and cite a source for every statement. Ask about reported results, "
        "calculations over them (growth, margins, trailing twelve months), guidance, management commentary, recent "
        "developments, or a comparison table across companies or periods. Follow-up questions can refer to earlier "
        "answers. I don't give investment advice, price targets, share prices or consensus estimates.")


# One shared password keeps the app from being used up by strangers; the name on the sign-in form is optional.
PASSWORD = "tavilyfde"
os.environ.setdefault("CHAINLIT_AUTH_SECRET", secrets.token_urlsafe(48))  # signs sessions; a restart signs users out


@cl.password_auth_callback
async def login(username: str, password: str) -> cl.User | None:
    if hmac.compare_digest(password.encode(), PASSWORD.encode()):
        return cl.User(identifier=username.strip() or "guest")
    await asyncio.sleep(1)  # slows down password guessing
    return None


_one_at_a_time = asyncio.Lock()  # a small instance answers one question at a time


@cl.set_starters
async def starters():
    return [
        cl.Starter(label="Latest quarter", message="How did PepsiCo do in its latest reported quarter?"),
        cl.Starter(label="Peer comparison table",
                   message="Compare revenue, gross margin and operating margin for Intel and IBM in their latest "
                           "reported quarters"),
        cl.Starter(label="Quarterly trend",
                   message="Show Chipotle's quarterly revenue and operating margin for its last four reported "
                           "quarters"),
        cl.Starter(label="Guidance", message="What revenue guidance did ServiceNow give for its next quarter?"),
    ]


@cl.on_chat_start
async def start():
    cl.user_session.set("history", [])
    cl.user_session.set("evidence", [])
    settings = await cl.ChatSettings([
        TextInput(id="as_of", label="As-of date (YYYY-MM-DD, empty for today)", initial=""),
        Switch(id="live_web", label="Live web search (spends Tavily credits; cached results are always reused)",
               initial=True),
    ]).send()
    cl.user_session.set("settings", settings)


@cl.on_settings_update
async def settings_update(settings: dict):
    cl.user_session.set("settings", settings)


class Stopped(Exception):
    pass


class Steps:
    """Shows pipeline stages as Chainlit steps. Called from the worker thread that runs the pipeline,
    which stops at the next stage once the user presses stop."""

    def __init__(self, parent_id: str):
        self.parent_id = parent_id
        self.running: dict[str, cl.Step] = {}
        self.stopped = False

    def __call__(self, stage: str, detail: str | None) -> None:
        if self.stopped:
            raise Stopped
        cl.run_sync(self.show(stage, detail))

    async def show(self, stage: str, detail: str | None) -> None:
        if detail is None:
            step = cl.Step(name=stage, type="tool", parent_id=self.parent_id, show_input=False)
            step.start = utc_now()
            self.running[stage] = step
            await step.send()
            return
        step = self.running.pop(stage)
        step.output, step.end = detail, utc_now()
        await step.update()

    async def fail(self, error: str) -> None:
        for step in self.running.values():
            step.output, step.end, step.is_error = error, utc_now(), True
            await step.update()
        self.running.clear()


def research(message: str, history: list[str], today: date, live_web: bool, steps: Steps,
             session: str) -> tuple[str | None, dict | None]:
    """(Question researched, pipeline output); (None, None) when the message isn't a research request."""
    with tracing.trace_question("agent", message, session) as trace:
        question = message
        if history:
            steps("Read the conversation", None)
            question, _ = standalone(message, history, today, trace.callbacks)
            steps("Read the conversation", f"Researching: {question}" if question else "Not a research request")
        output = None
        if question:
            output = run(question, today=today, callbacks=trace.callbacks, live_web=live_web, on_step=steps)
            trace.finish(output)
    tracing.flush()
    return question, output


@cl.on_stop
async def stop():
    steps: Steps | None = cl.user_session.get("steps")
    if steps:
        steps.stopped = True
        await steps.fail("Stopped")


@cl.on_message
async def on_message(message: cl.Message):
    settings = cl.user_session.get("settings") or {}
    try:
        today = date.fromisoformat(settings["as_of"].strip()) if (settings.get("as_of") or "").strip() else date.today()
    except ValueError:
        await cl.ErrorMessage(content=f"The as-of date '{settings['as_of']}' isn't YYYY-MM-DD; "
                                      "fix it in the settings.").send()
        return
    history: list[str] = cl.user_session.get("history")
    text = message.content.strip()
    steps = Steps(parent_id=cl.context.current_step.id)
    cl.user_session.set("steps", steps)
    try:
        async with _one_at_a_time:
            question, output = await cl.make_async(research)(text, history, today, settings.get("live_web", True),
                                                             steps, f"ui-{cl.context.session.thread_id}")
    except Exception as exc:  # model or network failure: report it in the chat and keep the session usable
        error = f"{type(exc).__name__}: {exc}"[:300]
        await steps.fail(error)
        await cl.ErrorMessage(content=f"The research failed ({error}). Try again, or rephrase the question.").send()
        return
    if output is None:
        await cl.Message(content=HELP).send()
        return
    content, panel = render(output, today, question, rewritten=question != text)
    answer = await cl.Message(content=content).send()
    if panel:
        await show_evidence(cl.Text(name=EVIDENCE, content=panel, display="side"), answer.id)
    history.append(turn(text, question, output))


async def show_evidence(panel: cl.Text, answer_id: str) -> None:
    """Attach an answer's Evidence panel, keeping the conversation's panels newest first.

    Chainlit opens the side view with every side element in the chat, in the order they arrived,
    so earlier panels are re-sent after the new one. Each answer's own link opens only its panel.
    """
    earlier: list[cl.Text] = cl.user_session.get("evidence")
    for element in earlier:
        await element.remove()
    await panel.send(for_id=answer_id)
    for element in reversed(earlier):
        await element.send(for_id=element.for_id)
    earlier.append(panel)
