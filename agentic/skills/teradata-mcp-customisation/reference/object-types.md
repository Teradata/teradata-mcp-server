# Object types — full YAML schemas

All custom objects live in `*.yml` files in the config directory. Each file is a top-level dictionary keyed by **object name** (must be a regex-friendly identifier; use snake_case with a domain prefix). Multiple files are merged into one namespace.

Every object has a mandatory `type:` field selecting one of the four schemas below.

---

## `type: tool` — parameterised SQL query

A reusable SQL the LLM calls with arguments. The server wraps it through `base_readQuery` (read-only); for writes use the built-in `base_writeQuery`.

```yaml
my_tool_name:
  type: tool
  description: "What this tool does — surfaced to the LLM as the docstring."
  sql: |
    SELECT col1, col2
    FROM {database_name}.{table_name}
    WHERE event_date >= :start_date
      AND amount > :min_amount
    ORDER BY event_date
  parameters:
    database_name:
      description: "Schema containing the target table."
      type_hint: str
      default: "DBC"             # makes the parameter optional
    table_name:
      description: "Table to query."
      type_hint: str
    start_date:
      description: "Inclusive lower bound, 'YYYY-MM-DD'."
      type_hint: str
    min_amount:
      description: "Filter rows where amount strictly exceeds this."
      type_hint: float
      default: 0
```

**Required:** `type`, `sql`. **Recommended:** `description`, `parameters`.

**Auto-added parameters** (the LLM sees them on every custom tool):
- `persist: bool = False` — when `True`, materialises the result as a volatile table and returns the table name instead of rows. Useful for chaining tool calls without re-running expensive queries.

**Parameter fields:**
- `description` — surfaced to the LLM. Always write one.
- `type_hint` — one of `"str"`, `"int"`, `"float"`, `"bool"`, `"list"`, `"dict"`, `"Any"`. Anything else falls back to `str`. The resolved type is appended to the LLM-facing description as `(type: int)` etc.
- `default` — presence makes the parameter optional. Absence makes it required.

See `parameter-substitution.md` for the difference between `:name` (value binds) and `{name}` (identifier interpolation, e.g. table/database names that cannot be bound).

---

## `type: cube` — semantic aggregator

A flat base SQL plus a vocabulary of dimensions and measures. The server wraps the base SQL with a filter → GROUP BY → filter SELECT and exposes a single MCP tool whose 6 auto-added parameters drive the wrapping. See `cube-mechanics.md` for the exact generated SQL.

```yaml
my_cube_name:
  type: cube
  description: |
    What this cube models, what subject area it covers, what filters
    are baked in. Tell the LLM both when to use it and when NOT to.
  parameters:
    period_start:
      description: "Inclusive lower bound on event_date, 'YYYY-MM-DD'."
      type_hint: str
    period_end:
      description: "Inclusive upper bound on event_date, 'YYYY-MM-DD'."
      type_hint: str
  sql: |
    SELECT
      d.database_name   AS database_name,
      d.owner_name      AS owner_name,
      d.account_name    AS account_name,
      s.current_perm    AS current_perm_v,
      s.peak_perm       AS peak_perm_v,
      s.max_perm        AS max_perm_v
    FROM DBC.DatabasesV d
    JOIN DBC.AllSpaceV  s ON s.databasename = d.database_name
    WHERE s.tablename = 'All'
      AND d.database_name NOT IN ('DBC', 'TDWM')   -- pin domain
  dimensions:
    database_name:
      description: "Schema / database name (DBC.DatabasesV.database_name)."
      expression: database_name
    owner_name:
      description: "Database owner (creator)."
      expression: owner_name
    account_name:
      description: "Account string used for workload accounting."
      expression: account_name
  measures:
    current_perm_bytes:
      description: "Permanent space currently in use, bytes."
      expression: SUM(current_perm_v)
    peak_perm_bytes:
      description: "Peak permanent space observed, bytes."
      expression: MAX(peak_perm_v)
    utilisation_pct:
      description: "Current perm as % of granted max. NULL when max=0."
      expression: "CAST(SUM(current_perm_v) * 100.0 / NULLIFZERO(SUM(max_perm_v)) AS DECIMAL(10,2))"
    share_of_total_pct:
      description: "Group's share of total current_perm across the result, %."
      expression: "CAST(SUM(current_perm_v) * 100.0 / NULLIFZERO(SUM(SUM(current_perm_v)) OVER ()) AS DECIMAL(10,2))"
```

**Required:** `type`, `sql`, `dimensions`, `measures`. **Recommended:** `description`, `parameters`.

**Conventions that pay off:**
- In the base SQL, alias dimension source columns to the dimension name (`d.database_name AS database_name`) so the dimension `expression:` is just the bare name. Alias measure source columns with a `_v` suffix (`s.current_perm AS current_perm_v`) to signal "internal value column, not for direct selection."
- Pin domain filters in the base SQL `WHERE` (e.g. `tablename = 'All'`, exclude system schemas). Do not push that into `dim_filters`.
- Measure expressions are evaluated *after* the implicit `GROUP BY <dimensions>`. They can be any aggregate, including ratios, `CAST`s, and window expressions like `SUM(x) OVER ()` for share-of-total measures.

---

## `type: prompt` — reusable prompt

A named prompt the client fetches via `prompts/get`. Static text by default; parameterised with Python `str.format`-style placeholders.

```yaml
my_prompt_name:
  type: prompt
  description: "DBA persona that focuses on a chosen problem area."
  parameters:
    focus_area:
      description: "What the DBA should emphasise: 'space', 'workload', or 'security'."
      type_hint: str
      required: true
  prompt: |
    You are a Teradata DBA assistant. Focus on {focus_area} questions.
    When the user asks an unrelated question, redirect them politely.
```

**Required:** `type`, `prompt`. **Recommended:** `description`, `parameters`.

**Parameter fields for prompts** (differ slightly from tools):
- `description` — surfaced to the client.
- `type_hint` — same set as tools.
- `required: bool` — defaults to `true` (note: opposite default from tools, which infer requiredness from presence of `default`).
- `default` — if present, parameter is optional regardless of `required`.

If `parameters:` is empty or omitted, the prompt is served as-is. With parameters, the server calls `prompt.format(**kwargs)` — so any literal `{` in the prompt body must be doubled `{{` to escape.

---

## `type: glossary` — domain terms (becomes MCP resource)

A single glossary block defines many terms in one object. Selected by the **`resource:`** pattern list in profiles, not `tool:`.

```yaml
my_glossary:
  type: glossary
  permspace:
    definition: "Permanent table storage granted to a database, in bytes."
    synonyms:
      - perm
      - permanent space
  spool:
    definition: "Temporary intermediate storage used by Teradata query execution."
    synonyms:
      - spool space
  skew_factor:
    definition: |
      Distribution skew across AMPs, (max - avg) / max * 100. Above ~30%
      indicates a primary-index choice that should be reviewed.
    synonyms:
      - skew
      - amp skew
```

**Required:** each term has a `definition`. **Optional:** `synonyms` (list of strings).

The server **enriches the glossary automatically** with terms derived from cube measure and dimension descriptions — so if you have a cube exposing `current_perm_bytes`, that becomes a glossary-discoverable term without you defining it explicitly.

---

## File organisation conventions

```
my-config/
├── profiles.yml              # always at the root, name fixed
├── dbc_demo_objects.yml      # one file per domain / area
├── sales_objects.yml
└── finance_objects.yml
```

Object **names must be globally unique** across all files (later files override earlier ones by key). Profile **regex selectors** then carve up that flat namespace. Keep one file per business area so a single grep tells you what a domain exposes.
