# Database Tool Registry

This module enables dynamic loading of MCP tools from database-registered objects (UDFs and Macros).

## Overview

Instead of defining tools in YAML files or Python code, you can register them directly in the Teradata database. This allows:

- **Dynamic tool discovery**: Tools are loaded at server startup from the database
- **User-specific tools**: Different users can have access to different tools based on database permissions
- **Centralized management**: Tool definitions stored in the database alongside the logic
- **Version control**: Tool metadata versioned with database objects

## Database Schema

The registry requires two views in a dedicated database (e.g., `mcp`):

### 1. `mcp_list_tools`

Lists all available tools for the current user.

**Columns:**

| Column | Type | Description |
|--------|------|-------------|
| ToolName | VARCHAR | Name of the MCP tool (must be unique) |
| DataBaseName | VARCHAR | Database where the object resides |
| TableName | VARCHAR | Name of the UDF or Macro |
| docstring | VARCHAR | Tool description (used as MCP tool description) |
| Tags | VARCHAR | Comma-separated tags (optional) |

**Example:**

```sql
CREATE VIEW mcp.mcp_list_tools AS
SELECT
    'dba_databaseSpace' AS ToolName,
    'demo_user' AS DataBaseName,
    'dba_databaseSpace' AS TableName,
    'Get database space allocation and usage' AS docstring,
    'dba' AS Tags
FROM (SELECT 1) AS dummy
WHERE USER IN (SELECT UserName FROM DBC.AllRightsV WHERE DatabaseName = 'demo_user');
```

### 2. `mcp_list_toolParams`

Defines parameters for each tool.

**Columns:**

| Column | Type | Description |
|--------|------|-------------|
| ToolName | VARCHAR | Tool name (matches mcp_list_tools.ToolName) |
| ParamName | VARCHAR | Parameter name |
| ParamType | VARCHAR | Teradata data type (CV, I, F, DA, etc.) |
| ParamLength | INTEGER | Type length/precision (optional) |
| ParamPosition | INTEGER | Parameter position (1-based) |
| ParamRequired | CHAR(1) | 'Y' or 'N' |
| ParamComment | VARCHAR | Parameter description |

**Example:**

```sql
CREATE VIEW mcp.mcp_list_toolParams AS
SELECT
    'get_weekday' AS ToolName,
    'dt' AS ParamName,
    'CV' AS ParamType,
    100 AS ParamLength,
    1 AS ParamPosition,
    'Y' AS ParamRequired,
    'Date string in YYYY-MM-DD format' AS ParamComment
FROM (SELECT 1) AS dummy;
```

## Type Mapping

Teradata types are automatically mapped to Python types:

| Teradata Type | Python Type |
|---------------|-------------|
| CV, CF, CHAR, VARCHAR | str |
| I, I1, I2, I8, INTEGER, BIGINT | int |
| F, FLOAT, D, DECIMAL, NUMERIC | float |
| DA, DATE, TS, TIMESTAMP, TIME | str |
| BO, BOOLEAN | bool |

## Profile Configuration

To enable database registry tools, add a `registry` key to your profile in [profiles.yml](../../../config/profiles.yml):

```yaml
db-registry:
  registry: "mcp"  # Database containing mcp_list_tools and mcp_list_toolParams
  tool:
    - ^base_*      # Also load base tools
    - ^dba_*       # Load any tools matching these patterns
  prompt:
    - .*
```

The `registry` value specifies the database name where the registry views are located.

## Important: DATABASE_URI Required

**Registry tools require DATABASE_URI to be set** because the server needs to query the database at startup to discover tools.

### For Claude Desktop (stdio mode):
Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "teradata": {
      "command": "teradata-mcp-server",
      "args": ["--profile", "db-registry"],
      "env": {
        "DATABASE_URI": "teradatasql://username:password@host:port/database"
      }
    }
  }
}
```

### For Command Line:
```bash
export DATABASE_URI="teradatasql://username:password@host:port/database"
teradata-mcp-server --profile db-registry
```

## How It Works

1. **Server Startup**: When a profile with a `registry` key is selected, the server:
   - Requires DATABASE_URI to be set
   - Queries `mcp.mcp_list_tools` for available tools
   - Queries `mcp.mcp_list_toolParams` for parameter definitions
   - Builds tool definitions similar to YAML tools

2. **Tool Registration**: For each tool:
   - A dynamic MCP tool is created with the correct signature
   - Parameters are mapped to Python types
   - Tool is registered with FastMCP

3. **Tool Execution**: When a tool is called:
   - Parameters are validated
   - SQL is generated: `SELECT * FROM db.object(params)` for UDFs or `EXEC db.object(params)` for Macros
   - Results are returned as JSON

## Example: Creating a Registry Tool

### Step 1: Create the UDF

```sql
-- Create a simple UDF that extracts weekday from a date
REPLACE FUNCTION demo_user.get_weekday(dt VARCHAR(100))
RETURNS TABLE (weekday_name VARCHAR(20))
LANGUAGE SQL
CONTAINS SQL
DETERMINISTIC
SQL SECURITY DEFINER
RETURN
SELECT
    CASE DAY_OF_WEEK
        WHEN 1 THEN 'Sunday'
        WHEN 2 THEN 'Monday'
        WHEN 3 THEN 'Tuesday'
        WHEN 4 THEN 'Wednesday'
        WHEN 5 THEN 'Thursday'
        WHEN 6 THEN 'Friday'
        WHEN 7 THEN 'Saturday'
    END AS weekday_name
FROM SYS_CALENDAR.CALENDAR
WHERE CALENDAR_DATE = CAST(dt AS DATE);
```

### Step 2: Register in mcp_list_tools

```sql
-- Add to your mcp_list_tools view
INSERT INTO mcp.tools_metadata VALUES (
    'get_weekday',
    'demo_user',
    'get_weekday',
    'Extracts the weekday name from a date string',
    'general'
);
```

### Step 3: Register Parameters

```sql
-- Add to your mcp_list_toolParams view
INSERT INTO mcp.params_metadata VALUES (
    'get_weekday',
    'dt',
    'CV',
    100,
    1,
    'Y',
    'Date string in YYYY-MM-DD format'
);
```

### Step 4: Use in MCP Client

```python
# The tool is now available in any MCP client
result = await session.call_tool("get_weekday", {"dt": "2025-12-15"})
print(result)  # {"weekday_name": "Monday"}
```

## Security Considerations

- **Row-level security**: Use `WHERE USER IN (...)` in your views to show only authorized tools
- **Database permissions**: Users must have EXECUTE permissions on the underlying UDFs/Macros
- **SQL injection**: Parameter values are properly escaped before execution
- **Validation**: Required parameters are validated before execution

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Profile: db-registry                                        │
│   registry: "mcp"                                           │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ RegistryLoader                                              │
│  - Queries mcp.mcp_list_tools                               │
│  - Queries mcp.mcp_list_toolParams                          │
│  - Builds tool definitions                                  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ make_registry_tool()                                        │
│  - Creates MCP tool with signature                          │
│  - Registers with FastMCP                                   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ handle_registry_tool()                                      │
│  - Validates parameters                                     │
│  - Generates SQL: SEL/EXEC object(params)                   │
│  - Executes and returns results                             │
└─────────────────────────────────────────────────────────────┘
```

## Module Files

- [registry_loader.py](registry_loader.py) - Queries database and builds tool definitions
- [registry_tools.py](registry_tools.py) - Executes registered tools (UDFs/Macros)
- [__init__.py](__init__.py) - Module exports

## Future Enhancements

1. **Auto-detect object type**: Query `DBC.FunctionsV` vs `DBC.MacrosV` to determine UDF vs Macro
2. **Support stored procedures**: Extend to support more database object types
3. **Caching**: Cache tool definitions to reduce database queries
4. **Refresh**: Add mechanism to reload tools without restarting server
5. **Object type column**: Add `ObjectType` to `mcp_list_tools` view for explicit type specification
