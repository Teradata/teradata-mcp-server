---
name: dba-table-lineage
description: Use when asked to map data lineage between tables in a Teradata database — traces which tables feed which by mining recent SQL history.
---

You are tracing the lineage of tables in a Teradata database from recent SQL activity, using a connected `teradata-mcp-server`.

Ask for (or infer from the request) the **database name** and how many days of history to search — default to 30 days if the user doesn't say.

## Workflow

1. **List the tables.** Call `base_tableList(database_name=...)`. Drop any table named `All`. Keep the list for step 2.
2. **Collect SQL history per table.** For each table from step 1, call `dba_tableSqlList(table_name=..., no_days=...)`.
3. **Derive lineage.** Using all SQL text collected in step 2:
   - For each statement, identify source and target tables from `INSERT ... SELECT`, `CREATE TABLE ... AS`, `MERGE INTO`, and `JOIN` patterns.
   - Build a deduplicated list of `(source_database.source_table, target_database.target_table)` pairs.
4. Present the lineage list as the final output — a simple diagram or table of the pairs is fine if the client can render one.

## Gotchas

- `dba_tableSqlList` matches purely on table name (a `LIKE '%table_name%'` search against SQL text) — it has no database filter, so its results can include statements referencing a same-named table in a different database. Filter those out yourself when a table name isn't unique across the system.
