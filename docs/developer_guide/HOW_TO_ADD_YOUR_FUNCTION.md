# Adding New Modules

Here is a clear and reusable documentation-style guide that explains how to integrate a Python function with multiple arguments into your **MPC server**, including both the `async` tool-facing function and the backend handler function.

---

## 📚 How to Integrate a Python Function into the MPC Server

This guide shows how to register a Python function named `myFunctionName`—with multiple arguments—into your MPC server using the `@mcp.tool` decorator and the `execute_db_tool` utility.

### 🎯 Goal

Function naming convention is describes [here.](DEVELOPER_GUIDE.md#toolpromptresource-naming-convention)

Integrate `myFunctionName` into the fs module of the MPC toolchain with two layers:

1. **Frontend wrapper** will be created by parsing the handle fuction
2. **Backend logic handler** (actual logic): `handle_fs_myFunctionName`

---

### 🧩 Step 1: Define the Backend Handler

This is the core function that performs the actual logic. It receives a database connection and the necessary arguments.

```python
# handler_function.py

def handle_fs_myFunctionName(
    conn: TeradataConnection, 
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
      ResponseType: formatted response with query results + metadata
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

### 🖥️ Step 2: Create the Async Tool Function

This is what MPC exposes and calls. It uses `@mcp.tool` to register metadata and relies on `execute_db_tool` to call the backend handler. The dynamic tool registration process in server.py will automatically decorate your tools starting with handle_ and that have been identified in the config_tools.yml profile.

You will need to add your tools into the config_tools.yaml file in the appropriate profile and module, the allmodule flag turns the entire module on and off, the example below enables the module and turns off the fs_myFunctionName.

```
fs: 
    allmodule: True
    tool:
        fs_myFunctionName : False
    prompt:
        fs_myPromptName: True
```


---

### 🛠️ Step 3: Ensure Your Utility Function is Available

Your `execute_db_tool` function is already defined like this:

```python
def execute_db_tool(tool, *args, **kwargs):
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
def myFunction(arg1: str, arg2: int, flag: bool = False) -> str:
    return f"arg1: {arg1}, arg2: {arg2}, flag: {flag}"
```

---

### 🧪 Optional: Testing via Direct Call

```python
# Emulate how MPC would call the tool
async def test_tool():
    result = await fs_myFunction(arg1="test", arg2=123, flag=True)
    print(result)
```

---

### 🔚 Summary

| Component                   | Purpose                                                                       |
| --------------------------- | ----------------------------------------------------------------------------- |
| `fs_myFunction`             | Async MPC tool function. Handles inputs, metadata, and passes to the backend. |
| `handle_fs_myFunction`      | Backend business logic handler, receives parsed arguments and DB connection.  |
| `execute_db_tool`           | Utility wrapper for error handling and formatting.                            |

Let me know if you'd like this as a template or reusable decorator for many functions. 