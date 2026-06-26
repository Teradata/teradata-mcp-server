# Cases & scoring

## What case types test

| Type | What it catches |
|---|---|
| `happy_path` | Agent picks the right tool with correct params |
| `ambiguous_selection` | Two tools could apply — descriptions must be distinct |
| `missing_parameter` | Agent must ask for clarification, not hallucinate |
| `multi_tool` | Chained tool calls in order |
| `multi_turn` | Shallow dialog — clarify first, then call the right tool (2–7 turns) |

**Priority modules:** `base`, `dba`, `sec`, `qlty` · **Maintained:** `chat`, `plot`, `tmpl`

Cases live in `cases/<module>.json`.

## Single-turn format

```json
{
  "id": "base_readQuery_happy",
  "type": "happy_path",
  "description": "What this tests",
  "input": "The natural language prompt sent to the agent",
  "expected_tools": [
    {
      "name": "base_readQuery",
      "params": { "sql": "SELECT * FROM {EVALS_DATABASE}.evals_employees SAMPLE 10" }
    }
  ]
}
```

- `missing_parameter`: set `expected_tools` to `[]`
- `multi_tool`: list expected tool calls in order
- Param names must match live MCP schemas (e.g. `sql` for `base_readQuery`)

## Multi-turn format (optional)

Use a `turns` array instead of top-level `input` / `expected_tools`. Scored in one MCP session. **2–7 turns.**

```json
{
  "id": "base_tablePreview_clarify_then_call",
  "type": "missing_parameter",
  "description": "Agent asks which table, then previews after user clarifies",
  "turns": [
    { "input": "Preview some rows for me", "expect": "clarification" },
    {
      "input": "Preview rows from {EVALS_DATABASE}.evals_employees",
      "expected_tools": [
        {
          "name": "base_tablePreview",
          "params": {
            "database_name": "{EVALS_DATABASE}",
            "table_name": "evals_employees"
          }
        }
      ]
    }
  ]
}
```

Each turn sets **exactly one** of `"expect": "clarification"` or non-empty `"expected_tools"`. IDs should contain `clarify_then_call` for `--type multi_turn` filtering.

## Scoring

Deterministic checks run first (`judge/checks.py`), then LLM judge metrics where needed.

### Deterministic checks

| Check | Applies to |
|---|---|
| No tool calls | `missing_parameter` and clarification turns |
| Exact tool name | Primary tool on happy/ambiguous; all tools on `multi_tool` |
| Exact param values | `database_name`, `table_name`, `column_name`, `user_name`, `role_name` |
| Param key presence | `sql` / `query` — key required; value judged by LLM |

Structural failures fail immediately without invoking the judge.

### LLM judge metrics

| Metric | Applies to |
|---|---|
| `ToolCorrectnessMetric` | Cases with `expected_tools` |
| `Clarification Check` (GEval) | `missing_parameter` and clarification turns |

## Adding cases for a new tool

1. Add a `happy_path` case (or use [`backup/generate_cases.py`](../backup/README.md) to draft from live descriptions).
2. Add `ambiguous_selection` — overlapping tool pair, prompt that could call either, `expected_tools` set to the winner.
3. Add `missing_parameter` — vague prompt, `expected_tools: []`.
4. Optionally add `multi_turn` or `multi_tool` cases.
5. Optionally run [`backup/audit_cases.py`](../backup/README.md) for pair coverage.

Use vocabulary **different from tool descriptions** — evals stress-test routing, not parrot descriptions.
