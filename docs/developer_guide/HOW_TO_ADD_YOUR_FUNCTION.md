# Adding New Modules

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

Let me know if you'd like this as a template or reusable decorator for many functions. 
