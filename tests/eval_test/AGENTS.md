# PROJECT KNOWLEDGE BASE

**Updated:** 2026-06-23

## OVERVIEW

**Project:** teradata-mcp-evals

**Purpose:** Eval suite for the [Teradata MCP Server](https://github.com/Teradata/teradata-mcp-server) community edition. Primary goal is **MCP tool description quality** — tests whether an LLM agent selects the right tool and forms valid parameters from natural language. Failures on `ambiguous_selection` cases usually indicate overlapping or unclear tool descriptions in the MCP server.

**Stack:**
- **Language:** Python ≥ 3.11
- **Package manager / build tool:** `uv` (recommended) or standard `venv` + `pip`
- **Core dependencies:**
  - `deepeval>=1.4.0`
  - `mcp>=1.0.0`
  - `boto3>=1.34.0`
  - `python-dotenv>=1.0.0`
  - `pytest>=8.0.0`
  - `pytest-asyncio>=0.23.0`
  - `teradatasql>=20.0.0`
- **Auxiliary tools:** `uv`, `dotenv`, deepeval CLI, `teradatasql` driver, AWS Bedrock (Claude) for agent + judge LLM calls

**Case types:**

| Type | Purpose |
|------|---------|
| `happy_path` | Unambiguous prompt → correct tool + params |
| `ambiguous_selection` | Two tools could apply → tests description distinctness |
| `missing_parameter` | Vague prompt → agent must ask, not hallucinate |
| `multi_tool` | Chained tool calls in order |
| `multi_turn` (optional) | 2–7 turns: clarify first, then correct tool after user supplies info |

**Module priority:** P0 `base` · P1 `dba`, `sec` · P2 `qlty` · maintained `chat`, `plot`, `tmpl`

## STRUCTURE

```
agent/
  client.py           # MCP agent; optional description_overrides (opt-in)
judge/
  bedrock_llm.py      # DeepEvalBaseLLM wrapper for Bedrock Converse API
  checks.py           # Deterministic structural checks (fail before LLM judge)
  metrics.py          # ToolCorrectnessMetric + Clarification GEval
  report.py           # Eval summaries → results/latest_summary.*
  suggest_overrides.py # LLM draft overrides from failed ambiguous_selection cases
cases/
  <module>.json       # Eval case definitions per MCP module prefix
tests/
  conftest.py          # Fixtures, _substitute() helper, wrapper functions for eval case execution
  case_runner.py       # Single/multi-turn execution and per-turn scoring (raw functions)
  generated_cases.py   # Dynamically generates pytest tests from JSON case definitions
  test_generated_cases.py # Exposes generated tests to pytest discovery
  test_checks.py       # Unit tests for judge/checks.py
  test_multi_turn.py   # Unit tests for multi-turn schema validation
backup/               # Optional bootstrap/audit scripts — see backup/README.md
run_evals.py          # CLI entry point (deepeval + pytest)
suggest_overrides.py  # CLI: draft description_overrides from eval failures
setup_test_data.py    # Create evals_employees / evals_orders in EVALS_DATABASE
preflight.py          # Verify eval tables exist before live eval runs
teardown_test_data.py
docs/                 # Extended user documentation
README.md             # Quick start and doc index
.env.example          # Required environment variables
pyproject.toml        # Project metadata, Ruff config, pytest paths
```

## COMMANDS

| Action | Command |
|--------|---------|
| **Install dependencies** (recommended) | `curl -LsSf https://astral.sh/uv/install.sh \| sh && uv venv && uv sync` |
| **Install dependencies** (standard) | `python3 -m venv .venv && source .venv/bin/activate && pip install -e .` |
| **Run test data setup** | `python setup_test_data.py` (or `uv run python setup_test_data.py`) |
| **Verify eval tables** | `python preflight.py` (also runs automatically via `run_evals.py`) |
| **Generate happy-path cases** | `uv run python backup/generate_cases.py` |
| **Regenerate after description change** | `uv run python backup/generate_cases.py --module base --overwrite` |
| **Audit ambiguous pair coverage** | `uv run python backup/audit_cases.py --strict` |
| **Audit against live MCP tools** | `uv run python backup/audit_cases.py --live-mcp --strict` |
| **List eval runs** | `uv run python run_evals.py --list-runs` |
| **Suggest description overrides** | `uv run python suggest_overrides.py` (after baseline eval) |
| **Apply description overrides** | `uv run python suggest_overrides.py --apply` (after reviewing draft) |
| **Test description overrides** | `uv run python run_evals.py --with-description-overrides` |
| **Unit tests (local)** | `uv run pytest tests/test_checks.py tests/test_multi_turn.py tests/test_report.py tests/test_suggest_overrides.py tests/test_description_overrides.py -v` |
| **Run full eval suite** | `python run_evals.py` (or `uv run python run_evals.py`) |
| **Run one module** | `python run_evals.py --module base` |
| **Filter by case type** | `python run_evals.py --module base --type ambiguous_selection` |
| **Run multi-turn cases only** | `python run_evals.py --module base --type multi_turn` |
| **Verbose output** | `python run_evals.py --verbose` |
| **Unit tests (no MCP/Bedrock)** | `uv run pytest tests/test_checks.py tests/test_multi_turn.py tests/test_report.py tests/test_suggest_overrides.py tests/test_description_overrides.py` |
| **Run tests directly (pytest)** | `pytest` (or `uv run pytest`) |
| **Tear down test data** | `python teardown_test_data.py` |
| **Package script** | `run-evals` (installed via `[project.scripts]` in `pyproject.toml`) |

### `--type` filter keywords (maps to pytest `-k` on case IDs)

| `--type` | Matches IDs containing |
|----------|------------------------|
| `happy_path` | `happy` |
| `ambiguous_selection` | `ambiguous` |
| `missing_parameter` | `missing` |
| `multi_tool` | `multi_tool` |
| `multi_turn` | `clarify_then_call` |

## CODING STANDARDS

- **Language:** Python 3.11+ with full type hints (`typing`, `dataclasses`).
- **Style:** PEP 8; line length 120 (Ruff in `pyproject.toml`).
- **Docstrings:** Triple-quoted module- and function-level docstrings.
- **Error handling:** Exceptions caught and surfaced as readable messages (e.g. tool errors in `agent/client.py`).
- **Configuration:** `python-dotenv`; secrets in `.env` (never commit). Key vars:
  - `MCP_SERVER_URL`, `EVALS_DATABASE`, `BEDROCK_MODEL_ID`
  - `BEDROCK_JUDGE_MODEL_ID` (optional, defaults to agent model)
  - `USE_DESCRIPTION_OVERRIDES` / `DESCRIPTION_OVERRIDES_FILE` (optional — default evals use live MCP descriptions)
  - `AGENT_MAX_STEPS` (default 5, single-turn)
  - `AGENT_MAX_STEPS_PER_TURN` (default 3, multi-turn)
- **Testing:** Pytest + DeepEval for integration evals; pure unit tests for `judge/checks.py` and schema validation without Bedrock/MCP.

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Agent loop / MCP session | `agent/client.py` |
| Deterministic checks | `judge/checks.py` |
| LLM judge metrics | `judge/metrics.py` |
| Dynamic test generation from JSON | `tests/generated_cases.py` → `_register_module_tests()` |
| Run + score any case (raw) | `tests/case_runner.py` → `assert_eval_case()` |
| Eval run summaries | `judge/report.py` → `results/runs/<run_id>/` + `results/latest.json` |
| List recent runs | `run_evals.py --list-runs` |
| Override suggestions | `suggest_overrides.py` → run's `suggested_overrides.json` |
| Apply override draft | `suggest_overrides.py --apply` → `description_overrides.json` |
| Apply overrides during evals | `description_overrides.json` + `--with-description-overrides` (`agent/client.py`) |
| Case JSON definitions | `cases/<module>.json` |
| Ambiguous pair registry / live MCP diff | `backup/audit_cases.py` → `AMBIGUOUS_PAIRS`, `--live-mcp` |
| Happy-path generator | `backup/generate_cases.py` |
| Test data setup / preflight | `setup_test_data.py`, `preflight.py` |
| `{EVALS_DATABASE}` substitution (runtime) | `tests/generated_cases.py` → `_register_module_tests()` calls `_substitute()` from conftest before execution |
| User-facing docs | `README.md`, `docs/` |

## EVAL FLOW

**Description quality loop** (see `docs/workflow.md`):

1. Baseline: `run_evals.py` — agent uses live MCP descriptions.
2. Summary: `judge/report.py` writes `results/runs/<run_id>/` and updates `results/latest.json`.
3. Draft: `suggest_overrides.py` — LLM rewrites for failed `ambiguous_selection` cases.
4. Test: `suggest_overrides.py --apply`, then re-run with `--with-description-overrides`.
5. Ship: promote to MCP server, re-run baseline.

**Per-case scoring:**

1. Pytest discovers parametrized tests from `tests/generated_cases.py` → `_register_module_tests()`.
2. Each parametrized test loads a case from `cases/<module>.json` and filters by `EVALS_RUN_MODULE` / `EVALS_RUN_TYPE` env vars.
3. `{EVALS_DATABASE}` placeholder substituted at runtime via `_substitute()` from `conftest.py` before execution.
4. **Single-turn:** `run_agent()` → deterministic checks → deepeval metrics.
5. **Multi-turn:** `run_agent_turns()` (one MCP session, max 7 turns) → per-turn checks:
   - Clarification turns: no tools + Clarification GEval
   - Tool turns: deterministic checks + ToolCorrectnessMetric
6. Structural failures in `judge/checks.py` raise `AssertionError` before the judge runs.
7. Outcomes recorded under `results/runs/<run_id>/` via `judge/report.py`.

## CASE JSON CONVENTIONS

**Single-turn:** top-level `input`, `type`, `expected_tools`.

**Multi-turn:** top-level `turns` (2–7 entries), each with `input` and exactly one of:
- `"expect": "clarification"`
- `"expected_tools": [...]`

Multi-turn case IDs should contain `clarify_then_call` for `--type multi_turn` filtering.

Param names in `expected_tools` must match live MCP schemas (e.g. `sql` for `base_readQuery`, `user_name` for sec tools). Use `{EVALS_DATABASE}.evals_*` tables for deterministic grounding in base, qlty, plot, and dba cases where applicable.

## MCP DESCRIPTION CHURN WORKFLOW

When a tool description changes in the MCP server:

1. `backup/generate_cases.py --module <m> --overwrite` for happy paths (optional)
2. Manually review `ambiguous_selection` cases in that module
3. `backup/audit_cases.py --module <m> --strict` (optional)
4. Run baseline evals; use `suggest_overrides.py` on failures; test with `--with-description-overrides`
5. Promote accepted wording to the MCP server repo; re-run baseline evals
6. Add new tool pairs to `AMBIGUOUS_PAIRS` in `backup/audit_cases.py` when overlap is discovered

## NOTES

- Requires running **Teradata MCP Server** at `MCP_SERVER_URL` and **ClearScape** database `EVALS_DATABASE` with demo tables from `setup_test_data.py`.
- AWS Bedrock credentials via standard boto3 chain. Default model: `anthropic.claude-3-5-sonnet-20241022-v2:0`.
- Eval results stored in `results/` (not committed). Each run gets `results/runs/<run_id>/` with summary, manifest, and optional suggestion draft. `results/latest.json` points at the newest run; `results/index.json` lists recent runs.
- Do not commit `.env` or credentials.
- Hand-author edge cases (`ambiguous_selection`, `missing_parameter`, `multi_tool`, `multi_turn`) after generating happy paths — generator cannot replace human judgement on description boundaries.
- Prompt vocabulary should differ from tool descriptions (same rule enforced in `backup/generate_cases.py` DRAFT_PROMPT).
