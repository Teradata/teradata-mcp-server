# How cubes become SQL

When a `type: cube` is loaded, the server registers a single MCP tool whose Python signature is:

```
my_cube_tool(
    dimensions: str,         # comma-separated dimension names
    measures: str,           # comma-separated measure names
    dim_filters: str,        # raw SQL filter expression, applied PRE-aggregation
    meas_filters: str,       # raw SQL filter expression, applied POST-aggregation
    order_by: str,           # raw SQL ORDER BY expression
    top: int,                # TOP n (0 / empty = no TOP)
    # ...plus any custom parameters you declared under `parameters:`
)
```

The LLM-facing description for each of these args is auto-built from your cube's dimension / measure names — so you only need to write good `description:` strings on each dim and measure.

## The generated SQL

For a call with `dimensions = "d1, d2"`, `measures = "m1, m2"`, the server builds:

```sql
SELECT TOP {top} * FROM
(SELECT
  <expression-of-d1>,
  <expression-of-d2>,
  <expression-of-m1> AS m1,
  <expression-of-m2> AS m2
FROM (
  sel * from ( <YOUR BASE SQL, with :params substituted> ) a
  WHERE <dim_filters>          -- omitted if empty
) AS c
GROUP BY d1, d2
) AS a
WHERE <meas_filters>            -- omitted if empty
ORDER BY <order_by>             -- omitted if empty
;
```

Three consequences fall out of this shape — internalise them before authoring a cube.

### 1. `dim_filters` runs on **base SQL columns**, not on dimension expressions

The base SQL is wrapped as `sel * from ( ... ) a`, and `dim_filters` lives in the outer `WHERE` of that subquery. So `dim_filters` references **whatever columns your base SELECT emits**.

If your base SQL aliases columns to the same names as your dimensions, `dim_filters` looks symmetric to the LLM:
```yaml
dim_filters example:  database_name = 'FINANCE'
```
If you don't alias, the LLM will write `dim_filters` against dimension names that don't exist in the inner table, and you'll get a SQL error. **Always alias base columns to the dimension name** unless you have a strong reason not to.

### 2. `meas_filters` runs on **measure aliases**, not on aggregate expressions

After `GROUP BY`, the inner result has columns named after the measures (`m1`, `m2`, …). `meas_filters` is applied as the outer `WHERE`, so:
```yaml
meas_filters example:  current_perm_bytes > 1000000000     -- correct
meas_filters example:  SUM(current_perm_v) > 1000000000    -- WRONG, won't resolve
```

### 3. Window functions in measures see the **post-aggregation** rowset

Because the `OVER ()` evaluates after `GROUP BY`, you can write share-of-total style measures cleanly:

```yaml
share_of_total_pct:
  description: "Group's share of the total across all rows in the result, %."
  expression: "CAST(SUM(x_v) * 100.0 / NULLIFZERO(SUM(SUM(x_v)) OVER ()) AS DECIMAL(10,2))"
```

Note the double `SUM` — inner `SUM(x_v)` is the per-group aggregate, outer `SUM(...) OVER ()` is the total across groups.

## Designing the base SQL

A good base SQL is:

- **Flat and denormalised.** Pre-join all the dimension tables. The cube tool should not have to know about joins.
- **Pinned to a domain.** Hard-code the filters that define what the cube *is* (subject area, view flag, product family). Do not let the LLM pick those via `dim_filters`.
- **Row-grain matches the smallest dimension you expose.** If your finest dimension is `month_end × business_line`, that's your row grain. Coarser dim selections aggregate cleanly via `GROUP BY`.
- **Aliased to the public names.** Each base column that becomes a dimension is aliased to the dimension name; each base column that feeds a measure is aliased to a `_v` (value) suffix to signal "internal."

```sql
SELECT
  d.database_name      AS database_name,    -- dimension column, public name
  d.owner_name         AS owner_name,
  s.current_perm       AS current_perm_v,   -- internal value column
  s.max_perm           AS max_perm_v
FROM DBC.AllSpaceV s
JOIN DBC.DatabasesV d ON s.databasename = d.database_name
WHERE s.tablename = 'All'                   -- domain pin
```

## Period-vs-period and other parameterised cubes

If your cube needs runtime parameters (date ranges, currency, snapshot date), declare them under `parameters:` and reference them in the base SQL with `:name` bind syntax:

```yaml
sql: |
  SELECT ...
  FROM fact
  WHERE event_date BETWEEN :period_start AND :period_end
```

For comparison cubes (current period vs previous period), a common pattern is to emit period-tagged value columns from the base SQL, then `SUM` each in measures:

```sql
-- inside base SQL
CASE WHEN event_date BETWEEN :cstart AND :cend THEN amount END AS amount_cur_v,
CASE WHEN event_date BETWEEN :pstart AND :pend THEN amount END AS amount_prev_v
```
```yaml
measures:
  amount_cur:  { expression: "SUM(amount_cur_v)" }
  amount_prev: { expression: "SUM(amount_prev_v)" }
  delta:       { expression: "SUM(amount_cur_v) - SUM(amount_prev_v)" }
```

This lets the LLM compare two arbitrary periods through a single tool call, and the attribution measures (volume effect, rate effect) compose from the same value columns.

## Hard limits and soft guidance

- **No hard cap** on dimensions or measures, but selection quality degrades sharply beyond ~10 dims and ~15 measures. Split into two cubes rather than building a god-cube.
- **Dimensions and measures share a namespace** in `order_by`. You can order by either by name.
- **An unknown measure raises an error** (`ValueError: Measure '...' not found in cube '...'`); an unknown dimension is passed through as a raw column reference, which usually fails downstream. Validate both names in your tests.
