# Teradata MCP Eval Run Summary

**Started (UTC):** 2026-06-24T00:05:13.720459+00:00
**Module filter:** base
**Case type filter:** all
**Agent model:** anthropic.claude-3-5-sonnet-20241022-v2:0
**Judge model:** anthropic.claude-3-5-sonnet-20241022-v2:0
**Eval database:** demo_user
**Tool descriptions:** live MCP server (baseline)

## Overview

| Metric | Count |
| --- | ---: |
| Total cases | 32 |
| Passed | 0 |
| Failed | 32 |

## Failed cases

### base_readQuery_happy (happy_path)

**Description:** Execute a SQL query against the evals employees table

**Eval prompt:**

> Run this query: SELECT name, department, salary FROM demo_user.evals_employees WHERE department = 'Sales'

**Expected tool(s):**

- `base_readQuery` with params:
```json
{
  "sql": "SELECT name, department, salary FROM demo_user.evals_employees WHERE department = 'Sales'"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_readQuery_ambiguous_vs_tablePreview (ambiguous_selection)

**Description:** Prompt with a WHERE clause should use base_readQuery, not base_tablePreview

**Eval prompt:**

> Get me all orders from demo_user.evals_orders where the amount is greater than 500

**Expected tool(s):**

- `base_readQuery` with params:
```json
{
  "sql": "SELECT * FROM demo_user.evals_orders WHERE amount > 500"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_readQuery_missing_sql (missing_parameter)

**Description:** Agent must ask for clarification when no SQL or table is given

**Eval prompt:**

> Query the database for me

**Expected tool(s):**

_none_

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_tableList_happy (happy_path)

**Description:** List tables in the evals database

**Eval prompt:**

> What tables are in the demo_user database?

**Expected tool(s):**

- `base_tableList` with params:
```json
{
  "database_name": "demo_user"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_tableList_missing_database (missing_parameter)

**Description:** User asks for tables without specifying a database

**Eval prompt:**

> Show me what tables are available

**Expected tool(s):**

_none_

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_tableDDL_happy (happy_path)

**Description:** Retrieve DDL for the evals employees table

**Eval prompt:**

> Show me the CREATE statement for evals_employees in the demo_user database

**Expected tool(s):**

- `base_tableDDL` with params:
```json
{
  "database_name": "demo_user",
  "table_name": "evals_employees"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_tableDDL_ambiguous_vs_columnMetadata (ambiguous_selection)

**Description:** Asking for full structure including constraints should prefer base_tableDDL

**Eval prompt:**

> Describe the full structure of demo_user.evals_employees including any constraints and indexes

**Expected tool(s):**

- `base_tableDDL` with params:
```json
{
  "database_name": "demo_user",
  "table_name": "evals_employees"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_columnMetadata_happy (happy_path)

**Description:** Get precise Teradata type codes, character sets, and precision for columns in evals_orders

**Eval prompt:**

> Give me the exact Teradata type codes, character set, and decimal precision for every column in demo_user.evals_orders

**Expected tool(s):**

- `base_columnMetadata` with params:
```json
{
  "database_name": "demo_user",
  "object_name": "evals_orders"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_columnMetadata_ambiguous_vs_tableDDL (ambiguous_selection)

**Description:** Asking for technical Teradata column precision metadata should prefer base_columnMetadata over base_tableDDL

**Eval prompt:**

> I need the UNICODE vs LATIN character set and nullability for every column in demo_user.evals_employees

**Expected tool(s):**

- `base_columnMetadata` with params:
```json
{
  "database_name": "demo_user",
  "object_name": "evals_employees"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_tablePreview_happy (happy_path)

**Description:** Preview a sample of rows from the evals orders table

**Eval prompt:**

> Give me a quick preview of what's in demo_user.evals_orders

**Expected tool(s):**

- `base_tablePreview` with params:
```json
{
  "database_name": "demo_user",
  "table_name": "evals_orders"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_tablePreview_ambiguous_vs_readQuery (ambiguous_selection)

**Description:** A simple 'show me a few rows' without a WHERE clause should use base_tablePreview

**Eval prompt:**

> Show me a few rows from demo_user.evals_orders

**Expected tool(s):**

- `base_tablePreview` with params:
```json
{
  "database_name": "demo_user",
  "table_name": "evals_orders"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_databaseList_happy (happy_path)

**Description:** List all accessible databases

**Eval prompt:**

> What databases do I have access to?

**Expected tool(s):**

- `base_databaseList` with params:
```json
{}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_tableList_ambiguous_vs_databaseList (ambiguous_selection)

**Description:** Listing tables inside one database should prefer base_tableList, not base_databaseList

**Eval prompt:**

> What tables exist inside the demo_user database?

**Expected tool(s):**

- `base_tableList` with params:
```json
{
  "database_name": "demo_user"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_databaseList_ambiguous_vs_tableList (ambiguous_selection)

**Description:** Listing accessible databases should prefer base_databaseList, not base_tableList

**Eval prompt:**

> Which databases am I allowed to connect to on this system?

**Expected tool(s):**

- `base_databaseList` with params:
```json
{}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_saveDDL_ambiguous_vs_tableDDL (ambiguous_selection)

**Description:** Persisting DDL to a file should prefer base_saveDDL, not base_tableDDL

**Eval prompt:**

> Export the DDL for demo_user.evals_orders to a file on disk

**Expected tool(s):**

- `base_saveDDL` with params:
```json
{
  "database_name": "demo_user",
  "table_name": "evals_orders"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_tableAffinity_ambiguous_vs_tableUsage (ambiguous_selection)

**Description:** Finding tables co-queried with a specific table should prefer base_tableAffinity, not base_tableUsage

**Eval prompt:**

> Which tables in demo_user tend to appear in the same queries as evals_employees?

**Expected tool(s):**

- `base_tableAffinity` with params:
```json
{
  "database_name": "demo_user",
  "table_name": "evals_employees"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_tableUsage_ambiguous_vs_tableAffinity (ambiguous_selection)

**Description:** Access frequency for tables in a database should prefer base_tableUsage, not base_tableAffinity

**Eval prompt:**

> Who has been reading tables in demo_user lately and how often?

**Expected tool(s):**

- `base_tableUsage` with params:
```json
{
  "database_name": "demo_user"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_saveDDL_happy (happy_path)

**Description:** Save DDL for the evals employees table to a file

**Eval prompt:**

> Save the DDL for evals_employees in demo_user to a file

**Expected tool(s):**

- `base_saveDDL` with params:
```json
{
  "database_name": "demo_user",
  "table_name": "evals_employees"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_tableAffinity_happy (happy_path)

**Description:** Find tables commonly queried together with evals_orders

**Eval prompt:**

> Which tables in demo_user are most often queried together with evals_orders?

**Expected tool(s):**

- `base_tableAffinity` with params:
```json
{
  "database_name": "demo_user",
  "table_name": "evals_orders"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_tableUsage_happy (happy_path)

**Description:** Check usage metrics for the evals database

**Eval prompt:**

> How frequently are the tables in demo_user being accessed and by whom?

**Expected tool(s):**

- `base_tableUsage` with params:
```json
{
  "database_name": "demo_user"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_multi_tool_list_then_preview (multi_tool)

**Description:** List tables in evals database then preview one

**Eval prompt:**

> List all tables in demo_user, then show me a preview of evals_employees

**Expected tool(s):**

- `base_tableList` with params:
```json
{
  "database_name": "demo_user"
}
```
- `base_tablePreview` with params:
```json
{
  "database_name": "demo_user",
  "table_name": "evals_employees"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_multi_tool_ddl_then_columns (multi_tool)

**Description:** Get DDL then drill into column detail for the same table

**Eval prompt:**

> First show me the DDL for demo_user.evals_orders, then give me the detailed column metadata

**Expected tool(s):**

- `base_tableDDL` with params:
```json
{
  "database_name": "demo_user",
  "table_name": "evals_orders"
}
```
- `base_columnMetadata` with params:
```json
{
  "database_name": "demo_user",
  "object_name": "evals_orders"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_tableDDL_missing_table (missing_parameter)

**Description:** Agent must ask for database name when only table is provided

**Eval prompt:**

> Show me the CREATE statement for evals_employees

**Expected tool(s):**

_none_

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_tablePreview_missing_table (missing_parameter)

**Description:** Agent must ask which table to preview

**Eval prompt:**

> Preview some rows

**Expected tool(s):**

_none_

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_saveDDL_missing_table (missing_parameter)

**Description:** Agent must ask which table to save DDL for

**Eval prompt:**

> Save the DDL to a file

**Expected tool(s):**

_none_

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_tablePreview_clarify_then_call (missing_parameter)

**Description:** Agent asks which table to preview, then calls base_tablePreview after user clarifies

**Eval prompt:**

> Turn 1: Preview some rows for me | Turn 2: Preview rows from demo_user.evals_employees

**Expected tool(s):**

_none_

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_tableList_clarify_then_call (missing_parameter)

**Description:** Agent asks which database, then calls base_tableList after user clarifies

**Eval prompt:**

> Turn 1: Show me what tables are available | Turn 2: List tables in the demo_user database

**Expected tool(s):**

_none_

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_readQuery_clarify_then_call (missing_parameter)

**Description:** Agent asks for SQL, then calls base_readQuery after user provides the query

**Eval prompt:**

> Turn 1: Run a query for me | Turn 2: Run: SELECT name, department FROM demo_user.evals_employees WHERE department = 'Sales'

**Expected tool(s):**

_none_

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_columnDescription_happy (happy_path)

**Description:** Show basic column info for the evals employees table

**Eval prompt:**

> Show me the columns in demo_user.evals_employees

**Expected tool(s):**

- `base_columnDescription` with params:
```json
{
  "database_name": "demo_user",
  "table_name": "evals_employees"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_columnDescription_ambiguous_vs_columnMetadata (ambiguous_selection)

**Description:** A simple 'what columns does this table have' question should prefer base_columnDescription

**Eval prompt:**

> What are the column names and types in demo_user.evals_orders?

**Expected tool(s):**

- `base_columnDescription` with params:
```json
{
  "database_name": "demo_user",
  "table_name": "evals_orders"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_columnMetadata_ambiguous_vs_columnDescription (ambiguous_selection)

**Description:** Asking for precise Teradata type codes and character sets should prefer base_columnMetadata

**Eval prompt:**

> Give me the exact Teradata type codes, character sets, and precision details for every column in demo_user.evals_employees

**Expected tool(s):**

- `base_columnMetadata` with params:
```json
{
  "database_name": "demo_user",
  "object_name": "evals_employees"
}
```

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

### base_unknown_tool_missing (missing_parameter)

**Description:** User asks to do something no tool supports — agent should explain and ask for clarification

**Eval prompt:**

> Automatically tune my Teradata database indexes and rebalance the AMPs

**Expected tool(s):**

_none_

**Actual tool(s):**

_none_

**Failure (agent):** unhandled errors in a TaskGroup (1 sub-exception)

**Recommendation:**

The agent loop failed before scoring: unhandled errors in a TaskGroup (1 sub-exception). Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable with the current environment (`EVALS_DATABASE=demo_user`).

## Passed cases

_None._

