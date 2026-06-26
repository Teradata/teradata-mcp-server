# Setup

## Prerequisites

- Python 3.11+
- Teradata MCP Server running at `http://127.0.0.1:8001` connected to a ClearScape Analytics Experience instance
- AWS account with Bedrock access to an Anthropic Claude model

## Install

### Option A — uv (recommended)

[uv](https://docs.astral.sh/uv/) manages the virtual environment automatically.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

git clone <this-repo>
cd teradata-mcp-evals

uv venv
uv sync
cp .env.example .env
```

With the venv active you can call scripts directly (`python run_evals.py`). Alternatively, prefix commands with `uv run`.

### Option B — standard venv + pip

```bash
git clone <this-repo>
cd teradata-mcp-evals

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

## Environment variables

Edit `.env`:

```dotenv
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# Optional — defaults to BEDROCK_MODEL_ID
# BEDROCK_JUDGE_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# Optional — used only for USD cost reporting. Token usage is captured without these.
# Values are USD per 1M tokens. Use prices for your exact Bedrock model and region.
# BEDROCK_AGENT_INPUT_COST_PER_1M_TOKENS=3.00
# BEDROCK_AGENT_OUTPUT_COST_PER_1M_TOKENS=15.00
# BEDROCK_AGENT_CACHE_READ_INPUT_COST_PER_1M_TOKENS=0.30
# BEDROCK_AGENT_CACHE_WRITE_INPUT_COST_PER_1M_TOKENS=3.75
# BEDROCK_JUDGE_INPUT_COST_PER_1M_TOKENS=3.00
# BEDROCK_JUDGE_OUTPUT_COST_PER_1M_TOKENS=15.00
# BEDROCK_JUDGE_CACHE_READ_INPUT_COST_PER_1M_TOKENS=0.30
# BEDROCK_JUDGE_CACHE_WRITE_INPUT_COST_PER_1M_TOKENS=3.75

MCP_SERVER_URL=http://127.0.0.1:8001/mcp
EVALS_DATABASE=your_database_name

AGENT_MAX_STEPS=5
AGENT_MAX_STEPS_PER_TURN=3

# Optional — only when testing description overrides (see docs/workflow.md)
# USE_DESCRIPTION_OVERRIDES=1
# DESCRIPTION_OVERRIDES_FILE=description_overrides.json
```

Credentials follow the standard boto3 chain — env vars, `~/.aws/credentials`, or an IAM instance profile. Set `AWS_SESSION_TOKEN` for temporary credentials.

The report always records Bedrock token usage by model and role (`agent` / `judge`) with input, output, cache-read input, cache-write input, and total token counts. Cost fields remain `null` / “not configured” until pricing env vars are set. Per-1K aliases are also accepted by replacing `PER_1M` with `PER_1K`.

## Multi-model batches

Use `--model-set` when you want the model IDs and cost parameters to come from YAML instead of `.env`:

```yaml
name: bedrock-model-comparison
judge:
  model: anthropic.claude-3-5-sonnet-20241022-v2:0
  cost:
    input_cost_per_1m_tokens: 3.00
    output_cost_per_1m_tokens: 15.00
    cache_read_input_cost_per_1m_tokens: 0.30
    cache_write_input_cost_per_1m_tokens: 3.75
models:
  - label: sonnet
    model: anthropic.claude-3-5-sonnet-20241022-v2:0
    cost:
      input_cost_per_1m_tokens: 3.00
      output_cost_per_1m_tokens: 15.00
  - label: haiku
    model: anthropic.claude-3-5-haiku-20241022-v1:0
    cost:
      input_cost_per_1m_tokens: 0.80
      output_cost_per_1m_tokens: 4.00
```

Run the same case filters as usual:

```bash
python run_evals.py --module base --model-set model_set.yml
```

The YAML keys `evaluated_models` and `models` are both accepted for the evaluated model list. Each run still produces `results/runs/<run_id>/summary.md`; when more than one model is listed, the batch also writes `results/latest_batch_summary.md` and `results/batches/<batch_id>/summary.md` with pass ratio and cost comparisons.

## Test data

Create eval tables once before running live evals:

```bash
python setup_test_data.py
```

| Table | Purpose |
|---|---|
| `evals_employees` | Used by base, qlty, plot cases |
| `evals_orders` | Used by base, qlty, plot, dba cases (includes nullable `ship_date`, negative `amount`) |

Set `EVALS_DATABASE` to the database where tables are created — usually your ClearScape username. Case JSON uses `{EVALS_DATABASE}` as a runtime placeholder.

```bash
python teardown_test_data.py           # clean up
python setup_test_data.py --drop-first # recreate from scratch
python preflight.py                      # verify tables exist (also run by run_evals.py)
```

## Unit tests

No MCP server or Bedrock required:

```bash
uv run pytest tests/test_checks.py tests/test_multi_turn.py tests/test_report.py \
  tests/test_suggest_overrides.py tests/test_description_overrides.py -v
```
