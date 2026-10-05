"""Offline tests for tracing: span structure, Tavily spans, chat turns, scores and the off switch (no network)."""

import asyncio
import hashlib
import json
import uuid
from datetime import date

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agents import tracing
from agents.research import Web
from ui import chat

ROW = {"id": "G01", "category": "reported", "difficulty": "easy"}
MODEL = "deepseek-ai/DeepSeek-V4.1-Flash"


class Recorder:
    def __init__(self):
        self.exporter = InMemorySpanExporter()
        self.api_calls: list[tuple] = []

    def spans(self, name: str | None = None) -> list:
        tracing.flush()
        return [s for s in self.exporter.get_finished_spans() if name is None or s.name == name]

    def one(self, name: str):
        (span,) = self.spans(name)
        return span


@pytest.fixture
def rec(monkeypatch):
    """Tracing on, exporting to memory; the Langfuse REST API is stubbed out."""
    r = Recorder()
    monkeypatch.setattr(tracing, "_langfuse_api", lambda method, path, **kw: r.api_calls.append((method, path, kw)))
    tracing._project.clear()
    tracing.configure(r.exporter)
    yield r
    tracing._tracer, tracing._provider = False, None  # leave tracing off for the rest of the session


def _cache(tmp_path, operation, params, response):
    key = hashlib.sha256(json.dumps([operation, params], sort_keys=True).encode()).hexdigest()
    (tmp_path / f"{key}.json").write_text(json.dumps({"operation": operation, "params": params, "response": response}))


def _model(input_tokens=1000, output_tokens=200):
    return GenericFakeChatModel(messages=iter([AIMessage(content="ok", usage_metadata={
        "input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": input_tokens + output_tokens})]))


def test_model_calls_nest_under_their_step_with_tokens_and_cost(rec):
    with tracing.trace_question("agent", "What was Acme's revenue?", "run1", ROW) as trace:
        with tracing.step("plan"):
            _model().invoke("plan this", config={"callbacks": trace.callbacks, "metadata": {"ls_model_name": MODEL}})
        trace.finish({"answer": "Revenue was $1.", "tokens": {"input": 1000, "output": 200}, "tavily_credits": 0})

    root, plan, chat = rec.one("invoke_agent agent"), rec.one("plan"), rec.one(f"chat {MODEL}")
    assert root.parent is None and trace.trace_id == format(root.context.trace_id, "032x")
    assert root.attributes["langfuse.trace.metadata.golden_id"] == "G01"
    assert root.attributes["session.id"] == "run1"
    assert root.attributes["output.value"] == "Revenue was $1."
    assert "user.id" not in root.attributes  # eval runs have no user
    assert plan.parent.span_id == root.context.span_id
    assert chat.parent.span_id == plan.context.span_id
    assert chat.attributes["gen_ai.usage.input_tokens"] == 1000
    assert chat.attributes["gen_ai.usage.output_tokens"] == 200
    assert chat.attributes["gen_ai.usage.cost"] == pytest.approx(1000 * 0.30 / 1e6 + 200 * 1.20 / 1e6)


def test_model_call_outside_a_step_nests_under_the_question(rec):
    with tracing.trace_question("starter", "q", "run1") as trace:
        _model().invoke("q", config={"callbacks": trace.callbacks, "metadata": {"ls_model_name": MODEL}})
    assert rec.one(f"chat {MODEL}").parent.span_id == rec.one("invoke_agent starter").context.span_id


def test_tavily_calls_record_cache_offline_and_results_without_page_text(rec, tmp_path):
    params = {"query": "acme revenue", "max_results": 5}
    _cache(tmp_path, "search", params, {"results": [
        {"url": "https://www.sec.gov/x", "title": "10-Q", "score": 0.9, "content": "third-party page text"}]})
    web = Web(tmp_path, live=False)
    with tracing.trace_question("agent", "q", "run1", ROW):
        with tracing.step("web_evidence"):
            asyncio.run(web.call("search", **params))
            asyncio.run(web.call("search", query="not cached"))

    step = rec.one("web_evidence")
    hit, miss = rec.spans("tavily_search")
    assert [hit.attributes["tavily.served_by"], miss.attributes["tavily.served_by"]] == ["cache", "offline"]
    assert hit.parent.span_id == step.context.span_id and miss.parent.span_id == step.context.span_id
    assert hit.attributes["tavily.credits"] == 0 and hit.attributes["tavily.cache_hit"] is True
    assert json.loads(hit.attributes["output.value"]) == [{"url": "https://www.sec.gov/x", "title": "10-Q", "score": 0.9}]
    assert json.loads(hit.attributes["input.value"]) == params
    assert miss.status.is_ok  # an offline cache miss is expected, not an error
    assert web.calls == [] and web.credits == 0  # cache and offline calls still spend nothing


def test_langchain_tool_calls_become_retriever_spans(rec):
    from uuid import uuid4

    with tracing.trace_question("starter", "q", "run1") as trace:
        handler, run_id = trace.callbacks[0], uuid4()
        handler.on_tool_start({"name": "tavily_search"}, "acme", run_id=run_id, inputs={"query": "acme"})
        handler.on_tool_end(json.dumps({"results": [{"url": "https://a.example", "title": "A", "score": 0.5}]}),
                            run_id=run_id)
    span = rec.one("tavily_search")
    assert span.attributes["langfuse.observation.type"] == "retriever"
    assert json.loads(span.attributes["output.value"]) == [{"url": "https://a.example", "title": "A", "score": 0.5}]


def test_steps_and_searches_outside_a_question_are_not_traced(rec, tmp_path):
    with tracing.step("plan") as span:
        assert span is None
    asyncio.run(Web(tmp_path, live=False).call("search", query="x"))
    assert rec.spans() == []


def test_scores_have_stable_ids_so_regrading_updates_them(rec):
    scores = {"correctness": {"score": 1.0, "verdict": "correct", "rationale": "matches"},
              "citations": {"cited": 4, "supported": 3}}
    tracing.attach_scores("abc123", scores)
    tracing.attach_scores("abc123", scores)
    posted = [kw["json"] for method, path, kw in rec.api_calls if path == "/api/public/scores"]
    assert [p["name"] for p in posted] == ["correctness", "fully_correct", "citation_support"] * 2
    assert posted[0]["id"] == posted[3]["id"] == str(uuid.uuid5(uuid.NAMESPACE_URL, "abc123/correctness"))
    assert posted[2]["value"] == 0.75


def test_parallel_questions_all_get_a_trace(monkeypatch):
    """Eval questions start in parallel threads; none may see a half-configured tracer as "tracing off"."""
    import threading
    import time

    exporter, real = InMemorySpanExporter(), tracing.configure

    class SlowProvider(tracing.TracerProvider):
        def __init__(self, *args, **kwargs):
            time.sleep(0.2)  # widen the window in which other threads ask for the tracer
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(tracing, "TracerProvider", SlowProvider)
    monkeypatch.setattr(tracing, "configure", lambda exporter_arg=None: real(exporter))
    monkeypatch.setattr(tracing, "_langfuse_api", lambda *a, **k: None)
    tracing._tracer, tracing._provider = None, None
    ids, barrier = [], threading.Barrier(4)

    def ask():
        barrier.wait()
        with tracing.trace_question("agent", "q", "run1") as trace:
            ids.append(trace.trace_id)

    threads = [threading.Thread(target=ask) for _ in range(4)]
    try:
        [t.start() for t in threads]
        [t.join() for t in threads]
        assert len(ids) == 4 and all(ids) and len(set(ids)) == 4
    finally:
        tracing._tracer, tracing._provider = False, None  # leave tracing off for the rest of the session


def _turn(message, history, monkeypatch, run=None):
    """One chat turn with the follow-up rewrite, pipeline and rendering stubbed out."""
    monkeypatch.setattr(chat, "standalone", lambda message, history, today, callbacks: (
        "What was Acme's gross margin in Q2 FY2026?" if message.startswith("and") else None, {}))
    monkeypatch.setattr(chat, "run", run or (lambda question, **kw: {
        "answer": "CLI brief", "companies": [], "claims": [], "unavailable": [], "tokens": {}}))
    monkeypatch.setattr(chat, "render", lambda output, today, question, rewritten: (
        f"**Researched as:** {question}\n\n- Gross margin was 40%. [[1]](<https://www.sec.gov/x>)", "panel"))
    return chat.research(message, history, date(2026, 10, 5), False, lambda stage, detail: None, "ui-t1", "ana")


def test_a_chat_turn_is_traced_as_the_analyst_saw_it(rec, monkeypatch):
    reply = _turn("and gross margin?", ["Analyst: What was Acme's revenue in Q2 FY2026?"], monkeypatch)
    root, followup = rec.one("invoke_agent agent"), rec.one("followup")
    assert root.attributes["input.value"] == "and gross margin?"
    assert root.attributes["output.value"] == reply.content  # the chat's rendering, not the CLI brief
    assert root.attributes["session.id"] == "ui-t1" and root.attributes["user.id"] == "ana"
    assert list(root.attributes["langfuse.trace.tags"]) == ["agent", "chat"]
    assert followup.parent.span_id == root.context.span_id
    assert followup.attributes["output.value"] == "What was Acme's gross margin in Q2 FY2026?"
    assert reply.trace_id == format(root.context.trace_id, "032x") and reply.panel == "panel"
    assert reply.turn.startswith("Analyst: and gross margin?\nResearched as: What was Acme's gross margin")


def test_small_talk_and_failures_record_what_the_chat_said(rec, monkeypatch):
    reply = _turn("thanks!", ["Analyst: What was Acme's revenue?"], monkeypatch)
    assert reply.content == chat.HELP and reply.turn is None and reply.panel is None

    def timeout(question, **kw):
        raise TimeoutError("model timed out")

    with pytest.raises(TimeoutError):
        _turn("What was Acme's revenue?", [], monkeypatch, run=timeout)
    small_talk, failed = rec.spans("invoke_agent agent")
    assert small_talk.attributes["output.value"] == chat.HELP
    assert failed.attributes["output.value"] == chat.failure("TimeoutError: model timed out")
    assert not failed.status.is_ok


def test_a_long_reply_is_kept_whole(rec):
    with tracing.trace_question("agent", "q", "ui-t1", user="ana", tags=["chat"]) as trace:
        trace.reply("x" * 5000)
    assert rec.one("invoke_agent agent").attributes["output.value"] == "x" * 5000


def test_feedback_is_one_score_per_answer_that_a_second_click_replaces(rec):
    tracing.feedback("abc123", True)
    tracing.feedback("abc123", False)
    up, down = [kw["json"] for method, path, kw in rec.api_calls if path == "/api/public/scores"]
    assert up["id"] == down["id"] and up["traceId"] == "abc123"
    assert (up["name"], up["dataType"], up["value"], down["value"]) == ("user_feedback", "BOOLEAN", 1.0, 0.0)


def test_tracing_off_is_a_no_op(monkeypatch, tmp_path):
    monkeypatch.setenv("TRACING", "off")
    tracing._tracer, tracing._provider = None, None  # re-read the environment
    try:
        with tracing.trace_question("agent", "q", "run1", ROW) as trace:
            assert trace.trace_id is None and trace.callbacks == []
            with tracing.step("plan") as span:
                assert span is None
            asyncio.run(Web(tmp_path, live=False).call("search", query="x"))
            trace.finish({"answer": "a"})
        tracing.attach_scores(None, {})
        tracing.flush()
    finally:
        tracing._tracer, tracing._provider = False, None  # leave tracing off for the rest of the session


def test_no_key_material_in_spans(rec, monkeypatch, tmp_path):
    secret = "tvly-" + "x" * 24
    monkeypatch.setenv("TAVILY_API_KEY", secret)
    with tracing.trace_question("agent", "q", "run1", ROW) as trace:
        with tracing.step("web_evidence"):
            asyncio.run(Web(tmp_path, live=False).call("search", query="x"))
        _model().invoke("q", config={"callbacks": trace.callbacks})
    blob = json.dumps([dict(s.attributes) for s in rec.spans()], default=str)
    assert secret not in blob
