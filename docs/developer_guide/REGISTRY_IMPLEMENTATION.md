# Database Tool Registry - Final Simplified Implementation

## Overview

This document describes the **implementation of the database tool registry** feature for Teradata MCP Server. 
This feature dynamically loads MCP tools defined as database objects (UDFs and Macros) and registered in the appropriate table.

## Architecture Principles

### Key Design Decisions

1. **Explicit tools**: Each tool is instantiated as a MCP Tool and listed by the clients using the 'list_tools()' primitive. Uses the same execution pattern as YAML tools.
2. **Server startup Load**: Registry tools are loaded **once** when the first database connection is established. Planned: an incremental load pattern to detect newly registered tools without restarting the server.
3. **No Profile Filtering**: ALL registry tools are loaded regardless of profile patterns (registry tools override code tools) if a valid database schema for the tool registry is provided.
4. **Database user filtering**: Tools need to be explicitly mapped to the database user of the MCP server (the proxy user in case of AUTH pattern). This allows for tool filtering in case a registry is shared by multiple MCP servers.

## Application flow

```
Server Startup
    ↓
Load code tools from src/teradata_mcp_server/tools/*
    (Profile patterns apply: ^base_*, ^dba_*, etc.)
    ↓
First Database Connection Established
    ↓
Check: Is registry configured in profile?
    ↓ Yes
Query mcp.mcp_list_tools + mcp.mcp_list_toolParams
    ↓
Load ALL registry tools (no profile filtering)
    ↓
Register as FastMCP tools (override if name collision)
    ↓
Done - Tools available for all sessions
```

## Database Schema

### Required Views

The registry exposes two database views in the configured registry database (e.g., `mcp` , as defined in the profile configuration):

**1. `mcp_list_tools`** - Tool-level metadata

**Column Details:**
- `ToolName`: Name of the tool as it will appear in MCP
- `DataBaseName`: Database where the object resides
- `TableName`: Name of the database object (UDF/Macro/Table/View)
- `ToolType`: Type code - `F` (Function/UDF), `M` (Macro), `T` (Table), `V` (View)
- `docstring`: Tool description/documentation
- `Tags`: Optional comma-separated tags for categorization

**2. `mcp.mcp_list_toolParams`** - Tool parameters metadata

**Column Details:**
- `ToolName`: Name of the tool (must match `mcp_list_tools.ToolName`)
- `ParamName`: Name of the parameter
- `ParamType`: Teradata data type code (CV=VARCHAR, I=INTEGER, F=FLOAT, DA=DATE, etc.)
- `ParamLength`: Optional length/precision information
- `ParamPosition`: 1-based position in the parameter list
- `ParamRequired`: `Y` (required) or `N` (optional)
- `ParamComment`: Description of the parameter

### Example Setup

See [examples/registry_setup_example.sql](examples/server-customization/registry_setup.sql) for complete SQL to create tables, views, and example tool registrations.

## Implementation Details

### File Structure

```
src/teradata_mcp_server/
├── app.py                          # Main integration (lines 893-978)
├── tools/
│   └── registry/
│       ├── __init__.py             # Module exports
│       ├── registry_loader.py      # Queries database for tools
│       └── registry_tools.py       # SQL generation helper
```

### Core Components

#### 1. Registry Loader (`registry_loader.py`)

Queries the database views and returns tool definitions:

```python
class RegistryLoader:
    def load_tools(self) -> Dict[str, Any]:
        """Query database and return tool definitions."""
        # Queries mcp.mcp_list_tools and mcp.mcp_list_toolParams
        # Maps Teradata types to Python types
        # Returns dict of tool_name -> tool_definition
```

**Type Mapping**:
- `CV` (CHAR/VARCHAR) → `str`
- `I` (INTEGER) → `int`
- `F` (FLOAT) → `float`
- `DATE` → `str`
- Default → `str`

#### 2. SQL Builder & Type Casting (`registry_tools.py`)

Generates SQL statements with named parameter placeholders and handles type casting:

```python
def build_registry_sql(tool_def: Dict[str, Any]) -> str:
    """Build SQL with named parameter placeholders for safe binding."""
    # For UDFs: SELECT database.function_name(:param1, :param2)
    # For Macros: EXEC database.macro_name(:param1, :param2)
    # Parameters sorted by position, using named placeholders

def cast_parameters(params: Dict[str, Any], tool_def: Dict[str, Any]) -> Dict[str, Any]:
    """Cast parameter values to correct Python types before SQLAlchemy binding."""
    # Ensures integer parameters stay as int, not string
    # Critical for Teradata operations like TOP N
```

**SQL Generation**:
- **UDF**: `SELECT database.function_name(:param1, :param2)`
- **Macro**: `EXEC database.macro_name(:param1, :param2)`
- Parameters sorted by position
- Uses named placeholders (`:param_name`) for safe SQLAlchemy parameter binding
- No value formatting needed - database handles escaping
- Eliminates SQL injection risks

**Type Casting**:
- Parameters received from clients (JSON/HTTP) are often strings
- `cast_parameters()` converts them to correct Python types based on tool definition
- Example: String `'10'` → integer `10` for TOP N parameters
- Essential for Teradata type-sensitive operations
- Handles int, float, str, bool, and None/NULL values

#### 3. Main Integration (`app.py`)

One-time loading on first DB connection:

```python
# Registry configuration from profiles.yml
registry_db = config.get('registry')  # e.g., 'mcp'
registry_tools_loaded = False

def load_registry_tools_once():
    """Load all registry tools once when DB connection is available."""
    nonlocal registry_tools_loaded

    if registry_tools_loaded or not registry_db:
        return

    # Query database for tools
    loader = RegistryLoader(get_tdconn(), registry_db)
    registry_tools = loader.load_tools()

    # Register each tool with FastMCP
    for tool_name, tool_def in registry_tools.items():
        # Build parameters and signature
        # Create executor: build_registry_sql() + handle_base_readQuery
        # Register with mcp.tool()

    registry_tools_loaded = True

# Hook into execute_db_tool to trigger on first DB connection
def execute_db_tool_with_registry(*args, **kwargs):
    tdconn_check = get_tdconn()
    if getattr(tdconn_check, "engine", None) and not registry_tools_loaded:
        load_registry_tools_once()
    return original_execute_db_tool(*args, **kwargs)
```

### Execution Flow

1. **Server Starts**: Registry not loaded yet (`registry_tools_loaded = False`)
2. **First Tool Call**: Any tool that uses `execute_db_tool()` triggers the wrapper
3. **DB Connection Check**: If database engine exists and registry not loaded yet
4. **Load Registry**: Query database views, build tool definitions, register with FastMCP
5. **Flag Set**: `registry_tools_loaded = True` prevents re-loading
6. **Subsequent Calls**: Registry tools available immediately, no re-loading

### Tool Registration

Registry tools are registered using the same pattern as YAML tools, with safe parameter binding:

```python
# Create handler function (like handle_* functions)
def handler(conn, tool_name=None, **kwargs):
    """Registry-defined database tool handler."""
    # Build SQL with named parameter placeholders
    sql = build_registry_sql(tool_def)

    # Extract tool parameters (excluding special params)
    special_params = {'persist', 'tool_name'}
    tool_params = {k: v for k, v in kwargs.items() if k not in special_params}

    # Extract special params for handle_base_readQuery
    persist = kwargs.get('persist', False)

    # Pass SQL with named placeholders and parameter values for safe binding
    return execute_db_tool(
        td.handle_base_readQuery,
        sql,
        tool_name=tool_name,
        persist=persist,
        **tool_params  # These will be safely bound by SQLAlchemy
    )

# Wrap handler as MCP tool
wrapped = make_tool_wrapper(handler)

# Register with FastMCP
mcp.tool(name=tool_name, description=description)(wrapped)
```

**Key Points**:
- SQL is generated once with placeholders (`:param1`, `:param2`)
- Parameter values are passed separately as kwargs
- SQLAlchemy safely binds parameters, preventing SQL injection
- Same secure pattern used by YAML tools

**Important Limitations**:
- **Registry tools do not support the `persist` parameter**:
  - The `persist` parameter is not available for registry tools (both UDFs and Macros)
  - Macros: Cannot be wrapped in `CREATE VOLATILE TABLE` (invalid: `CREATE VOLATILE TABLE vt AS (EXEC mydb.my_macro(param)) WITH DATA`) ❌
  - UDFs: While technically possible, persist is disabled for consistency and simplicity
  - If you need to persist results from registry tools, use YAML tools or Python tools instead

## Configuration

### Profile Setup

Configure registry database in [profiles.yml](src/teradata_mcp_server/config/profiles.yml):

```yaml
db-registry:
  registry: "mcp"  # Database containing registry views
  tool:
    - X      # No tool loaded from source code
  prompt:
    - .*
```

**Important**: Profile `tool` patterns do NOT filter registry tools. They only filter code-based tools. ALL registry tools are loaded regardless of patterns.
In the code above, all and only the tools registered in the `mcp` database schema are loaded.

### Environment Variables

```bash
DATABASE_URI="teradatasql://user:pass@host/database"
MCP_PROFILE="db-registry"  # Use profile with registry configuration
```


## Troubleshooting

### Tools Not Loading

**Check logs for**:
```log
[WARNING] No tools found in registry database 'mcp'
```

**Solution**: Verify database views exist and contain data:
```sql
SELECT * FROM mcp.mcp_list_tools;
SELECT * FROM mcp.mcp_list_toolParams;
```


## Files Reference

- **Implementation**: [app.py:893-978](src/teradata_mcp_server/app.py)
- **SQL Generation**: [registry_tools.py](src/teradata_mcp_server/tools/registry/registry_tools.py)
- **Database Loader**: [registry_loader.py](src/teradata_mcp_server/tools/registry/registry_loader.py)
- **Example Setup**: [examples/registry_setup_example.sql](examples/server-customization/registry_setup.sql)
- **Profile Config**: [profiles.yml](src/teradata_mcp_server/config/profiles.yml)

## Future Enhancements

Future improvements:

1. **Registry Refresh**: Add command to reload registry without server restart
2. **Tool Validation**: Validate database objects exist before registering tools
3. **Tool Categories**: Group registry tools by category/module
4. **Permissions**: Restrict tool listing based on end-user tool access rights.
