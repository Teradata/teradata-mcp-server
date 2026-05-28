---
name: teradata-mcp-customisation
description: Use when the task is to build, edit, or debug a semantic layer for the Teradata MCP server (https://github.com/Teradata/teradata-mcp-server) — custom tools, cubes, prompts, and glossary entries declared in YAML, plus the profiles.yml that exposes them. Covers schema rules, the cube SQL wrapping model, parameter substitution, profile regex selection, and the runtime smoke-test flow.
---

You are extending the Teradata MCP server with a **semantic layer**: domain-specific tools, cubes, prompts, and glossary terms declared in YAML files that the server picks up at startup.

The server is the upstream project at https://github.com/Teradata/teradata-mcp-server. The customisation surface is documented in `docs/server_guide/CUSTOMIZING.md`; this skill compiles the parts that are easy to get wrong, plus working examples that anyone can run against the `DBC` system database.

## When to use this skill

- Designing a new semantic layer for a Teradata data product (cubes + curated prompts).
- Adding or editing a custom tool / cube / prompt / glossary entry.
- Building a `profiles.yml` to expose a subset of objects to a given client.
- Debugging why a custom object does not appear in `tools/list`, `prompts/list`, or `resources/list`.
- Migrating a hand-written SQL pattern into a reusable cube the LLM can compose.

## Mental model — what each object becomes at runtime

| YAML `type:` | Where it surfaces | Selected by profile section |
|---|---|---|
| `tool` | MCP **tool** — parameterised SQL the LLM calls | `tool:` |
| `cube` | MCP **tool** — the server auto-generates a 6-arg aggregator (dimensions, measures, dim_filters, meas_filters, order_by, top) plus any custom params you declare | `tool:` |
| `prompt` | MCP **prompt** — a reusable system / user prompt the client can fetch by name | `prompt:` |
| `glossary` | MCP **resource** — domain terms surfaced as context resources, enriched with cube measure/dim descriptions | `resource:` |

There is no `type: resource`. Resources are derived: glossary entries become resources, and cube/tool descriptions feed back into glossary enrichment.

## Workflow

1. **Locate the config directory.** The server reads YAML from `--config_dir` (CLI) or `$CONFIG_DIR` (env), defaulting to the current working directory. Drop one or more `*.yml` files there alongside `profiles.yml`. Multiple files merge into one namespace keyed by object name.
2. **Pick the object type** for what you are building. If in doubt, see `reference/object-types.md`.
3. **Write the SQL first, in isolation.** Run it in your usual Teradata client until it returns what you want — *then* wrap it as a tool or cube. For cubes, write the flat denormalised base SQL; let the server build the aggregator on top. See `reference/cube-mechanics.md` for exactly how the wrapping works (which is critical for understanding dim_filters vs meas_filters semantics).
4. **Get parameter substitution right.** Custom tools support two styles: `:param` for value binds, `{param}` for identifier interpolation (database / table names). Cubes also accept custom parameters used inside the base SQL the same way. See `reference/parameter-substitution.md`.
5. **Expose via `profiles.yml`.** Add a profile (or extend an existing one) with regex selectors. See `reference/profiles.md` for the layering rules and the built-in profiles you can inherit from.
6. **Smoke-test the server** with the MCP listing flow before pointing a client at it. See `reference/deployment.md` for the bash curl recipe (`initialize` → `notifications/initialized` → `tools/list`).

## Authoring rules (important — don't skip)

1. **Descriptions are the contract.** The `description` fields on tools, cubes, dimensions, measures, and parameters are what the LLM reads to choose and shape its calls. Write them like terse API docs: what it represents, units, when to use it, when *not* to. The server appends type info automatically — don't repeat it.
2. **Cubes are filtered twice.** `dim_filters` apply to the flat base SQL before aggregation (use raw column names from the base SELECT). `meas_filters` apply after `GROUP BY` (use measure names — `nii > 1000` not `SUM(nii_v) > 1000`). Get this wrong and the LLM will write filters that error or return nothing.
3. **Pin the domain in the base SQL `WHERE`.** Hard-code the filters that define what the cube *is* (one product family, one subject area). Do not leave that decision to `dim_filters` — the LLM will forget or invent.
4. **Keep the menu small.** Aim for ~10 dimensions and ~15 measures per cube. More than that and selection accuracy drops sharply. Split into two cubes if you have a wider surface.
5. **Aggregate measure expressions are first-class.** A measure `expression:` is whatever Teradata SQL evaluates to a scalar over the group — `SUM(...)`, ratios with `NULLIFZERO`, even `SUM(x) OVER ()` for "share of total" measures. The server inlines it as `expression AS measure_name`.
6. **Never embed credentials** in cube/tool SQL or in `profiles.yml`. Connection strings belong in `profiles.yml`'s `run:` block via env-var substitution (`${TD_USER}`, `${TD_PASSWORD}`), or in the server's own startup env.
7. **Name with a domain prefix.** `sales_growth_cube`, `dba_space_cube`. A single regex (`sales_.*`) then selects the whole pack into a profile.
8. **Prompts are not auto-attached.** A `type: prompt` is a callable resource the client *fetches by name* — it is not silently injected into every conversation. Document that in your prompt's `description`.

## Progressive references

Load these only when needed:

- `reference/object-types.md` — full YAML schemas for `tool`, `cube`, `prompt`, `glossary` with every field and what each does.
- `reference/cube-mechanics.md` — the exact SELECT the server generates around your base SQL, plus the auto-added cube parameters (`dimensions`, `measures`, `dim_filters`, `meas_filters`, `order_by`, `top`).
- `reference/parameter-substitution.md` — `:name` value binds vs `{name}` identifier formatting, the synthetic `{table_ref}` key, supported `type_hint` values, and the auto-added `persist` parameter on custom tools.
- `reference/profiles.md` — how `profiles.yml` layers over the packaged profiles, regex selector rules, the `run:` block (transport / port / database URI), and the built-in profiles you can extend (`all`, `eda`, `dba`, `dataScientist`, …).
- `reference/deployment.md` — `config_dir` resolution, server launch, and the bare-bones curl smoke-test that walks the streamable-HTTP MCP handshake to list tools / prompts / resources.

## Worked examples (DBC-only, portable)

All examples target `DBC` system views so anyone with Teradata access can run them without setting up sample data:

- `examples/example_tool.yml` — a parameterised tool that lists the N largest tables in a given database (`DBC.AllSpaceV`).
- `examples/example_cube.yml` — a "database space" cube on `DBC.AllSpaceV` with dimensions (database, account, owner) and measures (current_perm, peak_perm, skew_factor).
- `examples/example_prompt.yml` — a Teradata DBA persona prompt with a `{focus_area}` parameter.
- `examples/example_glossary.yml` — glossary entries for `permspace`, `spool`, `skew factor`.
- `examples/example_profiles.yml` — a `dbc_demo` profile that selects the four objects above by regex, plus inherited read-only base tools.

Copy any of these into a `*.yml` file in your config dir, restart the server, and they will appear in the relevant MCP list.
