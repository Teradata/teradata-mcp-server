Here is a clear and reusable documentation-style guide that explains how to integrate a Python function with multiple arguments into your **MPC server**, including both the `async` tool-facing function and the backend handler function.

---

## 📚 How to Integrate a Python Function into the MPC Server

This guide shows how to register a Python function named `my_function`—with multiple arguments—into your MPC server using the `@mcp.tool` decorator and the `execute_db_tool` utility.

### 🎯 Goal

Integrate `my_function` into the MPC toolchain with two layers:

1. **Frontend wrapper** (MPC-exposed async function): `fs_my_function`
2. **Backend logic handler** (actual logic): `handle_fs_my_function`

---

### 🧩 Step 1: Define the Backend Handler

This is the core function that performs the actual logic. It receives a database connection and the necessary arguments.

```python
# handler_function.py

def handle_fs_my_function(
    conn: TeradataConnection, 
    arg1: str, 
    arg2: int, 
    flag: bool = False, 
    *args, 
    **kwargs
):
    logger.debug(f"Tool: handle_fs_my_function: Args: arg1={arg1}, arg2={arg2}, flag={flag}")

    try:
        # Replace this with real business logic
        result = my_function(arg1=arg1, arg2=arg2, flag=flag)

        metadata = {
            "tool_name": "fs_my_function",
            "arg1": arg1,
            "arg2": arg2,
            "flag": flag,
        }
        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_fs_my_function: {e}")
        return create_response({"error": str(e)}, {"tool_name": "fs_my_function"})
```

---

### 🖥️ Step 2: Create the Async Tool Function

This is what MPC exposes and calls. It uses `@mcp.tool` to register metadata and relies on `execute_db_tool` to call the backend handler.

```python
# mpc_tools.py

from pydantic import Field
from typing import Optional
from mcp import tool  # adjust this import based on your actual framework

@mcp.tool(
    description="Run `my_function` with required arguments `arg1`, `arg2`, and optional `flag`."
)
async def fs_my_function(
    arg1: str = Field(..., description="First argument (string)."),
    arg2: int = Field(..., description="Second argument (integer)."),
    flag: Optional[bool] = Field(False, description="Optional flag (boolean)."),
) -> ResponseType:
    return execute_db_tool(
        _tdconn,
        td.handle_fs_my_function,
        arg1=arg1,
        arg2=arg2,
        flag=flag,
    )
```

---

### 🛠️ Step 3: Ensure Your Utility Function is Available

Your `execute_db_tool` function is already defined like this:

```python
def execute_db_tool(conn, tool, *args, **kwargs):
    try:
        return format_text_response(tool(conn, *args, **kwargs))
    except Exception as e:
        logger.error(f"Error sampling object: {e}")
        return format_error_response(str(e))
```

No change is needed here.

---

### ✅ Example `my_function` (for reference)

```python
def my_function(arg1: str, arg2: int, flag: bool = False) -> str:
    return f"arg1: {arg1}, arg2: {arg2}, flag: {flag}"
```

---

### 🧪 Optional: Testing via Direct Call

```python
# Emulate how MPC would call the tool
async def test_tool():
    result = await fs_my_function(arg1="test", arg2=123, flag=True)
    print(result)
```

---

### 🔚 Summary

| Component                   | Purpose                                                                       |
| --------------------------- | ----------------------------------------------------------------------------- |
| `fs_my_function`        | Async MPC tool function. Handles inputs, metadata, and passes to the backend. |
| `handle_fs_my_function` | Backend business logic handler, receives parsed arguments and DB connection.  |
| `execute_db_tool`           | Utility wrapper for error handling and formatting.                            |

Let me know if you'd like this as a template or reusable decorator for many functions. 