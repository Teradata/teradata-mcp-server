# `profiles.yml`

Profiles select **which objects** the server exposes for a given launch and (optionally) **how the server runs** (transport, port, database URI). The selectors are regex patterns matched against object names; the runtime block is plain key/value.

## Layering

The server loads profiles in this order:

1. **Packaged profiles** from `src/teradata_mcp_server/config/profiles.yml` (ships with the install).
2. **Your `profiles.yml`** in the config directory — replaces the packaged file at the **top-level key** (whole-profile replace, no merge).

Pick the profile at launch via `--profile <name>` or `$PROFILE`. If unset (or `all`), the `all` packaged profile is used: everything loads.

## Schema

```yaml
profile_name:
  tool:
    - regex_pattern_.*
    - exact_tool_name
  prompt:
    - regex_pattern_.*
  resource:
    - regex_pattern_.*
  registry: "schema_name"          # optional — load tools from a DB tool registry
  run:                             # optional — overrides startup settings
    database_uri: "teradata://${TD_USER}:${TD_PASSWORD}@host:1025"
    mcp_transport: "streamable-http"
    mcp_port: 8001
```

- Each section's value is a **list of regex patterns**. An object matches if **any** pattern matches its name. Patterns are not anchored automatically — write `^foo_.*` if you want a prefix match (`foo_.*` alone matches names containing `foo_` anywhere).
- `tool:` selects both `type: tool` and `type: cube` objects.
- `prompt:` selects `type: prompt` objects.
- `resource:` selects `type: glossary` objects (and any future resource types).

## Built-in profiles you can mirror or extend

Excerpt of the packaged `profiles.yml` (see upstream for the source of truth):

```yaml
all:
  tool:     [".*"]
  prompt:   ["^(?!test_).*"]
  resource: [".*"]

eda:
  tool:
    - "base_(?!(writeQuery|dynamicQuery)$).*"  # read-only base tools only
    - qlty_.*
    - sec_userDbPermissions

dba:
  tool:    ["^dba_*", "^base_*", "^sec_*"]
  prompt:  ["^dba_*"]

dataScientist:
  tool:
    - ^base_*
    - ^rag_*
    - ^sql_*
    - ^fs_*
    - ^qlty_*
    - ^tdvs_*
    - ^sec_userDbPermissions
    - ^dba_userSqlList
    - ^plot_*
    - ^tdml_*
  prompt: ["^rag_*", "^sql_*", "^tdvs_*"]
```

Useful patterns when composing your own profile:

| Goal | Pattern |
|---|---|
| All your domain objects | `^mydomain_.*` |
| All read-only base tools (no DDL/DML, no dynamic SQL) | `base_(?!(writeQuery\|dynamicQuery)$).*` |
| Data-quality tools | `qlty_.*` |
| Single user's permissions check | `sec_userDbPermissions` |
| Everything except tests | `^(?!test_).*` |

## Composing a "business" + "exploration" profile

A common shape: one profile that exposes **only your curated semantic layer** for an end-user chat, and a second profile that adds read-only base tools for analysts who need to free-form explore.

```yaml
sales_business:
  tool:
    - sales_.*_cube
  prompt:
    - sales_.*
  resource:
    - sales_.*
  run:
    mcp_transport: "streamable-http"
    mcp_port: 8006

sales_super:
  tool:
    - sales_.*_cube
    - "base_(?!(writeQuery|dynamicQuery)$).*"
    - qlty_.*
  prompt:
    - sales_.*
  resource:
    - sales_.*
  run:
    mcp_transport: "streamable-http"
    mcp_port: 8007
```

Different ports per profile let you run both side-by-side and point different clients at each.

## The `registry:` field (database-backed tools)

If set, the server reads two views from that schema at startup:

- `<schema>.mcp_list_tools` — rows describing tools (name, object, description)
- `<schema>.mcp_list_toolParams` — rows describing each tool's parameters

Registered objects can be UDFs (`F`), Macros (`M`), Tables (`T`), or Views (`V`). Registry-loaded tools are **not filtered by the profile's regex selectors** — turning on the registry exposes everything in it. Use a separate schema per profile if you need scoping.

## `run:` block

Anything you'd otherwise set via env / CLI:

- `database_uri` — full SQLAlchemy URI with `${VAR}` env-var substitution.
- `mcp_transport` — `streamable-http`, `sse`, `stdio`.
- `mcp_port` — only meaningful for HTTP transports.
- `logging_level`, `config_dir`, etc. — anything in `Settings`.

Values here override env and CLI for that profile. Use this to bind a profile to a specific environment without juggling `.env` files.

## Validating

After editing `profiles.yml`, restart the server and verify with the smoke-test in `deployment.md`. A missing object in `tools/list` is almost always a regex that doesn't match (forgetting `^`, or putting the object in the wrong section — e.g. glossary in `tool:`).
