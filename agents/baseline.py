"""Baseline: the starter agent's configuration, reproduced without the CLI or streaming.

Same model, system prompt and TavilySearch defaults as the provided starter_agent.py
(which can't be committed). Returns the answer plus everything the eval needs:
tool calls, tool results, token usage, estimated Tavily credits and latency.
"""

from __future__ import annotations

import json
import time
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_nebius import ChatNebius
from langchain_tavily import TavilySearch

load_dotenv()

MODEL = "moonshotai/Kimi-K2.6"

SYSTEM_PROMPT = """You are a concise research assistant.
Use Tavily search when you need current or factual web information.
Answer the user's question directly and include source URLs when available.
"""

# Credits per Tavily search call by depth (docs.tavily.com/documentation/api-credits).
# langchain-tavily can't send X-Project-ID or request usage without changing the tool's
# output, so baseline credits are counted from the calls the agent makes.
CREDITS_BY_DEPTH = {"basic": 1, "fast": 1, "ultra-fast": 1, "advanced": 2}


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


def build_agent(model: str = MODEL):
    return create_agent(
        model=ChatNebius(model=model),
        tools=[TavilySearch()],
        system_prompt=SYSTEM_PROMPT,
    )


def run(question: str, model: str = MODEL, callbacks: list | None = None) -> dict[str, Any]:
    agent = build_agent(model)
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

    credits = sum(
        CREDITS_BY_DEPTH.get(c["args"].get("search_depth") or "basic", 1)
        for c in tool_calls
        if c["name"] == "tavily_search"
    )
    return {
        "answer": answer,
        "tool_calls": tool_calls,
        "tool_results": tool_results,
        "tokens": tokens,
        "tavily_credits": credits,
        "latency_s": round(latency, 2),
        "model": model,
    }
