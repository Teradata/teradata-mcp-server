# ┌────────────── Build stage ──────────────┐
FROM python:3.13-slim AS builder
WORKDIR /app

COPY pyproject.toml uv.lock* /app/
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc && \
    pip install --upgrade pip && \
    pip install uv mcpo && \
    uv sync && \
    uv build && \
    pip install . && \
    apt-get purge -y build-essential gcc && \
    rm -rf /var/lib/apt/lists/*

COPY . /app
# └──────────── End build stage ────────────┘

# ┌───────────── Runtime stage ─────────────┐
FROM python:3.13-slim
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

RUN useradd --no-log-init --create-home appuser && chown -R appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1
ENV SSE=True
ENV SSE_HOST=127.0.0.1
ENV SSE_PORT=8001
CMD ["uv", "run", "teradata-mcp-server"]
# └──────────── End runtime stage ──────────┘
