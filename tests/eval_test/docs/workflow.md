# Running evals & description workflow

## End-to-end flow

The main loop measures **live MCP tool descriptions**, improves wording locally, then promotes changes back to the MCP server.

```
setup_test_data.py  →  run_evals.py (baseline)
                              ↓
              results/runs/<run_id>/summary.{md,json}
              results/latest.json  ← pointer to latest run
                              ↓
              suggest_overrides.py
                              ↓
              results/runs/<run_id>/suggested_overrides.json
                              ↓
              suggest_overrides.py --apply
                              ↓
              description_overrides.json
                              ↓
              run_evals.py --with-description-overrides
                              ↓
              promote to MCP server  →  run_evals.py (baseline again)
```

| Step | Command / file | Purpose |
|------|----------------|---------|
| 1. Prepare | `setup_test_data.py`, MCP server running | Eval tables + live tools |
| 2. Baseline | `run_evals.py` | Agent sees **live MCP descriptions**; writes artifacts under `results/runs/<run_id>/` |
| 3. Triage | `results/latest_summary.md` or run directory | Pass/fail counts, eval prompts, recommendations |
| 4. Draft fixes | `suggest_overrides.py` | Bedrock drafts revised descriptions for failed `ambiguous_selection` cases |
| 5. Review | run's `suggested_overrides.json` | Human review — **not applied automatically** |
| 6. Apply | `uv run python suggest_overrides.py --apply` | Replace `description_overrides.json` with draft suggestions only |
| 6. Test locally | `description_overrides.json` + `--with-description-overrides` | Patch descriptions without changing the MCP server |
| 7. Ship | Edit descriptions in MCP server repo | Re-run baseline evals to confirm |

## Running evals

Before a live run: test tables created, MCP server at `MCP_SERVER_URL`. `run_evals.py` runs preflight automatically.

```bash
python run_evals.py                              # all modules
python run_evals.py --module base                # one module
python run_evals.py --module base --type ambiguous_selection
python run_evals.py --verbose
python run_evals.py --run-label after-tablelist-fix   # optional label in run directory name
python run_evals.py --list-runs                       # show recent runs
```

### `--type` filter

| Value | Matches case IDs containing |
|---|---|
| `happy_path` | `happy` |
| `ambiguous_selection` | `ambiguous` |
| `missing_parameter` | `missing` |
| `multi_tool` | `multi_tool` |
| `multi_turn` | `clarify_then_call` |

Advanced filtering via deepeval/pytest, e.g. `deepeval test run tests/ -k "test_base and tablePreview"`.

## Baseline vs overrides

**Default:** evals use live MCP server tool descriptions.

**Opt-in overrides:** review the draft, then apply with `suggest_overrides.py --apply`, or re-run with:

```bash
python run_evals.py --module base --with-description-overrides
python run_evals.py --module base --description-overrides-file my_overrides.json
```

Or set `USE_DESCRIPTION_OVERRIDES=1` / `DESCRIPTION_OVERRIDES_FILE=...` in `.env`.

### Suggesting override drafts

After a baseline run with failures:

```bash
uv run python suggest_overrides.py
uv run python suggest_overrides.py --type missing_parameter
uv run python suggest_overrides.py --type ambiguous_selection,happy_path
```

Processes failed **`ambiguous_selection`**, **`happy_path`**, **`missing_parameter`**, and **`multi_tool`** cases by default. Each type gets a tailored prompt:

| Case type | What it revises |
|---|---|
| `ambiguous_selection` | Both competing tools — sharpen routing boundaries |
| `happy_path` | Expected tool (and wrong tool if one was called) |
| `missing_parameter` | Tools called prematurely — add “ask first” constraints |
| `multi_tool` | Tools in the workflow — clarify sequencing |

`missing_parameter` cases where the agent never called a tool (judge-only clarification failure) are **skipped** — those are agent behavior, not description routing.

Flags: `--summary`, `--output`, `--overrides-file`, `--type`, `--dry-run`.

Reads the latest run summary (`results/latest.json` → `results/runs/<run_id>/summary.json`), fetches live MCP descriptions, and writes the draft into that run directory (also copied to `results/suggested_overrides.json`). Review the draft, then apply:

```bash
uv run python suggest_overrides.py --apply
uv run python suggest_overrides.py --apply --dry-run          # preview merge
uv run python suggest_overrides.py --apply --tools base_tableList  # one tool only
uv run python run_evals.py --with-description-overrides
```

## Results layout

Each eval run gets its own directory under `results/runs/`. The directory name encodes when and how the run was executed, for example:

`2026-06-23T20-40-34.611558Z__base__overrides`

Format: `<timestamp>__<module>__<baseline|overrides>[__<case-type>][__<run-label>]`

| Path | Contents |
|---|---|
| `results/runs/<run_id>/summary.md` | Human-readable triage report for that run |
| `results/runs/<run_id>/summary.json` | Structured case results |
| `results/runs/<run_id>/manifest.json` | Run metadata and artifact list |
| `results/runs/<run_id>/suggested_overrides.json` | LLM draft from that run's failures (when generated) |
| `results/latest.json` | Pointer to the most recent run |
| `results/index.json` | Newest-first list of recent runs with pass/fail counts |
| `results/latest_summary.md` | Copy of the latest run summary (backward compatible) |
| `results/latest_summary.json` | Copy of the latest run JSON (backward compatible) |
| `results/suggested_overrides.json` | Copy of the latest suggestion draft (backward compatible) |

List recent runs:

```bash
uv run python run_evals.py --list-runs
```

Other files may appear under `results/` from optional tooling (audit logs, live description dumps, etc.) — those are not tied to a specific eval run.
