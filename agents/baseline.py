"""Baseline: the starter agent's configuration, reproduced without the CLI or streaming.

Same system prompt, TavilySearch defaults and LangChain agent loop as the provided
starter_agent.py (which can't be committed). Two configurations are evaluated: the starter
exactly as shipped (its default model, Kimi K2.6) and the same design on the new agent's model,
which isolates what the architecture contributes. Returns the answer plus everything the eval needs.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_nebius import ChatNebius
from langchain_tavily import TavilySearch
from pydantic import Field

from agents.llm import AGENT_MODEL

load_dotenv()

MODEL = AGENT_MODEL                       # same-model baseline: isolates the architecture
STARTER_MODEL = "moonshotai/Kimi-K2.6"     # the starter's default model, i.e. exactly as shipped

SYSTEM_PROMPT = """You are a concise research assistant.
Use Tavily search when you need current or factual web information.
Answer the user's question directly and include source URLs when available.
"""

# Credits per Tavily search call by depth (docs.tavily.com/documentation/api-credits).
# langchain-tavily can't send X-Project-ID or request usage without changing the tool's
# output, so baseline credits are counted from the searches that reached Tavily.
CREDITS_BY_DEPTH = {"basic": 1, "fast": 1, "ultra-fast": 1, "advanced": 2}


class CachedTavilySearch(TavilySearch):
    """The starter's TavilySearch tool (same name, description and arguments the model sees), with a
    response cache: a resumed or repeated run replays identical searches instead of paying again."""
    cache_dir: Path | None = None
    live_depths: list[str] = Field(default_factory=list)  # search depth of each successful call to Tavily

    def _run(self, query: str, run_manager=None, **kwargs: Any) -> dict[str, Any]:
        key = hashlib.sha256(json.dumps([query, kwargs], sort_keys=True, default=str).encode()).hexdigest()
        path = self.cache_dir / f"{key}.json" if self.cache_dir else None
        if path and path.exists():
            return json.loads(path.read_text())
        result = super()._run(query, run_manager=run_manager, **kwargs)
        if "error" not in result:  # failed calls (e.g. a usage limit) are neither cached nor billed
            self.live_depths.append(kwargs.get("search_depth") or "basic")
            if path:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(f".{os.getpid()}.{id(self)}.tmp")
                tmp.write_text(json.dumps(result, default=str))
                os.replace(tmp, path)
        return result


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            b if isinstance(b, str) else b.get("text", "")
            for b in content
            if isinstance(b, str) or (isinstance(b, dict) and b.get("type") == "text")
        )
    return ""


def build_agent(model: str = MODEL, search: TavilySearch | None = None):
    return create_agent(
        model=ChatNebius(model=model),
        tools=[search or TavilySearch()],
        system_prompt=SYSTEM_PROMPT,
    )


def run(question: str, model: str = MODEL, callbacks: list | None = None,
        cache_dir: Path | str | None = None) -> dict[str, Any]:
    search = CachedTavilySearch(cache_dir=Path(cache_dir) if cache_dir else None)
    agent = build_agent(model, search)
    start = time.perf_counter()
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"callbacks": callbacks or []},
    )
    latency = time.perf_counter() - start

    tool_calls, tool_results = [], []
    tokens = {"input": 0, "output": 0}
    answer = ""
    for msg in result["messages"]:
        if msg.type == "ai":
            usage = getattr(msg, "usage_metadata", None) or {}
            tokens["input"] += usage.get("input_tokens", 0)
            tokens["output"] += usage.get("output_tokens", 0)
            for call in msg.tool_calls or []:
                tool_calls.append({"name": call["name"], "args": call["args"]})
            if not msg.tool_calls:
                answer = _text(msg.content)
        elif msg.type == "tool":
            try:
                payload = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
            except json.JSONDecodeError:
                payload = {"raw": _text(msg.content)}
            tool_results.append(payload)

    credits = sum(CREDITS_BY_DEPTH.get(depth, 1) for depth in search.live_depths)
    return {
        "answer": answer,
        "tool_calls": tool_calls,
        "tool_results": tool_results,
        "tokens": tokens,
        "tavily_credits": credits,
        "latency_s": round(latency, 2),
        "model": model,
    }
