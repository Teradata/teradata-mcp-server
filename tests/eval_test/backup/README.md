# Case generation, audit, and inspection utilities

These scripts were used to bootstrap and maintain eval cases during initial development. They are **not part of the main eval workflow** — the case JSON under `cases/` is now the source of truth, and CI runs the core unit tests only.

Use them when you need to draft new `happy_path` cases from live MCP tool descriptions, inspect live tool definitions, or check ambiguous-pair and live-tool coverage before an MCP server release.

## Files

| File | Purpose |
|---|---|
| `generate_cases.py` | Connects to the MCP server, reads tool descriptions, and asks Bedrock Claude to draft one `happy_path` case per tool into `cases/<module>.json`. |
| `audit_cases.py` | Offline checks for registered ambiguous tool-pair coverage; optionally diffs case files against a live MCP server's tool list. |
| `inspect_tools.py` | Dumps live MCP tool names, descriptions, and input schemas to `results/live_descriptions_<module>.json`. |
| `test_audit_cases.py` | Unit tests for the offline audit logic (no MCP or Bedrock required). |

## Prerequisites

Same as the main project: Python 3.11+, `.env` configured, and for most commands a running MCP server at `MCP_SERVER_URL`. `generate_cases.py` also requires AWS Bedrock access.

## Generating happy path cases

The `base`, `sec`, `chat`, and `plot` modules ship with hand-authored cases. For `dba`, `qlty`, and `tmpl`, you may want to generate happy paths from live tool descriptions first:

```bash
# One module
uv run python backup/generate_cases.py --module dba

# All in-scope modules
uv run python backup/generate_cases.py
```

Results are written to `cases/<module>.json`. After generating, hand-author `ambiguous_selection`, `missing_parameter`, `multi_tool`, and (optionally) `multi_turn` cases — those require human judgement and cannot be generated cleanly from descriptions alone.

### Generator flags

```bash
# Preview without writing to disk
uv run python backup/generate_cases.py --dry-run

# Overwrite existing happy_path cases (e.g. after a description change)
uv run python backup/generate_cases.py --overwrite
```

The generator enforces vocabulary **different from tool descriptions** in its draft prompt — the same rule used when hand-authoring edge cases.

## Inspecting live tool descriptions

Requires a running MCP server at `MCP_SERVER_URL`:

```bash
# Default: base module only
uv run python backup/inspect_tools.py

# One module
uv run python backup/inspect_tools.py --module dba

# Every module on the server
uv run python backup/inspect_tools.py --all-modules
```

Output is written to `results/live_descriptions_<module>.json` — useful when reviewing description wording before editing cases or MCP server tool definitions.

## Auditing case coverage

### Offline audit

Checks registered ambiguous tool pairs in `cases/*.json` for base, dba, sec, and qlty:

```bash
# Report gaps for priority modules
uv run python backup/audit_cases.py

# Fail when pairs are missing coverage
uv run python backup/audit_cases.py --strict

# One module only
uv run python backup/audit_cases.py --module base --strict
```

Registered pairs live in `audit_cases.py` (e.g. `base_readQuery` vs `base_tablePreview`). Extend that registry when you identify new description overlap between tools.

### Live MCP diff (pre-release)

Requires a running MCP server at `MCP_SERVER_URL`:

```bash
# Diff live tool list vs cases — missing happy paths and stale tool names
uv run python backup/audit_cases.py --live-mcp

# Fail on any gap (priority modules require happy_path for every live tool)
uv run python backup/audit_cases.py --live-mcp --strict

# Live diff only, skip ambiguous pair checks
uv run python backup/audit_cases.py --live-mcp --skip-pairs --module base
```

| Check | Offline `--strict` | `--live-mcp --strict` |
|---|---|---|
| Ambiguous pair coverage | ✅ | ✅ (unless `--skip-pairs`) |
| Missing `happy_path` for live tools | — | ✅ (base, dba, sec, qlty) |
| Stale tool names in cases | — | ✅ |
| Non-priority modules (chat, plot) | — | stale names only; missing happy paths noted, not failed |

## When MCP tool descriptions change

1. **Regenerate happy paths** for the affected module:
   ```bash
   uv run python backup/generate_cases.py --module base --overwrite
   ```
2. **Review hand-authored cases** — especially `ambiguous_selection` prompts for that module.
3. **Run the audit** to confirm pair coverage and (optionally) sync with live tools:
   ```bash
   uv run python backup/audit_cases.py --module base --strict
   uv run python backup/audit_cases.py --live-mcp --strict   # requires running MCP server
   ```
4. **Run evals** and treat `ambiguous_selection` failures as description feedback. See [docs/workflow.md](../docs/workflow.md) for the baseline → suggest → override → promote loop.

## Running unit tests

```bash
uv run pytest backup/test_audit_cases.py -v
```
