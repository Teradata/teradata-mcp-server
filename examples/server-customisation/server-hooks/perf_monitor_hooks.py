"""
Tool Performance Monitor — example hook for the Teradata MCP Server.

Tracks execution time for every tool call and writes a log line for each:

    2026-05-04 10:23:14 | base_tableList          |   0.234s | OK
    2026-05-04 10:23:15 | base_readQuery          |   1.842s | OK
    2026-05-04 10:23:16 | base_columnDescription  |   0.031s | ERROR: ...

Usage:
    uv run teradata-mcp-server \
        --database_uri "teradata://user:pass@host/db" \
        --hooks_module perf_monitor_hooks.py \
        --logging_level INFO

    # Optional: set log file path (default: tool_perf.log in the working directory)
    export PERF_LOG_FILE="/var/log/teradata_mcp/tool_perf.log"
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime

from teradata_mcp_server.hooks import ServerHooks, ToolCallContext

_log = logging.getLogger("perf_monitor_hooks")

_LOG_FILE = os.getenv("PERF_LOG_FILE", "tool_perf.log")

# Shared state between on_tool_call and on_tool_result / on_tool_error.
# Keyed by request_id so concurrent requests don't collide.
_in_flight: dict[str, float] = {}


def _key(ctx: ToolCallContext) -> str:
    """Unique key per request — falls back to tool name if no request_id."""
    return getattr(ctx.request_context, "request_id", None) or ctx.tool_name


def _on_tool_call(ctx: ToolCallContext) -> None:
    _log.info("Performance monitor Hook called ..")
    _in_flight[_key(ctx)] = time.perf_counter()


def _on_tool_result(ctx: ToolCallContext, result: object) -> None:
    elapsed = time.perf_counter() - _in_flight.pop(_key(ctx), time.perf_counter())
    _write(ctx.tool_name, elapsed, "OK")


def _on_tool_error(ctx: ToolCallContext, error: Exception) -> None:
    elapsed = time.perf_counter() - _in_flight.pop(_key(ctx), time.perf_counter())
    _write(ctx.tool_name, elapsed, f"ERROR: {type(error).__name__}: {error}")


def _write(tool_name: str, elapsed: float, status: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} | {tool_name:<30} | {elapsed:>7.3f}s | {status}\n"
    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as exc:
        _log.warning("perf_monitor_hooks: failed to write to %s: %s", _LOG_FILE, exc)


def get_hooks() -> ServerHooks:
    return ServerHooks(
        on_tool_call=_on_tool_call,
        on_tool_result=_on_tool_result,
        on_tool_error=_on_tool_error,
    )