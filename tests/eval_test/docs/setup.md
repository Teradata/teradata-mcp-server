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

MCP_SERVER_URL=http://127.0.0.1:8001/mcp
EVALS_DATABASE=your_database_name

AGENT_MAX_STEPS=5
AGENT_MAX_STEPS_PER_TURN=3

# Optional — only when testing description overrides (see docs/workflow.md)
# USE_DESCRIPTION_OVERRIDES=1
# DESCRIPTION_OVERRIDES_FILE=description_overrides.json
```

Credentials follow the standard boto3 chain — env vars, `~/.aws/credentials`, or an IAM instance profile. Set `AWS_SESSION_TOKEN` for temporary credentials.

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
