"""Langfuse tracing (OpenTelemetry-based). A no-op when Langfuse keys aren't configured.

One trace per question: a root `invoke_agent <name>` span (OTel GenAI naming), with the
LangChain callback handler recording every model call (generation, with tokens) and every
Tavily call (tool) underneath it. Eval scores are attached to the trace afterwards.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from dotenv import load_dotenv

load_dotenv()


def enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


@dataclass
class Trace:
    trace_id: str | None = None
    url: str | None = None
    callbacks: list[Any] = field(default_factory=list)
    _span: Any = None

    def finish(self, output: dict) -> None:
        """Record the agent's answer and run metrics on the root span."""
        if self._span is None:
            return
        self._span.update(
            output=output.get("answer"),
            metadata={
                "tavily_credits": output.get("tavily_credits"),
                "searches": sum('search' in c.get('name','') for c in output.get('tool_calls') or []),
                "tavily_calls": len(output.get('tool_calls') or []),
                "latency_s": output.get("latency_s"),
                "tokens_input": (output.get("tokens") or {}).get("input"),
                "tokens_output": (output.get("tokens") or {}).get("output"),
                "error": output.get("error"),
            },
        )


@contextmanager
def trace_question(agent: str, question: str, run_name: str, row: dict | None = None) -> Iterator[Trace]:
    if not enabled():
        yield Trace()
        return

    from langfuse import get_client, propagate_attributes
    from langfuse.langchain import CallbackHandler

    client = get_client()
    golden_id = (row or {}).get("id")
    tags = [agent] + ([golden_id, row["category"], row["difficulty"]] if row else [])
    with client.start_as_current_observation(as_type="agent", name=f"invoke_agent {agent}", input=question) as span:
        with propagate_attributes(
            session_id=run_name,
            trace_name=f"{agent} {golden_id}" if golden_id else agent,
            tags=tags,
            metadata={"golden_id": golden_id or "", "run": run_name, "agent": agent},
        ):
            trace_id = client.get_current_trace_id()
            yield Trace(trace_id=trace_id, url=client.get_trace_url(trace_id=trace_id),
                        callbacks=[CallbackHandler()], _span=span)


def attach_scores(trace_id: str | None, scores: dict) -> None:
    """Attach eval results to the question's trace so failures can be filtered in Langfuse."""
    if not (enabled() and trace_id):
        return
    from langfuse import get_client

    client = get_client()
    c = scores["correctness"]
    cit = scores["citations"]
    client.create_score(trace_id=trace_id, name="correctness", value=float(c["score"]), comment=c["rationale"][:1000])
    client.create_score(trace_id=trace_id, name="fully_correct", value=float(c["verdict"] == "correct"), data_type="BOOLEAN")
    if cit["cited"]:
        client.create_score(trace_id=trace_id, name="citation_support", value=cit["supported"] / cit["cited"])


def flush() -> None:
    if enabled():
        from langfuse import get_client

        get_client().flush()


@dataclass
class ToolSpan:
    span: Any = None

    def finish(self, output: dict):
        if self.span is not None:
            self.span.update(output=output, metadata={'tavily_credits': output.get('credits')})


@contextmanager
def tool_span(name: str, parameters: dict):
    """SDK tools join the current question trace without capturing HTTP headers."""
    if enabled():
        from langfuse import get_client
        client = get_client()
        if client.get_current_trace_id():
            with client.start_as_current_observation(as_type='tool', name=name, input=parameters) as span:
                yield ToolSpan(span)
            return
    yield ToolSpan()
