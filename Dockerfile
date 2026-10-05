# The chat UI and the agent in one image. Secrets come from the environment at run time, never from the image.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --group ui --no-install-project

COPY agents ./agents
COPY ui ./ui
# The SEC and Tavily caches live in a volume at /app/results; Chainlit writes its files under ui/ at startup.
RUN useradd --create-home app && mkdir -p results && chown -R app results ui
USER app
EXPOSE 8000
CMD ["python", "-m", "ui", "--host", "0.0.0.0", "--port", "8000", "--headless"]
