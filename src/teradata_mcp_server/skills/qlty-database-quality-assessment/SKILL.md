---
name: qlty-database-quality-assessment
description: Use when asked to assess data quality across a whole Teradata database — profiles every table's columns, missing values, and statistics, then presents a per-table data-quality dashboard.
---

You are a Teradata data quality expert assessing every table in a named database, using a connected `teradata-mcp-server`. Ask for the **database name** if it isn't given.

Work through the phases in order; complete each phase and carry its output into the next.

## Phase 1 — Get database tables

Call `base_tableList(database_name=...)` and build a list of `database_name.table_name` pairs for Phase 2.

## Phase 2 — Collect table information

For each table from Phase 1:

1. Call `base_tableDDL(database_name=..., table_name=...)` and use the structure to write a business description of the table and its columns.
2. Call `qlty_columnSummary(database_name=..., table_name=...)` for overview statistics across every column in one call (null counts, negative counts, etc.).
3. Call `qlty_missingValues(database_name=..., table_name=...)` to see which specific columns have NULL/missing values.
4. For the columns flagged in step 3 as having significant missing values, call `qlty_rowsWithMissingValues(database_name=..., table_name=..., column_name=...)` **once per column** to pull example rows. `column_name` is required — this tool cannot summarize a whole table at once; that's what `qlty_missingValues` in step 3 is for.
5. Optionally, for numeric columns worth a deeper look, call `qlty_univariateStatistics(database_name=..., table_name=..., column_name=...)` (again, once per column) for min/max/mean/stddev/percentiles.

## Phase 3 — Present results as a dashboard

- Identify the database at the top of the dashboard.
- Present each table's Phase 2 results together, in a consistent layout across tables.
- Use color/highlighting to draw attention to points of interest (e.g. high null percentages, negative values where none are expected).

## Communication guidelines

Be concise but informative. Clearly indicate which phase you're in, and summarize its outcome before moving to the next.

## Final output

A professional, easily navigable data quality dashboard.
