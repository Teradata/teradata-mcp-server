# Parameter substitution

Custom tools and cubes can take runtime parameters. The server supports **two substitution styles** in the SQL body; both can be used in the same statement.

## `:name` — SQLAlchemy named bind parameter (for values)

The default style. Use for literal values: dates, numbers, strings, filter predicates.

```yaml
get_recent_events:
  type: tool
  sql: |
    SELECT *
    FROM events_table
    WHERE event_date >= :start_date
      AND severity   >= :min_severity
  parameters:
    start_date:   { type_hint: str,   description: "'YYYY-MM-DD'" }
    min_severity: { type_hint: int,   description: "0..5" }
```

Pros: SQL-injection-safe, types preserved through the driver, query plan can be cached.

**You cannot bind identifiers** (database, schema, table, column names) this way — the driver will quote them as literal strings, producing `SELECT * FROM 'DBC.AllSpaceV'` and an error.

## `{name}` — Python format-string interpolation (for identifiers)

When *any* `{…}` placeholder is present in the SQL body, the server first runs `sql.format_map(...)` against the supplied kwargs, then passes the resulting SQL to the bind-parameter step. This lets you parameterise table and database names.

```yaml
list_table_columns:
  type: tool
  sql: |
    SELECT ColumnName, ColumnType
    FROM DBC.ColumnsV
    WHERE DatabaseName = '{database_name}'
      AND TableName    = '{table_name}'
    ORDER BY ColumnId
  parameters:
    database_name: { type_hint: str, description: "Schema name." }
    table_name:    { type_hint: str, description: "Table name." }
```

**Risk:** identifier interpolation is *not* injection-safe in general. If your tool may be called by an untrusted client, validate the values (e.g. uppercase ASCII + underscore) before relying on this. For most internal MCP deployments, the caller is the LLM and the surface is small enough to be acceptable.

### The synthetic `{table_ref}` key

When the SQL contains `{table_ref}`, the server synthesises it from `database_name` + `table_name`:
- both given → `database_name.table_name`
- only `table_name` → `table_name`

This lets you write:
```yaml
sql: |
  SELECT COUNT(*) AS row_count FROM {table_ref}
parameters:
  database_name: { type_hint: str, default: "" }
  table_name:    { type_hint: str }
```

Both `database_name` and `table_name` are consumed by `format_map` and **not** also passed as bind params — so the tool is internally consistent even if you also reference them as `:database_name` elsewhere (don't — pick one style per parameter).

## Mixing the two styles

Allowed and common: identifiers via `{…}`, values via `:…`.

```yaml
top_n_by_size:
  type: tool
  sql: |
    SELECT
      TableName                                AS table_name,
      SUM(CurrentPerm)                         AS current_perm_bytes,
      SUM(PeakPerm)                            AS peak_perm_bytes,
      CAST(SUM(CurrentPerm) / 1024.0 / 1024.0
            AS DECIMAL(18,2))                   AS current_perm_mb
    FROM DBC.AllSpaceV
    WHERE DataBaseName = :database_name
      AND TableName   <> 'All'
    GROUP BY TableName
    QUALIFY ROW_NUMBER() OVER (ORDER BY SUM(CurrentPerm) DESC) <= :n
    ORDER BY current_perm_bytes DESC
  parameters:
    database_name: { type_hint: str, default: "DBC" }
    n:             { type_hint: int, default: 10 }
```

> **Never use `TOP N` with a parameter — use `ROW_NUMBER()` instead.**  
> `TOP :n` fails because Teradata's parser requires a literal integer immediately after
> the `TOP` keyword, before bind-parameter substitution occurs (error 3707:
> *"expected something like an integer … between the 'TOP' keyword and '?'"*).  
> `TOP {n}` avoids the parse error (Python string-substitution produces a literal), but
> it bypasses the prepared-statement layer entirely, which is fragile and injection-prone.  
> The correct pattern is a derived-table with `ROW_NUMBER() OVER (ORDER BY …)` and
> `WHERE rn <= :n` in the outer query — `:n` is then a normal value bind that works safely.
> The same applies to `SAMPLE :n`.

## `type_hint` values

Resolved against `{str, int, float, bool, list, dict, Any}`. Anything else (`"datetime"`, `"Decimal"`, …) silently falls back to `str`. If you need richer typing, validate inside your SQL (`CAST(:x AS DATE)`) instead.

## The auto-added `persist` parameter

Every custom tool gets a `persist: bool = False` parameter automatically. When the LLM passes `persist=True`, the server materialises the result into a volatile table and returns the table name as a string, rather than streaming rows. This is the canonical way to chain tool calls — e.g. write the output of one tool, then have a second tool join against it by name.

You do not declare `persist` yourself; do not collide with the name.

## Required vs optional

- **Custom tools / cubes:** a parameter is **required** if its YAML entry has no `default:`. Add a `default:` to make it optional.
- **Prompts:** opposite default — a parameter is required unless `required: false` is set (or a `default:` is provided).

Keep required parameters to a minimum. Every required parameter is one more thing the LLM must successfully infer from the user's question.
