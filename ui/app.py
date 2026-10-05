"""Conversational front end for the research agent, built on Chainlit.

    uv run --group ui python -m ui

A message that follows up on the conversation is first rewritten into a standalone question,
then answered by the same pipeline as the CLI and the evals. Pipeline stages show as steps
while it runs; the answer cites a source after every statement and links the sources at the
end, and each answer's evidence (the quotes and calculations behind every statement) opens in
the side panel. Thumbs up and down under each reply record the analyst's verdict on that turn's
trace in Langfuse.
"""

from __future__ import annotations

import asyncio
import hmac
import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import chainlit as cl
from chainlit.input_widget import Switch, TextInput
from chainlit.utils import utc_now

from agents import tracing
from ui.chat import Stopped, describe, failure, research
from ui.render import EVIDENCE

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
    user: cl.User | None = cl.user_session.get("user")
    steps = Steps(parent_id=cl.context.current_step.id)
    cl.user_session.set("steps", steps)
    try:
        async with _one_at_a_time:
            reply = await cl.make_async(research)(message.content.strip(), history, today,
                                                  settings.get("live_web", True), steps,
                                                  f"ui-{cl.context.session.thread_id}", user and user.identifier)
    except Exception as exc:  # model or network failure: report it in the chat and keep the session usable
        error = describe(exc)
        await steps.fail(error)
        await cl.ErrorMessage(content=failure(error)).send()
        return
    answer = await cl.Message(content=reply.content, actions=feedback_buttons(reply.trace_id)).send()
    if reply.panel:
        await show_evidence(cl.Text(name=EVIDENCE, content=reply.panel, display="side"), answer.id)
    if reply.turn:
        history.append(reply.turn)


VOTES = {True: ("thumbs-up", "Helpful"), False: ("thumbs-down", "Not helpful")}
_votes = ThreadPoolExecutor(max_workers=1)  # posts scores in click order, off the event loop


def feedback_buttons(trace_id: str | None, chosen: bool | None = None) -> list[cl.Action]:
    """Thumbs up and down under a reply (none when tracing is off). The chosen one shows its label.

    Ids are derived from the trace, so a vote can redraw both buttons without keeping them in the session.
    """
    if not trace_id:
        return []
    return [cl.Action(name="feedback", payload={"trace_id": trace_id, "helpful": helpful}, icon=icon, tooltip=tip,
                      label=tip if helpful is chosen else "", id=f"{trace_id}-{icon}")
            for helpful, (icon, tip) in VOTES.items()]


@cl.action_callback("feedback")
async def feedback(action: cl.Action):
    """Show the vote at once and score the reply's trace in Langfuse in the background (the API may be slow
    or rate-limited); a click on the other button changes the vote."""
    trace_id, helpful = action.payload["trace_id"], action.payload["helpful"]
    _votes.submit(tracing.feedback, trace_id, helpful)
    for button in feedback_buttons(trace_id):
        await button.remove()
    for button in feedback_buttons(trace_id, chosen=helpful):
        await button.send(for_id=action.forId)


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
