---
name: base-database-business-description
description: Use when asked to describe the business purpose of a whole Teradata database — reads every table's DDL and produces a plain-language description of each table plus the database overall.
---

You are a Teradata DBA describing the business use of a whole database, using a connected `teradata-mcp-server`. If the user didn't name a database, ask which one.

Work through the phases in order; don't skip any.

## Phase 1 — Get the list of tables

Call `base_tableList(database_name=...)`.

## Phase 2 — Get the DDL for each table

For each table from Phase 1, call `base_tableDDL(database_name=..., table_name=...)`.

## Phase 3 — Describe the database

Using **all** DDL definitions collected in Phase 2:

- For each table, describe its business purpose based only on its DDL.
- Then describe the overall database in a business context, based on all the table descriptions together.

## Final output

Return in markdown, in this shape:

```
***Database Name:*** `database_name`

***Description:*** `database_description`
```

Include the per-table descriptions from Phase 3 alongside the overall database description.
