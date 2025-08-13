# ┌────────────── Build stage ──────────────┐
FROM --platform=linux/amd64 python:3.13-slim AS builder
WORKDIR /app

# Build arguments for optional modules
ARG ENABLE_FS_MODULE=false
ARG ENABLE_EVS_MODULE=false

# Copy essential files for dependency installation
COPY pyproject.toml uv.lock* README.md /app/

# Install system dependencies and Python dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc && \
    pip install --upgrade pip && \
    pip install uv mcpo && \
    # Build uv sync command with conditional extras \
    UV_EXTRAS="" && \
    if [ "$ENABLE_FS_MODULE" = "true" ]; then UV_EXTRAS="$UV_EXTRAS --extra fs"; fi && \
    if [ "$ENABLE_EVS_MODULE" = "true" ]; then UV_EXTRAS="$UV_EXTRAS --extra evs"; fi && \
    uv sync $UV_EXTRAS

# Copy source code before building
COPY ./src /app/src

# Build and install the package
RUN uv build && \
    pip install . && \
    apt-get purge -y build-essential gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy everything else
COPY . /app
# Remove optional module directories if not enabled
RUN if [ "$ENABLE_FS_MODULE" != "true" ]; then rm -rf /app/src/teradata_mcp_server/tools/fs; fi && \
    if [ "$ENABLE_EVS_MODULE" != "true" ]; then rm -rf /app/src/teradata_mcp_server/tools/evs; fi
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
