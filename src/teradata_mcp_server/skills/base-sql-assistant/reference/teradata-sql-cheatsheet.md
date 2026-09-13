# Teradata SQL cheat sheet

Quick reference for common Teradata functions, statements, keywords, and types.

## Common functions

| Function | Description | Parameters |
|---|---|---|
| `count` | Total number of rows returned by a query result. | `result` |
| `sum` | Total of all non-null values in a column/expression across rows. | `arg` |
| `max` | Largest value from a column/expression. | `arg`, `n` (top-n list size, optional) |
| `min` | Smallest value in a group of input values. | `expression` |
| `avg` | Average of non-null values. | `arg` |
| `coalesce` | Returns the first non-NULL value among the given expressions; NULL if all are NULL. | `expr`, `...` (additional expressions, optional) |
| `trunc` | Truncates a date/timestamp to the given precision (e.g. first day of week). | `date`, `precision`, `format` (optional) |
| `row_number` | Unique incrementing number per row within a partition, starting at 1. | `ORDER BY` (optional), `PARTITION BY` (optional), `RANGE`/`ROWS` (optional), `EXCLUDE` (optional), `WINDOW` (optional) |
| `concat` | Concatenates multiple strings into one. | `string` |
| `lower` | Converts a string to lower case. | `string` |
| `TO_CHAR` | Converts a date/timestamp/numeric expression to a VARCHAR using a format pattern. | `value`, `format` (e.g. `dd-mon-yyyy`, `9,999.99`, `$9.99`) |
| `OREPLACE` | Replaces all occurrences of a substring within a string. | `source_string`, `search_string`, `replace_string` (omit to remove `search_string`) |
| `round` | Rounds a numeric value to a given number of decimal places. | `v`, `s` |
| `length` | Length of a string. | `value` |
| `MONTHS_BETWEEN` | Number of months between two dates. | `enddate`, `startdate` |
| `lag` | Value from a prior row within the same result set partition. | `expression`, `offset` (optional), `default_value` (optional) |
| `year` | Extracts the year from a date/timestamp. | `date`/`timestamp` |

## Common statements

- **`FROM`** — specifies the data source: a table, joined tables, or subqueries.
  `JOIN` combines rows from two or more tables (INNER, OUTER LEFT/RIGHT/FULL, CROSS, self-join).
  ```sql
  SELECT * FROM table_name;
  SELECT * FROM database_name.schema_name.table_name;
  SELECT * FROM table_name JOIN other_table ON table_name.key = other_table.key;
  SELECT * FROM table_a LEFT JOIN table_b ON table_a.id = table_b.id;
  SELECT * FROM table_name SAMPLE 10;
  ```
- **`SELECT`** — retrieves rows; combines with `FROM`, `WHERE`, `GROUP BY`, `ORDER BY`, `TOP`.
  ```sql
  SELECT i, sum(j) FROM tbl GROUP BY i;
  SELECT TOP 3 * FROM tbl ORDER BY i DESC;
  SELECT DISTINCT city FROM addresses;
  ```
- **`WHERE`** — filters rows, applied right after `FROM`.
  ```sql
  SELECT * FROM table_name WHERE UPPER(name) LIKE '%MARK%';
  SELECT * FROM table_name WHERE date_column BETWEEN DATE '2023-01-01' AND DATE '2023-12-31';
  ```
- **`ORDER BY`** — sorts rows, ascending/descending, NULLS FIRST/LAST, by name or position.
  ```sql
  SELECT * FROM addresses ORDER BY city DESC NULLS LAST;
  SELECT * FROM addresses ORDER BY 1, 2;
  ```
- **`GROUP BY`** — groups rows for aggregation.
  ```sql
  SELECT department, COUNT(*) FROM employees GROUP BY department;
  ```
- **`WITH`** — common table expressions (CTEs), including recursive CTEs.
  ```sql
  WITH cte AS (SELECT 42 AS x) SELECT * FROM cte;
  WITH RECURSIVE FibonacciNumbers (RecursionDepth, FibonacciNumber, NextNumber) AS (
    SELECT 0, 0, 1
    UNION ALL
    SELECT fib.RecursionDepth + 1, fib.NextNumber, fib.FibonacciNumber + fib.NextNumber
    FROM FibonacciNumbers fib WHERE fib.RecursionDepth + 1 < 10
  ) SELECT RecursionDepth, FibonacciNumber FROM FibonacciNumbers;
  ```
- **`TOP`** — restricts the number of rows returned (`SELECT TOP n`); pair with `QUALIFY` + `ROW_NUMBER()` for more sophisticated filtering.
  ```sql
  SELECT * FROM employees QUALIFY ROW_NUMBER() OVER (ORDER BY salary DESC) <= 5;
  ```
- **`CASE`** — conditional expression with `WHEN`/`ELSE`; returns NULL if no branch matches and `ELSE` is omitted.
  ```sql
  SELECT i, CASE WHEN i = 1 THEN 10 WHEN i = 2 THEN 20 ELSE 0 END AS test FROM integers;
  ```
- **`CREATE TABLE`** — defines columns, types, constraints, primary keys; supports volatile/global temporary tables and `CREATE TABLE ... AS SELECT`.
  ```sql
  CREATE TABLE t1 (id INTEGER PRIMARY KEY, j VARCHAR(50));
  CREATE VOLATILE TABLE temp_t1 AS (SELECT * FROM source_table) WITH DATA;
  CREATE GLOBAL TEMPORARY TABLE gtt1 (id INTEGER, name VARCHAR(100));
  ```
- **`DROP`** — removes a database object (table, view, function, index, database, user, macro, procedure); supports `IF EXISTS`.
  ```sql
  DROP TABLE tbl;
  DROP VIEW IF EXISTS v1;
  ```
- **`ALTER TABLE`** — adds/drops columns, sets/drops defaults and NOT NULL constraints. Transactional.
  ```sql
  ALTER TABLE integers ADD COLUMN l INTEGER DEFAULT 10;
  ALTER TABLE integers DROP COLUMN k;
  RENAME TABLE integers TO integers_old;
  ```
- **`HAVING`** — filters grouped results after aggregation (unlike `WHERE`, which filters before grouping).
  ```sql
  SELECT city, count(*) FROM addresses GROUP BY city HAVING count(*) >= 50;
  ```
- **`UPDATE`** — modifies rows; supports joins via `FROM`, subqueries, or `MERGE` for upserts.
- **`SHOW TABLE`** / **`HELP TABLE`** — display table structure and metadata.
  ```sql
  HELP TABLE employee;
  SHOW TABLE employee;
  ```
- **`DATABASE`** — sets the default database for the session.
  ```sql
  DATABASE my_database;
  ```
- **`INSERT`** — inserts values or query results.
  ```sql
  INSERT INTO tbl SELECT * FROM other_tbl;
  ```
- **`DELETE`** — removes rows, optionally filtered by `WHERE`, joins, or `MERGE`.
- **`CREATE VIEW`** — defines a virtual table backed by a query, re-run each time it's referenced.
  ```sql
  CREATE VIEW employee_summary AS SELECT department, COUNT(*) AS emp_count FROM employees GROUP BY department;
  ```
- **`VALUES`** — supplies rows to `INSERT INTO`.
  ```sql
  INSERT INTO cities (name, id) VALUES ('Amsterdam', 1), ('London', 2);
  ```

## Common types

`VARCHAR`, `INTEGER`, `NULL`, `DATE`, `TIME`, `TIMESTAMP`, `DECIMAL`/`NUMERIC`, `FLOAT`/`REAL`, `BIGINT`, `DOUBLE PRECISION`, `BLOB`.

```sql
CREATE TABLE people (name VARCHAR(100), age INTEGER);
CREATE TABLE salaries (employee_id INTEGER, base_salary DECIMAL(10, 2));
SELECT DATE '1992-03-22' + 5;                         -- 1992-03-27
SELECT EXTRACT(YEAR FROM DATE '1992-09-20');           -- 1992
SELECT TIMESTAMP '1992-09-20 11:30:00' + INTERVAL '10' DAY;
SELECT CAST(3.7 AS INTEGER) AS whole_number;
```

## Common keywords

- **`AS`** — alias for columns/tables. `SELECT first_name AS name FROM employees;`
- **`DISTINCT`** — removes duplicate rows. `SELECT DISTINCT city, state FROM addresses;`
- **`IN`** — matches against a list of values. `WHERE department IN ('HR', 'Engineering')`
- **`ALL`** — used with `UNION ALL` / `EXCEPT ALL` to retain duplicates.
- **`LIKE`** — pattern matching; `_` matches one character, `%` matches any sequence.
  ```sql
  SELECT 'abc' LIKE 'a%';   -- true
  SELECT 'abc' LIKE '_b_';  -- true
  ```
