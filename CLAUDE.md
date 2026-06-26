# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Teradata MCP Server — a Model Context Protocol server for interacting with Teradata databases. Built on FastMCP, distributed on PyPI as `teradata-mcp-server`. Python 3.11+.

## Build & Development Commands

```bash
# Install dependencies
uv sync

# Install with optional modules
uv sync --extra fs       # Feature Store (teradataml)
uv sync --extra tdvs     # Vector Store (teradatagenai)
uv sync --extra bar      # Backup & Restore
uv sync --extra dev      # Dev tools (ruff, mypy)

# Run the server locally (stdio mode)
uv run teradata-mcp-server --database_uri "teradata://user:pass@host:1025/db"

# Run with specific profile and transport
uv run teradata-mcp-server --profile dba --mcp_transport streamable-http --mcp_port 8001

# Lint
uv run ruff check src/
uv run ruff format --check src/

# Type check
uv run mypy src/

# Run tests (requires a live Teradata connection)
export DATABASE_URI="teradata://user:pass@host:1025/database"
uv run python tests/integration/run_mcp_tests.py "uv run teradata-mcp-server"

# Docker
docker compose up teradata-mcp-server
```

## Architecture

### Request Flow

1. **`server.py`** — CLI argument parsing, calls `create_mcp_app()`
2. **`app.py`** — FastMCP app factory. Creates the MCP instance, registers tools/prompts/resources based on profile, configures middleware. A `teradata_lifespan` async context manager (passed to `FastMCP(lifespan=...)`) owns the `TDConn` pool lifecycle: creates the pool at server startup and calls `engine.dispose()` in its `finally` block on shutdown.
3. **`middleware.py`** — `RequestContextMiddleware` extracts per-request headers, auth, and session info. Sets Teradata QueryBand for tracing
4. **Tool handlers** — Plain sync functions (`handle_*`) in `tools/` subdirectories. Wrapped to async via `asyncio.to_thread`

### Profile-Based Module Loading

Tools are organized into domain modules under `src/teradata_mcp_server/tools/`:
- **base/** — Core queries (readQuery, tableList, columnDescription, etc.)
- **dba/** — Administration & monitoring
- **sec/** — Security & permissions
- **rag/** — Retrieval-augmented generation workflows
- **fs/** — Feature Store (optional, requires teradataml)
- **tdvs/** — Vector Store operations
- **bar/** — Backup & restore (optional)
- **chat/** — Chat completion
- **qlty/** — Data quality / EDA
- **plot/** — Visualization (charts)
- **sql_opt/** — SQL optimization
- **tmpl/** — Template tools

Profiles (defined in `config/profiles.yml`) control which modules load. The `module_loader.py` uses regex pattern matching against tool name prefixes to determine which modules to import. Available profiles: `all`, `dba`, `dataScientist`, `eda`, `bar`, `llmUser`, `tester`.

### teradataml Analytic Function Tools (`tdml_*`)

The ~89 `tdml_*` tools (e.g., `tdml_KMeans`, `tdml_XGBoost`) are registered dynamically in `app.py`, separate from the `handle_*` module pattern. Key files:

- **`tools/constants.py`** — `TD_ANALYTIC_FUNCS`: a `dict[str, str]` mapping teradataml function name → curated one-line summary. This is the authoritative list of which functions to register. To add a new function, add one entry here.
- **`tools/utils/__init__.py`** — `build_tdml_tool_docstring(summary, func_metadata, partition_order_cols)`: builds the compact MCP tool description at registration time by reading parameter names, descriptions, and types from the live teradataml JSON store.

Tools are registered inside `teradata_lifespan` at server startup (after the DB connection and teradataml context are confirmed). This means `tdml_*` tools become available once the lifespan completes, not at factory time. Functions missing from the connected system are skipped with a warning.

### Configuration System

Layered config loading (`config_loader.py`):
1. Packaged defaults from `src/teradata_mcp_server/config/*.yml`
2. User overrides from working directory or `CONFIG_DIR` env var

Settings dataclass in `config/__init__.py` merges CLI args, environment variables, and defaults.

### Database Connectivity

`TDConn` class in `tools/td_connect.py` manages SQLAlchemy engine creation for Teradata. Supports connection pooling (`TD_POOL_SIZE`, `TD_MAX_OVERFLOW`, `TD_POOL_TIMEOUT`), auth modes (TD2, LDAP via `LOGMECH`), and rate-limited authentication.

The `TDConn` instance is created inside the `teradata_lifespan` context manager in `app.py` and stored in a `_ConnState` holder (`_state.tdconn`). This guarantees `engine.dispose()` runs on server shutdown. If `DATABASE_URI` is not set, `TDConn` sets `engine = None` and the server starts without a database (tools will raise at invocation time).

Tool handlers receive either a SQLAlchemy `Connection` or raw `TeradataConnection` as their first parameter — the wrapper in `app.py` handles injection.

`base_readQuery` caps result rows to prevent LLM token overflow: default 1000 rows, hard ceiling 50000. Configurable via `DEFAULT_ROW_LIMIT` and `MAX_ROW_LIMIT` env vars. When truncated, response metadata includes `truncated: true`; callers can pass a higher `row_limit` or use `persist=true` to bypass the cap.

### Transport Modes

Set via `MCP_TRANSPORT` env var or `--mcp_transport` flag:
- **stdio** (default) — for Claude Desktop and CLI clients
- **streamable-http** — HTTP with streaming on configurable host/port
- **sse** — Server-Sent Events, this will be merged into streamable-http as the MCP standard is depricating SSE as a separate transport

For stdio transport, logs go to file only (to avoid polluting MCP stdout). Log locations: macOS `~/Library/Logs/TeradataMCP/`, Linux `~/.local/state/teradata_mcp_server/logs/`.

### Testing

Tests require a live Teradata database. Test cases are JSON files in `tests/integration/cases/` (e.g., `core_test_cases.json`). The test runner (`tests/integration/run_mcp_tests.py`) dynamically discovers available tools and only runs matching test cases. Results are saved as timestamped JSON in `var/test-reports/`.

## Code Conventions

- **Ruff** for linting/formatting: line length 120, target py311, rules: E, W, F, I, N, B, UP, C4, SIM, PIE, PL
- Tool handler functions are named `handle_<tool_name>` and stay synchronous
- Tool names are prefixed by module: `base_*`, `dba_*`, `sec_*`, `rag_*`, etc.
- Structured JSON logging via `CustomJSONFormatter` in `utils.py`
