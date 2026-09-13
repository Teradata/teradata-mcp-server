# Base tools

**Dependencies**

Assumes Teradata >=17.20.

**Base** tools:

  - base_readQuery - runs a read query
  - base_tableDDL - returns the show table results
  - base_databaseList - returns a list of all databases
  - base_tableList - returns a list of tables in a database
  - base_columnDescription - returns description of columns in a table
  - base_tablePreview - returns column information and 5 rows from the table
  - base_tableAffinity - gets tables commonly used together
  - base_tableUsage - Measure the usage of a table and views by users in a given schema

The `base_query`, `base_tableBusinessDesc`, and `base_databaseBusinessDesc` prompts that used to live here are now Agent Skills: [`base-sql-assistant`](../../skills/README.md), [`base-table-business-description`](../../skills/README.md), and [`base-database-business-description`](../../skills/README.md) respectively.

[Return to Main README](../../../../README.md)
