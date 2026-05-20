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

### 🏷️ Tool Annotations (automatic)

Every registered tool receives an MCP `ToolAnnotations` object based on its name prefix. These hints tell LLM clients whether a tool is safe to run silently (`readOnlyHint`) or requires a confirmation prompt (`destructiveHint`).

| Prefix | Hint applied |
|--------|-------------|
| `base_`, `dba_`, `sec_`, `rag_`, `qlty_`, `graph_`, `sql_`, `plot_`, `tdvs_` | `readOnlyHint=True, idempotentHint=True` |
| `bar_` | `readOnlyHint=False, destructiveHint=True` |
| `tdml_` | `readOnlyHint=False, idempotentHint=True` |
| `chat_`, `fs_`, unknown prefixes | No annotation (MCP default) |

Per-tool overrides exist for `tdvs_grant_user` and `tdvs_revoke_user` (marked destructive despite the read-only `tdvs_` prefix).

When adding a new tool:
- **Existing prefix** — no action needed; the correct annotation is inherited automatically.
- **New prefix** — add an entry to `_PREFIX_ANNOTATIONS` in `app.py`.
- **Exception within a read-only prefix** (e.g., a future `dba_dropTable`) — add a per-tool entry to `_TOOL_ANNOTATIONS` in `app.py`.

---

### 🛠️ What the server does for you

You do not need to write a wrapper or call decorators. At startup, the server:
- Loads modules per `profiles.yml`, finds functions named `handle_*`
- Builds an MCP wrapper internally that:
  - Injects a DB connection (`Connection`) as `conn`
  - Optionally injects `fs_config` if your handler declares it
  - Removes internal params (`conn`, `tool_name`, `fs_config`) from the MCP signature
  - Calls the internal `execute_db_tool` which handles:
    - QueryBand (using request context)
    - Error handling + response formatting
    - Reconnect logic if needed

Therefore, handlers should be protocol‑agnostic and not import MCP.

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

---

## ➕ Adding a teradataml Analytic Function (`tdml_*`)

The `tdml_*` tools (e.g., `tdml_KMeans`, `tdml_XGBoost`) are registered dynamically from the teradataml library. They do **not** follow the `handle_*` pattern — instead, they are driven by a curated dictionary.

### How it works

1. `tools/constants.py` contains `TD_ANALYTIC_FUNCS`, a `dict[str, str]` mapping each teradataml function name to a curated one-line summary.
2. At startup, `app.py` iterates this dict, queries the live teradataml JSON store for each function's parameter metadata, and generates + registers a `tdml_<FunctionName>` MCP tool automatically.
3. `build_tdml_tool_docstring()` in `tools/utils/__init__.py` assembles the compact description (summary + one line per parameter with Required/Optional and types).

### Steps to add a new function

1. Open `src/teradata_mcp_server/tools/constants.py`.
2. Add one entry to `TD_ANALYTIC_FUNCS`:

```python
TD_ANALYTIC_FUNCS = {
    ...
    "MyNewFunction": "One-sentence description of what this function does.",
}
```

That's it — no other code changes are needed. The server will register `tdml_MyNewFunction` automatically on next startup, provided the function exists in the connected database's teradataml version.

### Notes
- The summary should be one sentence, no longer than ~120 characters.
- If the function is not present in the connected database, it is skipped with a warning — no error.
- The `fs` extra (`uv sync --extra fs`) must be installed for any `tdml_*` tools to register.
