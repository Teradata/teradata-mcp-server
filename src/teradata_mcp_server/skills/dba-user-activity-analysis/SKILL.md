---
name: dba-user-activity-analysis
description: Use when asked to analyze Teradata user activity over the past week — ranks users by resource consumption and drills into the heaviest consumers' recent SQL.
---

You are analyzing Teradata user activity for the past 7 days (or whatever window the user asks for), using a connected `teradata-mcp-server`.

## Workflow

1. **System-wide resource usage.** Call `dba_resusageSummary(no_days=7)`. A single call returns rows already broken down by `LogDate`, `hourOfDay`, `dayOfWeek`, `workloadType`, `workloadComplexity`, `UserName`, and `AppID` — you don't need to call it more than once or once per dimension.
2. **Rank users.** From the step 1 results, rank users by CPU time (primary), IO operations (secondary), and memory/byte usage (tertiary). Compute each user's share of total system resources.
3. **Drill into the top consumers.** For each of the top 5 users by CPU time, call `dba_userSqlList(user_name=..., no_days=7)` to get their recent SQL activity. `user_name` is required — this tool cannot be called for "all users" at once, so call it once per user of interest.
4. **Report.** Produce a dashboard-style write-up:
   - System-wide resource overview with an hour-of-day heatmap for the period, color-coded by CPU usage.
   - The user ranking table from step 2, with resource shares as percentages.
   - Each top user's peak activity hours and workload mix.
   - For the top 5: their recent SQL activity, which tables they hit most, and how complex/long their queries ran.
   - Sortable tables and color-coded metrics throughout; include specific query and table examples where useful.

## Gotchas

- `dba_userSqlList` requires a specific `user_name` — you cannot call it with no arguments or an empty name to get "everyone's" SQL history. Use `dba_resusageSummary`'s per-user breakdown for the system-wide view, and only call `dba_userSqlList` per user when you need that user's individual SQL history.
