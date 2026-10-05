"""LLM prices, used for the cost recorded on model-call spans."""

# USD per 1M tokens (input, output) on Nebius Token Factory, from the account's model list (2026-10-04).
PRICES = {
    "moonshotai/Kimi-K2.6": (0.95, 4.00),
    "deepseek-ai/DeepSeek-V4.1-Flash": (0.30, 1.20),
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> dict[str, float]:
    """Cost of one call; unknown models cost 0 rather than a guess."""
    p_in, p_out = PRICES.get(model, (0.0, 0.0))
    i, o = input_tokens * p_in / 1e6, output_tokens * p_out / 1e6
    return {"input": i, "output": o, "total": i + o}
