# Server Hook Example

This directory contains example configuration files for the Teradata MCP Server.

See the [developer guide](../../../docs/developer_guide/HOOKS.md) for full details about adding custom capabilities via hooks.

'perf_monitor_hooks.py' shows a demo of this capability.  You can add this via the --hooks_module argument.

```
uv run teradata-mcp-server --hooks_module /home/jovyan/JupyterLabRoot/perf_monitor_hooks.py
```

## What it does:
  1. on_tool_call — records the start time, keyed by request_id
  2. on_tool_result — calculates elapsed time, writes a log line
  3. on_tool_error — logs the error with elapsed time

## Sample output it would produce:

```
  2026-05-04 10:23:14 | base_tableList          |   0.234s | OK
  2026-05-04 10:23:15 | base_readQuery          |   1.842s | OK
  2026-05-04 10:23:16 | base_columnDescription  |   0.031s | ERROR: connection timeout
  2026-05-04 10:23:18 | dba_sessionInfo         |   0.118s | OK
```

## Why this is a good showcase:
  - Uses all three hook points in a cohesive way
  - Demonstrates state sharing between hooks (start time dict keyed by request_id)
  - No external dependencies — just writes to a .log file
  - The output is tangible and easy to verify during a demo
  - Works in both stdio and HTTP transport modes
