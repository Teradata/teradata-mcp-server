# Teradata MCP Eval Run Summary

**Started (UTC):** 2026-06-23T21:14:19.042368+00:00
**Module filter:** all
**Case type filter:** all
**Agent model:** us.anthropic.claude-sonnet-4-5-20250929-v1:0
**Judge model:** us.anthropic.claude-sonnet-4-5-20250929-v1:0
**Eval database:** demo_user
**Tool descriptions:** live MCP server (baseline)

## Overview

| Metric | Count |
| --- | ---: |
| Total cases | 106 |
| Passed | 103 |
| Failed | 3 |

## Failed cases

### base_tableList_missing_database (missing_parameter)

**Description:** User asks for tables without specifying a database

**Eval prompt:**

> Show me what tables are available

**Expected tool(s):**

_none_

**Actual tool(s):**

- `base_tableList` with params:
```json
{
  "database_name": ""
}
```

**Agent response (excerpt):**

> I can see the system has many tables available. The results show tables across multiple databases. Here's a summary of what I found:

**Main Databases with Tables:**
- **DBC** - System database with metadata tables (InDoubtLog, StatsTbl, QryLog, DBCInfo, etc.)
- **TD_SYSFNLIB** - System function library
- **SYSLIB** - System library
- **TD_SERVER_DB** - Server database
- **SQLJ** - SQL/Java support
- **TD_SYSGPL** - System GPL (General Purpose Library)
- **SystemFe** - System functions
- **SYSSP

**Failure (deterministic):** expected no tool calls for missing_parameter case, got ['base_tableList']

**Recommendation:**

The prompt deliberately omits required information: "Show me what tables are available". The agent called `base_tableList` instead of asking for clarification. Recommendation: review whether those tool descriptions invite calls without full context, and keep the eval prompt vague enough that asking is the only reasonable response.

### base_tableList_clarify_then_call (missing_parameter)

**Description:** Agent asks which database, then calls base_tableList after user clarifies

**Eval prompt:**

> Turn 1: Show me what tables are available | Turn 2: List tables in the demo_user database

**Expected tool(s):**

_none_

**Actual tool(s):**

- `base_tableList` with params:
```json
{
  "database_name": ""
}
```

**Agent response (excerpt):**

> I can see there are tables available in the system. The results show many tables from the **DBC** database (which is the Teradata Data Dictionary/system catalog). 

Would you like me to:
1. **Filter by a specific database** - If you're looking for user/application tables rather than system tables, please tell me which database to show
2. **Show only user databases** - I can list the available databases first so you can pick one
3. **Continue showing all tables** - though the full list is quite l

**Failure (deterministic):** turn 1: expected no tool calls for missing_parameter case, got ['base_tableList']

**Turn details:**

```json
[
  {
    "turn": 1,
    "input": "Show me what tables are available",
    "mode": "clarification",
    "passed": false,
    "failure_stage": "deterministic",
    "failure_detail": "expected no tool calls for missing_parameter case, got ['base_tableList']",
    "actual_tools": [
      {
        "name": "base_tableList",
        "params": {
          "database_name": ""
        }
      }
    ]
  }
]
```

**Recommendation:**

The prompt deliberately omits required information: "(multi-turn — see turn details)". The agent called `base_tableList` instead of asking for clarification. Recommendation: review whether those tool descriptions invite calls without full context, and keep the eval prompt vague enough that asking is the only reasonable response.

### qlty_distinctCategories_missing_column (missing_parameter)

**Description:** Agent must ask which column when none is specified

**Eval prompt:**

> What distinct values exist in a column of demo_user.evals_orders?

**Expected tool(s):**

_none_

**Actual tool(s):**

- `base_columnDescription` with params:
```json
{
  "database_name": "demo_user",
  "table_name": "evals_orders"
}
```

**Agent response (excerpt):**

> The `demo_user.evals_orders` table has the following columns:

1. **product_category** (VARCHAR)
2. **ship_date** (DATE)
3. **customer_name** (VARCHAR)
4. **order_id** (INTEGER)
5. **quantity** (INTEGER)
6. **amount** (DECIMAL)
7. **order_date** (DATE)

Which column would you like to see the distinct values for?

**Failure (deterministic):** expected no tool calls for missing_parameter case, got ['base_columnDescription']

**Recommendation:**

The prompt deliberately omits required information: "What distinct values exist in a column of demo_user.evals_orders?". The agent called `base_columnDescription` instead of asking for clarification. Recommendation: review whether those tool descriptions invite calls without full context, and keep the eval prompt vague enough that asking is the only reasonable response.

## Passed cases

- `base_readQuery_happy` (happy_path)
- `base_readQuery_ambiguous_vs_tablePreview` (ambiguous_selection)
- `base_readQuery_missing_sql` (missing_parameter)
- `base_tableList_happy` (happy_path)
- `base_tableDDL_happy` (happy_path)
- `base_tableDDL_ambiguous_vs_columnMetadata` (ambiguous_selection)
- `base_columnMetadata_happy` (happy_path)
- `base_columnMetadata_ambiguous_vs_tableDDL` (ambiguous_selection)
- `base_tablePreview_happy` (happy_path)
- `base_tablePreview_ambiguous_vs_readQuery` (ambiguous_selection)
- `base_databaseList_happy` (happy_path)
- `base_tableList_ambiguous_vs_databaseList` (ambiguous_selection)
- `base_databaseList_ambiguous_vs_tableList` (ambiguous_selection)
- `base_saveDDL_ambiguous_vs_tableDDL` (ambiguous_selection)
- `base_tableAffinity_ambiguous_vs_tableUsage` (ambiguous_selection)
- `base_tableUsage_ambiguous_vs_tableAffinity` (ambiguous_selection)
- `base_saveDDL_happy` (happy_path)
- `base_tableAffinity_happy` (happy_path)
- `base_tableUsage_happy` (happy_path)
- `base_multi_tool_list_then_preview` (multi_tool)
- `base_multi_tool_ddl_then_columns` (multi_tool)
- `base_tableDDL_missing_table` (missing_parameter)
- `base_tablePreview_missing_table` (missing_parameter)
- `base_saveDDL_missing_table` (missing_parameter)
- `base_tablePreview_clarify_then_call` (missing_parameter)
- `base_readQuery_clarify_then_call` (missing_parameter)
- `base_columnDescription_happy` (happy_path)
- `base_columnDescription_ambiguous_vs_columnMetadata` (ambiguous_selection)
- `base_columnMetadata_ambiguous_vs_columnDescription` (ambiguous_selection)
- `base_unknown_tool_missing` (missing_parameter)
- `chat_completeChat_missing_message` (missing_parameter)
- `chat_unknown_tool_missing` (missing_parameter)
- `dba_tableSpace_happy` (happy_path)
- `dba_tableSqlList_happy` (happy_path)
- `dba_userSqlList_happy` (happy_path)
- `dba_databaseSpace_happy` (happy_path)
- `dba_tableUsageImpact_happy` (happy_path)
- `dba_resusageSummary_happy` (happy_path)
- `dba_databaseVersion_happy` (happy_path)
- `dba_flowControl_happy` (happy_path)
- `dba_featureUsage_happy` (happy_path)
- `dba_userDelay_happy` (happy_path)
- `dba_sessionInfo_happy` (happy_path)
- `dba_systemSpace_happy` (happy_path)
- `dba_tableSpace_ambiguous_vs_databaseSpace` (ambiguous_selection)
- `dba_databaseSpace_ambiguous_vs_systemSpace` (ambiguous_selection)
- `dba_systemSpace_ambiguous_vs_databaseSpace` (ambiguous_selection)
- `dba_tableSqlList_ambiguous_vs_userSqlList` (ambiguous_selection)
- `dba_userSqlList_ambiguous_vs_tableSqlList` (ambiguous_selection)
- `dba_tableUsageImpact_ambiguous_vs_resusageSummary` (ambiguous_selection)
- `dba_resusageSummary_ambiguous_vs_tableUsageImpact` (ambiguous_selection)
- `dba_tableUsageImpact_ambiguous_vs_sessionInfo` (ambiguous_selection)
- `dba_sessionInfo_ambiguous_vs_tableUsageImpact` (ambiguous_selection)
- `dba_userDelay_ambiguous_vs_flowControl` (ambiguous_selection)
- `dba_flowControl_ambiguous_vs_userDelay` (ambiguous_selection)
- `dba_tableSpace_missing_db` (missing_parameter)
- `dba_tableSqlList_missing_table` (missing_parameter)
- `dba_userSqlList_missing_user` (missing_parameter)
- `dba_databaseSpace_missing_db` (missing_parameter)
- `dba_tableUsageImpact_missing_db` (missing_parameter)
- `dba_databaseSpace_clarify_then_call` (missing_parameter)
- `dba_tableSqlList_clarify_then_call` (missing_parameter)
- `dba_userSqlList_clarify_then_call` (missing_parameter)
- `dba_unknown_tool_missing` (missing_parameter)
- `plot_line_chart_happy` (happy_path)
- `plot_pie_chart_happy` (happy_path)
- `plot_polar_chart_happy` (happy_path)
- `plot_radar_chart_happy` (happy_path)
- `plot_line_vs_radar_ambiguous` (ambiguous_selection)
- `plot_pie_vs_polar_ambiguous` (ambiguous_selection)
- `plot_missing_data` (missing_parameter)
- `plot_pie_chart_direct` (happy_path)
- `plot_missing_table` (missing_parameter)
- `plot_unknown_tool_missing` (missing_parameter)
- `qlty_missingValues_happy` (happy_path)
- `qlty_missingValues_ambiguous_vs_rowsWithMissingValues` (ambiguous_selection)
- `qlty_negativeValues_happy` (happy_path)
- `qlty_distinctCategories_happy` (happy_path)
- `qlty_standardDeviation_happy` (happy_path)
- `qlty_standardDeviation_ambiguous_vs_univariateStatistics` (ambiguous_selection)
- `qlty_columnSummary_happy` (happy_path)
- `qlty_univariateStatistics_happy` (happy_path)
- `qlty_univariateStatistics_ambiguous_vs_columnSummary` (ambiguous_selection)
- `qlty_rowsWithMissingValues_happy` (happy_path)
- `qlty_rowsWithMissingValues_ambiguous_vs_missingValues` (ambiguous_selection)
- `qlty_multi_tool_summary_then_nulls` (multi_tool)
- `qlty_unknown_tool_missing` (missing_parameter)
- `sec_userDbPermissions_ambiguous_vs_userRoles` (ambiguous_selection)
- `sec_userDbPermissions_missing_user` (missing_parameter)
- `sec_rolePermissions_ambiguous_vs_userDbPermissions` (ambiguous_selection)
- `sec_userRoles_ambiguous_vs_rolePermissions` (ambiguous_selection)
- `sec_rolePermissions_ambiguous_vs_userRoles` (ambiguous_selection)
- `sec_userRoles_ambiguous_vs_userDbPermissions` (ambiguous_selection)
- `sec_multi_tool_user_roles_then_role_permissions` (multi_tool)
- `sec_userDbPermissions_happy` (happy_path)
- `sec_rolePermissions_happy` (happy_path)
- `sec_userRoles_happy` (happy_path)
- `sec_rolePermissions_missing_role` (missing_parameter)
- `sec_userRoles_missing_user` (missing_parameter)
- `sec_userRoles_clarify_then_call` (missing_parameter)
- `sec_rolePermissions_clarify_then_call` (missing_parameter)
- `sec_userDbPermissions_clarify_then_call` (missing_parameter)
- `sec_unknown_tool_missing` (missing_parameter)

