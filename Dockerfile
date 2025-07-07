# ┌────────────── Build stage ──────────────┐
FROM --platform=linux/amd64 python:3.13-slim AS builder
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

# Copy everything *except* src (excluded via .dockerignore)
COPY . /app

# Now copy src separately — this layer will be re-run only if src changes
COPY ./src /app/src
# └──────────── End build stage ────────────┘

# ┌───────────── Runtime stage ─────────────┐
FROM --platform=linux/amd64 python:3.13-slim
WORKDIR /app

# Create the user early
RUN useradd --no-log-init --create-home appuser

# Copy all files with correct ownership immediately
COPY --from=builder --chown=appuser:appuser /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder --chown=appuser:appuser /usr/local/bin /usr/local/bin
COPY --from=builder --chown=appuser:appuser /app /app
RUN mkdir /app/logs && chown appuser:appuser /app/logs

USER appuser

RUN chmod -R u+w /app/src


ENV PYTHONUNBUFFERED=1
ENV MCP_TRANSPORT=streamable-http
ENV MCP_PATH=/mcp/
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8001
CMD ["uv", "run", "teradata-mcp-server"]
# └──────────── End runtime stage ──────────┘
