# Adding New Modules

> **📍 Navigation:** [Documentation Home](../README.md) | [Server Guide](../README.md#-server-guide) | [Getting started](../server_guide/GETTING_STARTED.md) | [Architecture](../server_guide/ARCHITECTURE.md) | [Installation](../server_guide/INSTALLATION.md) | [Configuration](../server_guide/CONFIGURATION.md) | [Security](../server_guide/SECURITY.md) | [Customization](../server_guide/CUSTOMIZING.md) | [Client Guide](../client_guide/CLIENT_GUIDE.md)

Here is a clear and reusable documentation-style guide that explains how to add a new tool implemented in Python to the Teradata MCP server. The design cleanly separates the MCP protocol from your Teradata‑specific logic: you implement a plain Python handler; the server auto‑registers it and wires MCP concerns (validation, context, query band, errors) for you.

---

## 📚 How to Add a New Tool

You add a new handler function named `handle_<toolName>` inside a tools module (e.g., `src/teradata_mcp_server/tools/base/base_tools.py`). The server scans modules according to `profiles.yml`, wraps your handler with an MCP adapter, and registers it automatically.

### 🎯 Goal

Function naming convention is describes [here.](DEVELOPER_GUIDE.md#toolpromptresource-naming-convention)

Two layers at runtime:
1. Your backend handler: `handle_fs_myFunctionName(conn: Connection, ...)` (pure Python, protocol‑agnostic)
2. The server’s auto‑generated MCP wrapper: exposes your handler to MCP clients (built automatically)

---

### 🧩 Step 1: Define the Backend Handler (pure Python)

This is the core function that performs the actual logic. It receives a database connection and the necessary arguments. Prefer typing the first parameter as `sqlalchemy.engine.Connection` to use the SQLAlchemy path.

```python
# handler_function.py

def handle_fs_myFunctionName(
    conn: Connection, 
    arg1: str, 
    arg2: int, 
    flag: bool = False, 
    *args, 
    **kwargs
):
    """
    <description of what the tool is for, this is critical for the LLM to understand when to use the tool>

    Arguments:
      conn   - SQLAlchemy Connection
      arg1 - arg1 to analyze
      arg2 - arg2 to analyze
      flag - flag to analyze
      *args  - Positional bind parameters
      **kwargs - Named bind parameters

    Returns:
      Any: result to be formatted by the server (string/JSON/rows, etc.)
    """
    logger.debug(f"Tool: handle_fs_my_function: Args: arg1={arg1}, arg2={arg2}, flag={flag}")

    try:
        # Replace this with real business logic
        result = my_function(arg1=arg1, arg2=arg2, flag=flag)

        metadata = {
            "tool_name": "fs_myFunctionName",
            "arg1": arg1,
            "arg2": arg2,
            "flag": flag,
        }
        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_fs_myFunctionName: {e}")
        return create_response({"error": str(e)}, {"tool_name": "fs_myFunctionName"})
```

---

### 🖥️ Step 2: Enable the tool in a profile

Add your tool name to the proper profile in `profiles.yml` so the server will register it. The pattern must match the tool name (without the `handle_` prefix). Example that enables the module while disabling a single tool:

```
fs:
  allmodule: True
  tool:
    fs_myFunctionName: True   # or False to hide
  prompt:
    fs_myPromptName: True
```


---

### 🛠️ What the server does for you

You do not need to write a wrapper or call decorators. At startup, the server:
- Loads modules per `profiles.yml`, finds functions named `handle_*`
- Builds an MCP wrapper internally that:
  - Injects a DB connection (`Connection`) as `conn`
  - Optionally injects `fs_config` if your handler declares it
  - Removes internal params (`conn`, `tool_name`, `fs_config`) from the MCP signature
  - Injects a universal `get_all` parameter (see [Row caps](#row-caps) below) unless the tool opts out
  - Calls the internal `execute_db_tool` which handles:
    - QueryBand (using request context)
    - Error handling + response formatting
    - Reconnect logic if needed

Therefore, handlers should be protocol‑agnostic and not import MCP.

---

### Row caps

Tool result sets are capped before they reach the LLM (defaults: 1000 rows, 50000 ceiling — configurable via `DEFAULT_ROW_LIMIT` / `MAX_ROW_LIMIT`). For most tools you do not need to do anything: handlers that go through `handle_base_readQuery` are capped automatically by `SELECT TOP N+1` injection, and a wrapper-level fallback trims oversized list results from any other handler.

**Customize the cap from YAML.** In your `*_objects.yml`, alongside `parameters:` / `sql:`, set any of:

```yaml
my_tool_listThings:
  type: tool
  description: "..."
  row_limit: 200              # default cap, overrides DEFAULT_ROW_LIMIT
  max_row_limit: 5000         # ceiling raised by get_all=true, overrides MAX_ROW_LIMIT
  bypass_row_cap: true        # never cap; do not inject get_all
  narrowing_parameters:       # surfaced in the truncation hint
    - user_name
    - no_days
```

Use `bypass_row_cap: true` on tools that already return a single row, return non-list payloads (e.g. DDL, plans, charts), or have their own paging contract. The `narrowing_parameters` list is shown to the client when truncation fires, so the LLM knows which inputs would shrink the result set.

**Reserved kwargs.** When the cap is active the wrapper passes `_row_limit`, `_hard_ceiling`, `_get_all_used`, and `_narrowing_params` into your handler. If you call `handle_base_readQuery` you can ignore them — it pops them itself. If you implement your own SQL execution path, pop them off `kwargs` before binding parameters and either honour the cap yourself or rely on the wrapper-level trim. Do **not** declare a parameter named `get_all` — the wrapper owns that name.

When truncation fires, attach `metadata["truncation"] = build_truncation_metadata(...)` (from `teradata_mcp_server.tools.utils.row_cap`) so the client sees a uniform shape across tools.

---

### ✅ Example `my_function` (helper used by your handler)

```python
def myFunction(arg1: str, arg2: int, flag: bool = False) -> str:
    return f"arg1: {arg1}, arg2: {arg2}, flag: {flag}"
```

---

### 🧪 Optional: Testing via the server

Use MCP Inspector or your client (Claude Desktop) to call the tool once it’s enabled in the profile.

---

### 🔚 Summary

| Component                   | Purpose                                                                       |
| --------------------------- | ----------------------------------------------------------------------------- |
| `handle_fs_myFunction`      | Backend business logic handler, receives `conn` and arguments.               |
| MCP wrapper (auto)          | Auto-generated MCP wrapper around your handler (built at startup).           |
| `execute_db_tool` (internal)  | Central adapter: sets QueryBand, handles errors/formatting, reconnects.    |

Let me know if you'd like this as a template or reusable decorator for many functions. 
