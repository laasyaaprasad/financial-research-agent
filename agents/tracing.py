"""OpenTelemetry tracing for agent runs, exported over OTLP (Langfuse by default).

Spans use plain OpenTelemetry with the GenAI semantic conventions (`gen_ai.*`) plus the common
`input.value` / `output.value` / `session.id` attributes, so any OTLP backend (Langfuse, Phoenix,
Jaeger, Grafana Tempo…) can receive them. Per question:
  - one root `invoke_agent <agent>` span (the trace),
  - one span per pipeline step (`resolve`, `plan`, `sec_evidence`, `web_evidence`, `write`, …),
  - one `chat <model>` span per model call (tokens and cost), nested under its step,
  - one span per Tavily call (parameters, cache or live, credits, result URLs).
LangChain's internal chain and graph runs are deliberately not traced: Langfuse counts every observation.

Backend selection: if OTEL_EXPORTER_OTLP_TRACES_ENDPOINT / OTEL_EXPORTER_OTLP_ENDPOINT is set, the
standard OTel env config is used as-is. Otherwise spans go to Langfuse's OTLP endpoint using
LANGFUSE_BASE_URL (or LANGFUSE_HOST) / LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY. TRACING=off
disables everything. Tracing never raises into a run.

The only Langfuse-specific code is at the bottom: attaching eval scores and building trace links,
which OpenTelemetry has no standard for.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from dotenv import load_dotenv
from langchain_core.callbacks import BaseCallbackHandler
from opentelemetry import context as otel_context
from opentelemetry import trace as otel
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from agents import pricing

load_dotenv()

SERVICE = "fin-research-agent"
MAX_CHARS = 2000  # per text field, to keep payloads small
_tracer: Any = None
_provider: TracerProvider | None = None
_setup_lock = threading.Lock()


def _langfuse_base() -> str | None:
    base = os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST")
    return base.rstrip("/") if base else None


def _langfuse_auth() -> str | None:
    pk, sk = os.getenv("LANGFUSE_PUBLIC_KEY"), os.getenv("LANGFUSE_SECRET_KEY")
    return "Basic " + base64.b64encode(f"{pk}:{sk}".encode()).decode() if pk and sk else None


def configure(exporter=None) -> None:
    """Set up the tracer with `exporter`, or from the environment when none is given (tests pass their own)."""
    global _tracer, _provider
    provider = None
    if exporter is None and os.getenv("TRACING", "on") != "off":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        if os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
            exporter = OTLPSpanExporter()  # standard OTel env config
        elif _langfuse_auth() and _langfuse_base():
            exporter = OTLPSpanExporter(endpoint=_langfuse_base() + "/api/public/otel/v1/traces",
                                        headers={"Authorization": _langfuse_auth(), "x-langfuse-ingestion-version": "4"})
    if exporter is not None:
        provider = TracerProvider(resource=Resource.create({"service.name": SERVICE}))
        provider.add_span_processor(BatchSpanProcessor(exporter))
    # Assigned last, so a thread never sees a half-built tracer.
    _provider, _tracer = provider, provider.get_tracer(SERVICE) if provider else False


def tracer():
    """The OTel tracer, or None if tracing is off or no backend is configured."""
    if _tracer is None:
        with _setup_lock:  # eval questions start in parallel threads: set up once
            if _tracer is None:
                configure()
    return _tracer or None


def enabled() -> bool:
    return tracer() is not None


def _clip(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= MAX_CHARS else text[:MAX_CHARS] + f"… [+{len(text) - MAX_CHARS} chars]"


def _in_trace() -> bool:
    return otel.get_current_span().get_span_context().is_valid


def _set(span, attributes: dict) -> None:
    """Set attributes, skipping None (OTel rejects it)."""
    for k, v in attributes.items():
        if v is not None:
            span.set_attribute(k, v)


# --- one trace per question ---------------------------------------------------------------------

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
        tokens = output.get("tokens") or {}
        _set(self._span, {
            "output.value": _clip(output.get("answer") or ""),
            "run.tavily_credits": output.get("tavily_credits"),
            "run.tavily_calls": len(output.get("tool_calls") or []),
            "run.latency_s": output.get("latency_s"),
            "gen_ai.usage.input_tokens": tokens.get("input"),
            "gen_ai.usage.output_tokens": tokens.get("output"),
            "run.error": output.get("error"),
        })
        if output.get("error"):
            self._span.set_status(otel.Status(otel.StatusCode.ERROR, _clip(output["error"])))


@contextmanager
def trace_question(agent: str, question: str, run_name: str, row: dict | None = None) -> Iterator[Trace]:
    """Root span for one question. Model calls made with `trace.callbacks` and steps opened inside nest under it."""
    t = tracer()
    if not t:
        yield Trace()
        return
    golden_id = (row or {}).get("id")
    tags = [agent] + ([golden_id, row["category"], row["difficulty"]] if row else [])
    metadata = {"golden_id": golden_id or "", "run": run_name, "agent": agent}
    attributes = {
        "gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": agent,
        "input.value": _clip(question), "session.id": run_name,
        "langfuse.observation.type": "agent",
        "langfuse.trace.name": f"{agent} {golden_id}" if golden_id else agent,
        "langfuse.trace.tags": [str(x) for x in tags if x],
        **{f"langfuse.trace.metadata.{k}": v for k, v in metadata.items()},
        **{f"langfuse.observation.metadata.{k}": v for k, v in metadata.items()},
    }
    with t.start_as_current_span(f"invoke_agent {agent}", attributes=attributes) as span:
        tid = format(span.get_span_context().trace_id, "032x")
        yield Trace(trace_id=tid, url=trace_url(tid), callbacks=[LeanCallbackHandler()], _span=span)


@contextmanager
def step(name: str, **attributes):
    """A pipeline step as a child span of the current trace; model and search spans inside it nest under it."""
    t = tracer()
    if not (t and _in_trace()):
        yield None
        return
    with t.start_as_current_span(name, attributes={f"step.{k}": _clip(v) for k, v in attributes.items()}) as span:
        yield span


def set_output(span, output: Any, **attributes) -> None:
    if span is not None:
        span.set_attribute("output.value", _clip(output))
        _set(span, {f"step.{k}": v for k, v in attributes.items()})


# --- Tavily calls ---------------------------------------------------------------------------------

def _results(response: Any) -> list[dict]:
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            return []
    results = response.get("results") if isinstance(response, dict) else None
    return [{"url": r.get("url"), "title": r.get("title"), "score": r.get("score")}
            for r in results or [] if isinstance(r, dict)]


@dataclass
class ToolSpan:
    span: Any = None

    def finish(self, response: dict, served_by: str = "live") -> None:
        """Record where the response came from (live, cache or offline), credits spent and the result URLs."""
        if self.span is None:
            return
        _set(self.span, {
            "tavily.served_by": served_by,
            "tavily.cache_hit": served_by == "cache",
            "tavily.credits": float((response.get("usage") or {}).get("credits", 0)) if served_by == "live" else 0.0,
            "output.value": _clip(_results(response)),
        })
        if response.get("error") and served_by == "live":  # an offline cache miss is expected, not a failure
            self.span.set_status(otel.Status(otel.StatusCode.ERROR, _clip(response["error"])))


@contextmanager
def tool_span(name: str, parameters: dict) -> Iterator[ToolSpan]:
    """A retriever span inside the current question's trace (records parameters, never HTTP headers)."""
    t = tracer()
    if not (t and _in_trace()):
        yield ToolSpan()
        return
    with t.start_as_current_span(name, attributes={
        "input.value": _clip(parameters), "langfuse.observation.type": "retriever",
        "openinference.span.kind": "RETRIEVER",
    }) as span:
        yield ToolSpan(span)


# --- model and tool calls made through LangChain ----------------------------------------------------

def _messages(messages) -> list[dict]:
    out = []
    for m in messages:
        item = {"role": m.type, "content": _clip(m.content if isinstance(m.content, str) else str(m.content))}
        if getattr(m, "tool_calls", None):
            item["tool_calls"] = [{"name": c["name"], "args": c["args"]} for c in m.tool_calls]
        out.append(item)
    return out


class LeanCallbackHandler(BaseCallbackHandler):
    """Records chat-model calls as `chat <model>` spans (GenAI conventions) and tool calls as tool spans.

    Spans open under the caller's current span (the pipeline step) and fall back to the question's root.
    """

    def __init__(self):
        self.root = otel_context.get_current()
        self.open: dict = {}

    def _start(self, name: str, attributes: dict, run_id) -> None:
        t = tracer()
        if t:
            self.open[run_id] = t.start_span(name, context=None if _in_trace() else self.root, attributes=attributes)

    def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs):
        params = kwargs.get("invocation_params") or {}
        model = (kwargs.get("metadata") or {}).get("ls_model_name") or params.get("model") or params.get("model_name") or "unknown"
        self._start(f"chat {model}", {
            "gen_ai.operation.name": "chat", "gen_ai.provider.name": "nebius", "gen_ai.request.model": model,
            "langfuse.observation.type": "generation", "input.value": _clip(_messages(messages[0])),
        }, run_id)

    def on_llm_end(self, response, *, run_id, **kwargs):
        span = self.open.pop(run_id, None)
        if span is None:
            return
        msg = getattr(response.generations[0][0], "message", None)
        usage = getattr(msg, "usage_metadata", None) or {}
        i, o = usage.get("input_tokens", 0), usage.get("output_tokens", 0)
        output = {"content": getattr(msg, "content", "") or ""}
        if getattr(msg, "tool_calls", None):
            output["tool_calls"] = [{"name": c["name"], "args": c["args"]} for c in msg.tool_calls]
        model = span.attributes.get("gen_ai.request.model", "")
        _set(span, {"gen_ai.usage.input_tokens": i, "gen_ai.usage.output_tokens": o,
                    "gen_ai.usage.cost": pricing.cost_usd(model, i, o)["total"], "output.value": _clip(output)})
        span.end()

    def on_tool_start(self, serialized, input_str, *, run_id, **kwargs):
        name = (serialized or {}).get("name") or kwargs.get("name") or "tool"
        kind = "retriever" if name.startswith("tavily") else "tool"
        self._start(name, {"input.value": _clip(kwargs.get("inputs") or input_str), "langfuse.observation.type": kind,
                           "openinference.span.kind": kind.upper()}, run_id)

    def on_tool_end(self, output, *, run_id, **kwargs):
        span = self.open.pop(run_id, None)
        if span is not None:
            content = getattr(output, "content", output)
            span.set_attribute("output.value", _clip(_results(content) or content))
            span.end()

    def _error(self, error, run_id) -> None:
        span = self.open.pop(run_id, None)
        if span is not None:
            span.set_status(otel.Status(otel.StatusCode.ERROR, _clip(str(error))))
            span.end()

    def on_llm_error(self, error, *, run_id, **kwargs):
        self._error(error, run_id)

    def on_tool_error(self, error, *, run_id, **kwargs):
        self._error(error, run_id)


def flush() -> None:
    """Send any buffered spans (call before the process exits)."""
    if _provider is not None:
        _provider.force_flush()


# --- Langfuse-specific: scores and trace links (no OpenTelemetry standard for these) ---------------

def _langfuse_api(method: str, path: str, **kwargs):
    """Best-effort Langfuse REST call: throttled, backs off on 429, never raises (tracing must not break runs)."""
    import time

    import httpx

    base, auth = _langfuse_base(), _langfuse_auth()
    if not (base and auth):
        return None
    for attempt in range(4):
        try:
            time.sleep(0.25)  # stay well under the free tier's API rate limit
            r = httpx.request(method, base + path, headers={"Authorization": auth}, timeout=20, **kwargs)
            if r.status_code == 429:
                time.sleep(float(r.headers.get("retry-after") or 5 * (attempt + 1)))
                continue
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as exc:
            print(f"[tracing] Langfuse {method} {path} failed: {type(exc).__name__}", file=sys.stderr)
            return None
    print(f"[tracing] Langfuse {method} {path} still rate-limited; skipped", file=sys.stderr)
    return None


_project: list[str] = []  # cached Langfuse project id (only once found, so a failed lookup is retried)
_project_lock = threading.Lock()


def _project_id() -> str | None:
    with _project_lock:
        if not _project:
            data = _langfuse_api("GET", "/api/public/projects")
            if data and data.get("data"):
                _project.append(data["data"][0]["id"])
    return _project[0] if _project else None


def trace_url(tid: str | None) -> str | None:
    """Link to the trace in Langfuse (None for other OTLP backends)."""
    if not tid or os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return None
    base, pid = _langfuse_base(), _project_id()
    return f"{base}/project/{pid}/traces/{tid}" if base and pid else None


def score(tid: str | None, name: str, value, data_type: str, comment: str | None = None) -> None:
    """Attach an eval score to a trace (data_type: NUMERIC, CATEGORICAL or BOOLEAN).

    The score id is derived from (trace, name), so re-grading updates the score instead of adding one.
    """
    if tid and enabled():
        _langfuse_api("POST", "/api/public/scores", json={
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{tid}/{name}")),
            "traceId": tid, "name": name, "value": value, "dataType": data_type,
            **({"comment": _clip(comment)} if comment else {}),
        })


def attach_scores(trace_id: str | None, scores: dict) -> None:
    """Attach eval results to the question's trace so failures can be filtered in Langfuse."""
    if not (trace_id and enabled()):
        return
    c, cit = scores["correctness"], scores["citations"]
    if c.get("score") is not None:
        score(trace_id, "correctness", float(c["score"]), "NUMERIC", comment=(c.get("rationale") or "")[:1000])
        score(trace_id, "fully_correct", float(c.get("verdict") == "correct"), "BOOLEAN")
    if cit.get("cited"):
        score(trace_id, "citation_support", cit["supported"] / cit["cited"], "NUMERIC")
