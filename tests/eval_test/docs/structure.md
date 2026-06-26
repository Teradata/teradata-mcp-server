# Project structure

```
teradata-mcp-evals/
  agent/
    client.py              # MCP agent; optional description overrides (opt-in)
  judge/
    bedrock_llm.py         # Bedrock wrapper for deepeval judge
    checks.py              # Deterministic structural checks
    metrics.py             # ToolCorrectnessMetric + clarification GEval
    report.py              # Eval summaries → results/
    suggest_overrides.py   # LLM draft overrides (library)
  cases/
    *.json                 # Eval cases per MCP module prefix
  tests/
    conftest.py            # Fixtures, {EVALS_DATABASE} substitution
    case_runner.py         # Case execution and scoring
    test_<module>.py       # One pytest file per module
    test_checks.py         # Unit tests — deterministic checks
    test_multi_turn.py     # Unit tests — multi-turn schema
    test_report.py         # Unit tests — eval summaries
    test_suggest_overrides.py
    test_description_overrides.py
  docs/                    # Extended documentation
  backup/                  # Optional bootstrap/audit scripts
  run_evals.py             # CLI entry point
  suggest_overrides.py     # CLI — draft description overrides
  setup_test_data.py
  preflight.py
  teardown_test_data.py
  pyproject.toml
  .env.example
```

Optional scripts in [`backup/`](../backup/README.md) are not required for the main eval workflow.
