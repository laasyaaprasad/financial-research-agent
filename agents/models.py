"""Shared small Nebius model for extraction and planning; no agent loop."""

from __future__ import annotations

from typing import TypeVar

from langchain_nebius import ChatNebius
from pydantic import BaseModel

SMALL_MODEL = "Qwen/Qwen3.8-27B"
T = TypeVar("T", bound=BaseModel)


def structured(schema: type[T], system: str, user: str, *, model: str = SMALL_MODEL,
               callbacks: list | None = None) -> tuple[T, dict[str, int]]:
    client = ChatNebius(model=model, temperature=0, max_tokens=6500,
                        reasoning_effort="none", timeout=90, max_retries=1)
    # Installed langchain-nebius initializes the completion resource but leaves
    # langchain-openai's root_client unset. Native schema parsing needs that root.
    if client.root_client is None:
        client.root_client = client.client._client
    response = client.with_structured_output(schema, method="json_schema", strict=True, include_raw=True).invoke(
        [("system", system + "\nReturn only the requested JSON schema, no prose."),
         ("human", user)], config={"callbacks": callbacks or []})
    if response.get("parsing_error") or response.get("parsed") is None:
        error = response.get("parsing_error")
        raise ValueError(f"Nebius structured output failed: {str(error)[:900] if error else 'no structured response'}")
    usage = response["raw"].usage_metadata or {}
    return response["parsed"], {"input": usage.get("input_tokens", 0), "output": usage.get("output_tokens", 0)}
