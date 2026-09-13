---
name: dba-dashboard
description: Use when asked to build a Teradata system health/status dashboard for a DBA — space usage, resource consumption, flow control, and session activity. Calls the teradata-mcp-server dba_* and base_* tools and renders the results as a single dashboard (HTML artifact, markdown report, or chat response, depending on what the client supports).
---

You are building a Teradata system health dashboard for a DBA audience, using the tools exposed by a connected `teradata-mcp-server` (profile must include the `dba_` and `base_` tool prefixes — e.g. `--profile dba` or `--profile all`).

## Workflow

Work through the phases below in order. Each phase is one or two tool calls — do not iterate per day or per database unless a step says to.

### Phase 1 — Inventory and space

1. `base_databaseList(scope="user")` — or `scope="all"` if the DBA wants system databases included too. Use the result as the list of databases for later phases.
2. `dba_systemSpace()` — total space used/allocated/free across the whole system.
3. `dba_tableSpace(database_name=..., top_n=10, exclude_system="Y")` for the database(s) in scope — largest tables and how full they are.
4. `dba_databaseSpace(database_name=...)` per database in scope — allocated vs. used vs. free space.

`dba_databaseSpace`, `dba_tableSpace`, and `dba_tableUsageImpact` all **require** a non-empty `database_name`. If the DBA didn't name one, iterate the list from step 1 rather than passing an empty string.

### Phase 2 — Resource usage (CPU / IO / memory)

`dba_resusageSummary(no_days=30)` returns one row per `LogDate` × `hourOfDay` × `dayOfWeek` × `workloadType` × `workloadComplexity` × `UserName` × `AppID` already grouped — a **single call** gives the full 30-day breakdown needed for both a daily trend and an hour-of-day heatmap. Don't call it once per dimension or once per day.

Use `workloadType`/`workloadComplexity` filters only if the DBA wants to drill into one slice (e.g. `workloadType="Batch"`).

### Phase 3 — Flow control and queueing

`dba_flowControl` and `dba_userDelay` take explicit `start_date`/`end_date` (`YYYY-MM-DD`), not a day count. Compute the range yourself (e.g. today minus 30 days) and call each **once**:

1. `dba_flowControl(start_date=..., end_date=...)` — when and how much the workload manager throttled queries.
2. `dba_userDelay(start_date=..., end_date=...)` — how long users personally waited in queue before their queries started.

### Phase 4 — Sessions and activity

1. `dba_sessionInfo(user_name="*")` — currently active sessions across all users.
2. `base_tableUsage(database_name=...)` per database in scope — which tables are hottest and who's hitting them.

### Phase 5 — Optional context

- `dba_databaseVersion()` — software version, useful in the dashboard header.
- `dba_featureUsage(start_date=..., end_date=...)` — which product features were exercised in the period, if the DBA cares about feature adoption.

## Rendering the dashboard

Structure the output as:

1. **Executive summary** — system version, total space used/allocated/free, number of databases and tables in scope, headline resource trend, any critical alerts.
2. **Space** — system-wide totals, per-database breakdown, top space-consuming tables. Color-code utilization: red ≥ 85%, yellow 70–85%, green < 70%.
3. **Resource usage** — CPU/IO/memory trend by day, plus an hour-of-day × day heatmap from the Phase 2 data.
4. **Flow control & delay** — throttling events and queue wait times from Phase 3, called out as bottlenecks if delay times are material.
5. **Sessions & activity** — active sessions and the busiest tables/users from Phase 4.

If the client can render an HTML artifact, build the dashboard as a single self-contained page (see the `dataviz` skill for chart/color guidance if available) so it's easy to skim. Otherwise, present the same structure as markdown with tables and a short narrative per section — don't skip sections just because charts aren't available.

## Gotchas

- Never call `dba_databaseSpace`, `dba_tableSpace`, or `dba_tableUsageImpact` with an empty `database_name` — ask which database, or iterate the list from `base_databaseList`.
- `dba_flowControl` and `dba_userDelay` want computed `start_date`/`end_date`, not a `no_days` count like `dba_resusageSummary` — don't mix the two calling conventions up.
- `base_databaseList` defaults to `scope="user"` (excludes system databases); pass `scope="all"` explicitly if the DBA wants system databases in the picture.
- To hand a metric to the `plot_*` tools (`plot_line_chart`, `plot_pie_chart`, ...), materialize it first by calling the source tool with `persist=true`, then pass the returned table name — the plot tools read from a table, not from raw query results.
