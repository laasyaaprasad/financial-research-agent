"""Nebius model access. One cheap model runs every agent step; structured output via tool calling."""

from __future__ import annotations

from typing import TypeVar

from dotenv import load_dotenv
from langchain_nebius import ChatNebius
from pydantic import BaseModel

load_dotenv()

AGENT_MODEL = "deepseek-ai/DeepSeek-V4.1-Flash"
T = TypeVar("T", bound=BaseModel)


def structured(schema: type[T], system: str, user: str, *, model: str = AGENT_MODEL, reasoning: str = "low",
               callbacks: list | None = None, retries: int = 2) -> tuple[T, dict[str, int]]:
    """Call the model and parse its answer into `schema`. Returns (result, token usage).

    `reasoning` sets the model's thinking budget ("none", "low", "medium"): simple extraction
    needs none, while writing the answer benefits from more.
    """
    llm = ChatNebius(model=model, temperature=0, timeout=240, max_retries=2, reasoning_effort=reasoning)
    runnable = llm.with_structured_output(schema, method="function_calling", include_raw=True)
    tokens = {"input": 0, "output": 0}
    error = None
    for _ in range(retries + 1):
        response = runnable.invoke([("system", system), ("human", user)], config={"callbacks": callbacks or []})
        usage = getattr(response["raw"], "usage_metadata", None) or {}
        tokens["input"] += usage.get("input_tokens", 0)
        tokens["output"] += usage.get("output_tokens", 0)
        if response.get("parsed") is not None:
            return response["parsed"], tokens
        error = response.get("parsing_error")
    raise ValueError(f"{schema.__name__}: model did not return valid structured output ({error})")
