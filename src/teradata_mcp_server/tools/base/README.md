# Base tools

**Dependencies**

Assumes Teradata >=17.20.

**Base** tools:

  - get_base_readQuery - runs a read query
  - write_base_writeQuery - runs a write query
  - get_base_tableDDL - returns the show table results
  - get_base_databaseList - returns a list of all databases
  - get_base_tableList - returns a list of tables in a database
  - get_base_columnDescription - returns description of columns in a table
  - get_base_tablePreview - returns column information and 5 rows from the table
  - get_base_tableAffinity - gets tables commonly used together
  - get_base_tableUsage - Measure the usage of a table and views by users in a given schema

**Base** Prompts:

  - base_query - Create a SQL query against the database
  - base_tableBusinessDesc - generates a business description of a table
  - base_databaseBusinessDesc - generates a business description of a databases based on the tables

  
[Return to Main README](../../../../README.md)
