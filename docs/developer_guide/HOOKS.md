# Server Hooks

> **📍 Navigation:** [Documentation Home](../README.md) | [Server Guide](../README.md#-server-guide) | [Getting started](../server_guide/GETTING_STARTED.md) | [Architecture](../server_guide/ARCHITECTURE.md) | [Installation](../server_guide/INSTALLATION.md) | [Configuration](../server_guide/CONFIGURATION.md) | [Security](../server_guide/SECURITY.md) | [Customization](../server_guide/CUSTOMIZING.md) | [Client Guide](../client_guide/CLIENT_GUIDE.md)

Server hooks let you inject custom logic around every tool invocation — without modifying the server source or adding a wrapper layer. You provide a plain Python module; the server loads it at startup and calls your functions at the right moments.

---

## 📚 Overview

Three hook points are called in sequence for every tool call:

| Hook | When it fires | Signature |
|---|---|---|
| `on_tool_call` | Before the handler runs | `(ctx: ToolCallContext) -> None` |
| `on_tool_result` | After a successful result | `(ctx: ToolCallContext, result: object) -> None` |
| `on_tool_error` | When the handler raises | `(ctx: ToolCallContext, error: Exception) -> None` |

All hooks are **synchronous** and run inside the same worker thread as the tool. A hook that raises an exception is caught and logged — it never interrupts the tool call itself or the server.

---

## 🧩 Step 1: Create your hooks module

Write a plain Python file that imports `ServerHooks` and `ToolCallContext`, defines your hook functions, and exposes a `get_hooks()` factory.

```python
# my_hooks.py

from teradata_mcp_server.hooks import ServerHooks, ToolCallContext


def _on_tool_call(ctx: ToolCallContext) -> None:
    print(f"[CALL]   {ctx.tool_name}  args={ctx.kwargs}")


def _on_tool_result(ctx: ToolCallContext, result: object) -> None:
    print(f"[RESULT] {ctx.tool_name}")


def _on_tool_error(ctx: ToolCallContext, error: Exception) -> None:
    print(f"[ERROR]  {ctx.tool_name}: {error}")


def get_hooks() -> ServerHooks:
    return ServerHooks(
        on_tool_call=_on_tool_call,
        on_tool_result=_on_tool_result,
        on_tool_error=_on_tool_error,
    )
```

You only need to supply the hooks you use. Omit any field (or pass `None`) to skip that hook point:

```python
def get_hooks() -> ServerHooks:
    # Only intercept errors — ignore call and result events
    return ServerHooks(on_tool_error=_on_tool_error)
```

---

## 📋 ToolCallContext reference

Every hook receives a `ToolCallContext` snapshot of the in-flight request:

| Field | Type | Description |
|---|---|---|
| `tool_name` | `str` | MCP tool name, e.g. `base_tableList` |
| `kwargs` | `dict` | Keyword arguments passed to the tool (internal params `conn`, `tool_name` already removed) |
| `request_context` | `object` | `RequestContext` from the middleware; carries `request_id`, headers, session info |
| `engine` | `object` | SQLAlchemy `Engine` for this request |
| `profile_name` | `str \| None` | Active profile, e.g. `dba` |
| `db_user` | `str \| None` | Teradata database user for this session |

Access `request_context.request_id` to correlate `on_tool_call` and `on_tool_result` / `on_tool_error` events in concurrent scenarios:

```python
_in_flight: dict[str, float] = {}

def _on_tool_call(ctx: ToolCallContext) -> None:
    key = getattr(ctx.request_context, "request_id", None) or ctx.tool_name
    _in_flight[key] = time.perf_counter()

def _on_tool_result(ctx: ToolCallContext, result: object) -> None:
    key = getattr(ctx.request_context, "request_id", None) or ctx.tool_name
    elapsed = time.perf_counter() - _in_flight.pop(key, time.perf_counter())
    print(f"{ctx.tool_name} completed in {elapsed:.3f}s")
```

---

## 🖥️ Step 2: Register the hooks module

Pass the path to your file via the `--hooks_module` CLI argument or the `HOOKS_MODULE` environment variable.

**CLI:**
```bash
uv run teradata-mcp-server \
    --database_uri "teradata://user:pass@host/db" \
    --hooks_module /path/to/my_hooks.py
```

**Environment variable:**
```bash
export HOOKS_MODULE=/path/to/my_hooks.py
uv run teradata-mcp-server --database_uri "teradata://user:pass@host/db"
```

**Claude Desktop `claude_desktop_config.json`:**
```json
{
  "mcpServers": {
    "teradata": {
      "command": "uvx",
      "args": ["teradata-mcp-server", "--hooks_module", "/path/to/my_hooks.py"],
      "env": {
        "DATABASE_URI": "teradata://user:pass@host/db"
      }
    }
  }
}
```

The value can be either:
- A file path ending in `.py` — loaded directly from disk
- A dotted Python import name (e.g. `my_package.hooks`) — resolved via the normal import machinery

If the module cannot be loaded, a warning is logged and the server starts normally with all hooks disabled. A misconfigured hooks module never prevents the server from starting.

---

## 🛠️ What the server does for you

- Calls `get_hooks()` once at startup and caches the result.
- Fires `on_tool_call` before the handler executes.
- Fires `on_tool_result` with the raw handler result, before it is formatted for MCP.
- Fires `on_tool_error` when the handler raises, before the error is formatted for MCP.
- Catches any exception your hook raises, logs it as a warning, and continues execution.
- Passes the same `ToolCallContext` instance to all three hooks for the same request, so you can safely attach state to it.

---

## 🔁 Worked example

The repository ships a complete reference implementation — a performance monitor that times every tool call and writes one log line per invocation:

```
2026-05-04 10:23:14 | base_tableList          |   0.234s | OK
2026-05-04 10:23:15 | base_readQuery          |   1.842s | OK
2026-05-04 10:23:16 | base_columnDescription  |   0.031s | ERROR: connection timeout
```

See [`examples/server-customisation/server-hooks/perf_monitor_hooks.py`](../../examples/server-customisation/server-hooks/perf_monitor_hooks.py).

Run it with:
```bash
uv run teradata-mcp-server \
    --database_uri "teradata://user:pass@host/db" \
    --hooks_module examples/server-customisation/server-hooks/perf_monitor_hooks.py
```

---

## 💡 Use-case ideas

| Use case | Hooks used |
|---|---|
| Performance monitoring | `on_tool_call`, `on_tool_result`, `on_tool_error` |
| Audit logging (who called what) | `on_tool_call` |
| Request rate limiting or quota enforcement | `on_tool_call` |
| Alerting on specific tool errors | `on_tool_error` |
| Caching / memoisation of expensive tools | `on_tool_call`, `on_tool_result` |
| Telemetry / tracing (OpenTelemetry spans) | `on_tool_call`, `on_tool_result`, `on_tool_error` |

---

## 🔚 Summary

| Component | Purpose |
|---|---|
| `ServerHooks` dataclass | Declares the three optional hook callables |
| `ToolCallContext` dataclass | Per-request snapshot passed to every hook |
| `get_hooks()` factory | Entry point the server calls once at startup |
| `--hooks_module` / `HOOKS_MODULE` | How to tell the server which module to load |
| Error isolation | Hook exceptions are caught and logged; they never break tool execution |
