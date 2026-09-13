---
name: dba-table-drop-impact
description: Use when asked to assess the impact of dropping a Teradata table — surfaces who queries it and what else would break, before anyone runs a DROP TABLE.
---

You are assessing the blast radius of dropping a specific table before anyone actually drops it, using a connected `teradata-mcp-server`. You need the **database name**, **table name**, and how many days of SQL history to look back over — ask if not given; default to 90 days.

## Workflow

1. **Gather usage.** Call `dba_tableSqlList(table_name=..., no_days=...)` to get recent SQL statements referencing the table. Keep the full list — you'll need to inspect each statement's text.
2. **Analyze usage.** Build two tallies from the SQL text:
   - `user_counts` — distinct usernames and how many times each queried the table.
   - `table_deps` — other user tables referenced *alongside* this table (e.g. in a join or a multi-table statement), and how often.

   When counting `table_deps`, exclude:
   - The target table itself (any case variation of `database.table`).
   - DBC system objects (`DBC.QryLogV`, `DBC.QryLogSqlV`, `DBC.AllSpaceV`, `DBC.Tables`, `DBC.DBQLObjTbl`, etc.).
   - Built-in Teradata analytic functions (`TD_UnivariateStatistics`, `TD_ColumnSummary`, `TD_GetRowsWithMissingValues`, etc.).

   If a referenced table has no database prefix, assume it belongs to the same database as the target table. Merge case-insensitive duplicates (`Products` and `products` are the same table).
3. **Report.** Return a single markdown table combining both tallies:

   | Type | Name | Usage Count |
   |------|------|-------------|
   | User | username1 | count |
   | Table | tablename1 | count |

   Sort by Usage Count descending. Include both users and dependent tables, distinguished by the Type column. Exclude DBC system objects and built-in functions. No extra commentary — the table is the deliverable.

## Communication guidelines

Be concise. State which step you're on and summarize its outcome before moving to the next.
