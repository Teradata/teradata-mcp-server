# teradata-mcp-evals

Eval suite for the [Teradata MCP Server](https://github.com/Teradata/teradata-mcp-server) community edition.

Tests whether an LLM agent selects the right MCP tool and forms valid parameters from natural language. The primary goal is **MCP tool description quality** — routing failures on `ambiguous_selection` cases usually mean overlapping or unclear descriptions. Uses [deepeval](https://github.com/confident-ai/deepeval) and Claude on AWS Bedrock as agent and judge.

## Quick start

**Pre-requisite:** ensure that the MCP Server is running in a separate process and reachable in streamable-http.

Eg. `teradata-mcp-server --mcp_port 8001 --mcp_transport streamable-http` 


```bash
uv venv && uv sync
cp .env.example .env   # set MCP_SERVER_URL, EVALS_DATABASE, Bedrock credentials

python setup_test_data.py
python run_evals.py --module base
```

Open `results/latest_summary.md` for pass/fail details and aggregate Bedrock token usage, or run `python run_evals.py --list-runs` to browse run directories. `summary.json` also includes per-case `token_usage` plus run-level totals; set the optional `BEDROCK_AGENT_*_COST_PER_1M_TOKENS` and `BEDROCK_JUDGE_*_COST_PER_1M_TOKENS` env vars to add USD cost reporting.

To compare several evaluated models with the same judge, put the model set in YAML and run:

```bash
python run_evals.py --module base --model-set model_set.yml
```

When the YAML contains multiple evaluated models, the runner writes one normal run per model plus `results/latest_batch_summary.md` with links, pass ratios, token totals, and cost comparison. With one evaluated model, it behaves like the regular single-run path while taking model IDs and costs from YAML.

## Workflow

Baseline evals use **live MCP descriptions**. To iterate on wording before changing the server:

1. `run_evals.py` — baseline
2. `suggest_overrides.py` — LLM draft for failed cases
3. `suggest_overrides.py --apply` — merge reviewed draft into `description_overrides.json`
4. `run_evals.py --with-description-overrides` — test locally
5. Promote to MCP server → baseline again

Full diagram, commands, and results files: **[docs/workflow.md](docs/workflow.md)**

## Documentation

| Doc | Contents |
|---|---|
| [docs/setup.md](docs/setup.md) | Install, `.env`, test data, unit tests |
| [docs/workflow.md](docs/workflow.md) | Running evals, overrides, results |
| [docs/cases.md](docs/cases.md) | Case types, JSON format, scoring, adding cases |
| [docs/structure.md](docs/structure.md) | Repository layout |
| [backup/README.md](backup/README.md) | Optional case generation and audit scripts |
