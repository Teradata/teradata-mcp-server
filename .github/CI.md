# CI/CD

## GitHub Actions Workflow

The CI workflow (`.github/workflows/ci.yml`) runs on every push to `main` and on pull requests targeting `main`. It consists of three parallel jobs:

### Jobs

| Job | What it does |
|-----|-------------|
| **Lint** | Runs `ruff check` and `ruff format --check` against `src/` |
| **Type Check** | Runs `mypy` against `src/` (installs the `dev` extra for type stubs) |
| **Integration Tests** | Runs the test suite against a live Teradata database |

All jobs use `uv sync --frozen` to ensure the lock file is up to date — if `uv.lock` is stale relative to `pyproject.toml`, the job will fail.

### Running Checks Locally

```bash
# Lint
uv run ruff check src/
uv run ruff format --check src/

# Type check
uv sync --extra dev
uv run mypy src/

# Integration tests (requires a live Teradata connection)
export DATABASE_URI="teradata://user:pass@host:1025/database"
uv run python tests/run_mcp_tests.py "uv run teradata-mcp-server"
```

### Configuring the `DATABASE_URI` Secret

The integration test job requires a `DATABASE_URI` repository secret to connect to a Teradata instance. Without it, the test job logs a warning and skips.

To configure:

1. Go to **Settings > Secrets and variables > Actions** in the GitHub repository
2. Click **New repository secret**
3. Name: `DATABASE_URI`
4. Value: a Teradata connection URI, e.g. `teradata://user:pass@host:1025/database`

You need to be on the Teradata VPN to access the test database, so this secret should only be added by authorized Teradata personnel. If you don't have access, the tests will simply be skipped.

The test job is automatically skipped on fork PRs (where secrets are unavailable) to avoid failures.

### Concurrency

The workflow uses concurrency groups scoped to the branch/PR ref. If a new commit is pushed while a previous run is still in progress, the older run is cancelled to save CI minutes and avoid database contention.
