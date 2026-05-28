# Development Conventions

> **📍 Navigation:** [Documentation Home](../README.md) | [Server Guide](../README.md#-server-guide) | [Getting started](../server_guide/GETTING_STARTED.md) | [Architecture](../server_guide/ARCHITECTURE.md) | [Installation](../server_guide/INSTALLATION.md) | [Configuration](../server_guide/CONFIGURATION.md) | [Security](../server_guide/SECURITY.md) | [Customization](../server_guide/CUSTOMIZING.md) | [Client Guide](../client_guide/CLIENT_GUIDE.md) 

This document provides guidelines for developing new tools for the Teradata MCP server.
<br>

## Quick Setup (uv recommended)

We standardize on **uv** for development: fast installs, reproducible envs, no global pollution.

### 1) Install uv
- **macOS:** `brew install uv`
- **Windows:** `winget install astral-sh.uv`

### 2) Clone and bootstrap
```bash
git clone https://github.com/<your-org>/teradata-mcp-server.git
cd teradata-mcp-server
uv python install            # ensure a compatible Python is available
uv sync                      # create venv and install project deps
```

> Tip: add extras for full dev (feature store, tdvs) if you use them:
```bash
uv sync --extra fs --extra tdvs
```

### 3) Run the server from source
```bash
uv run teradata-mcp-server --profile all
```

### 4) MCP Inspector (interactive testing)
```bash
npx modelcontextprotocol/inspector uv run teradata-mcp-server
```

### 5) Run tests

Always run the full pre-push checklist before submitting a PR. Run steps in order — the fast checks come first so you fail early.

```bash
# 1. Lint (no database required)
uv run ruff check src/
uv run ruff format --check src/

# 2. Type check (no database required)
uv sync --extra dev
uv run mypy src/

# 3. HTTP transport smoke test (no database required)
#    Catches startup-time errors in HTTP-specific code paths (middleware,
#    imports, constructor errors) that the stdio suite cannot reach.
uv run python tests/smoke_http.py --verbose

# 4. Integration tests — stdio (requires DATABASE_URI)
export DATABASE_URI="teradata://user:pass@host:1025/database"
uv run python tests/run_mcp_tests.py "uv run teradata-mcp-server"

# 5. Integration tests — streamable-http (requires DATABASE_URI)
uv run python tests/run_mcp_tests.py "uv run teradata-mcp-server" --transport streamable-http
```

Steps 1–3 have no database dependency and are quick — run them on every change. Steps 4–5 require VPN and credentials; run them when you have changed tool handlers, middleware, or connection logic.

Most users use the MCP server with Claude over stdio, so always test Claude's behaviour with your code or build before pushing it.

Example configurations:
```json
"teradata_dev": {
  "command": "uv",
  "args": [
    "--directory",
    "/Users/remi.turpaud/Code/genAI/teradata-mcp-server",
    "run",
    "teradata-mcp-server"
  ],
  "env": {
"DATABASE_URI": "teradata://user:password@system.clearscape.teradata.com:1025/user",
"MCP_TRANSPORT": "stdio"
  }
}

"teradata_build": {
  "command": "/opt/homebrew/bin/uvx",
  "args": [
    "path_to_code/teradata-mcp-server/dist/teradata_mcp_server-0.1.3-py3-none-any.whl",
    "python", "-m", "teradata_mcp_server",
    "--profile", "all"
  ],
  "env": {
    "DATABASE_URI": "teradata://user:password@system.clearscape.teradata.com:1025/user",
    "MCP_TRANSPORT": "stdio"
  }
}
```



### 6) Troubleshooting (dev)
- GUI apps (e.g., Claude) have a different PATH. Prefer `uv --directory … run …` or `uvx` in configs.
- Clear caches when testing or installing fresh builds/uploads: `uv cache clean` or run with `--no-cache`.


## Directory Structure & File Naming

The directory structure will follow the following conventions
[root directory](./) - will contain:
- README.md - this will be the main readme file, outlining scope of project, grouping of tools, installation instructions, how to use instructions.
- LICENSE file - MIT license
- pyproject.toml - Project metadata
- uv.lock - uv package lock file contains detailed package information
- .gitignore - list of files and directories that should not be loaded into github
- .python-version - python version
- env - example environments file
- profiles.yml - default profiles for development (external to package)
- custom_objects.yml - example custom tools/prompts definitions (external to package)
- *_objects.yml - additional custom object definitions (external to package)

[logs directory](./logs/) – (legacy note) we do **not** write logs to the current working directory by default. For CLI runs, logs go to a per‑user location (e.g., `~/Library/Logs/TeradataMCP` on macOS). When used via stdio (e.g., Claude Desktop), file logging is disabled by default to keep stdout clean; you can override with `LOG_DIR`.

[src/teradata_mcp_server](./src/teradata_mcp_server) - main server source code:
- `server.py`: slim entrypoint. Parses CLI/env into `Settings`, builds the app via `create_mcp_app`, and runs the selected transport.
- `app.py`: application factory. Sets up logging, middleware, adapters, loads tools/prompts/resources from code and YAML, and returns a configured `FastMCP` app.
- `config.py`: `Settings` dataclass and `settings_from_env()` for centralized configuration (single source of truth; precedence is CLI > env > defaults).
- `utils.py` (logging): structured logging setup (stdio‑safe) and JSON formatter.
- `middleware.py`: shared `RequestContextMiddleware` that extracts per-request context; has a stdio fast-path (no headers/auth) and a full HTTP/SSE path that can enforce auth and cache.
- MCP adapter (inlined in `app.py`): internal `execute_db_tool` (DB connection injection, QueryBand, raises `ToolError` on failure) and `make_tool_wrapper` (auto MCP wrapper for `handle_*` functions). `ErrorHandlingMiddleware` with `mask_error_details=True` ensures raw SQL errors and stack traces are never forwarded to LLM clients.
- `tools/utils/queryband.py`: pure helpers to build Teradata QueryBand strings from request context (protocol-agnostic).
- `utils.py`: configuration helpers for profiles and YAML object loading.
- `testing/`: testing framework and utilities.


[src/teradata_mcp_server/tools](./src/teradata_mcp_server/tools) - this will contain code to connect to the database as well as the modules.
- __init__.py - will contain tool module imports
- td_connect.py - contains the code responsible for connecting to Teradata.


We will modularize the tool sets so that users will have the ability to add the tool sets that they need to the server.  It is expected that groupings of tools will have a consistent naming convention so that they can be easily associated.  

[src/teradata_mcp_server/tools/base](./src/teradata_mcp_server/tools/base) - this will contain the base tool set:
- __init__.py - will contain library imports
- base_tools.py - will contain the tool handle code
- base_prompts.yml - will contain the object (e.g. prompts, etc) code
- base_resources.py - will contain the resource handle code
- README.md - will describe the tools, prompts, resources, and package dependencies

[src/teradata_mcp_server/tools/dba](./src/teradata_mcp_server/tools/dba) - this will contain DBA focused tools set:
- __init__.py - will contain library imports
- dba_tools.py - will contain the tool handle code
- dba_objects.yml - will contain the object (e.g. prompts, etc) code
- dba_resources.py - will contain the resource handle code
- README.md - will describe the tools, prompts, resources, and package dependencies

[src/teradata_mcp_server/tools/qlty](./src/teradata_mcp_server/tools/qlty) - this will contain data quality tool set:
- __init__.py - will contain library imports
- qlty_tools.py - will contain the tool handle code
- qlty_objects.yml - will contain the object (e.g. prompts, etc) code
- qlty_resources.py - will contain the resource handle code
- README.md - will describe the tools, prompts, resources, and package dependencies

[src/teradata_mcp_server/tools/sec](./src/teradata_mcp_server/tools/sec) - this will contain security tool set:
- __init__.py - will contain library imports
- sec_tools.py - will contain the tool handle code
- sec_objects.yml - will contain the object (e.g. prompts, etc) code
- sec_resources.py - will contain the resource handle code
- README.md - will describe the tools, prompts, resources, and package dependencies

[src/teradata_mcp_server/tools/fs](./src/teradata_mcp_server/tools/fs) - this will contain feature store (tdfs4ds package) tool set:
- __init__.py - will contain library imports
- fs_tools.py - will contain the tool handle code
- fs_prompts.py - will contain the prompt handle code
- fs_resources.py - will contain the resource handle code
- README.md - will describe the tools, prompts, resources, and package dependencies


[src/teradata_mcp_server/tools/rag](./src/teradata_mcp_server/tools/rag) - this will contain vector store tool set:
- __init__.py - will contain library imports
- rag_tools.py - will contain the tool handle code
- rag_prompts.py - will contain the prompt handle code
- rag_resources.py - will contain the resource handle code
- README.md - will describe the tools, prompts, resources, and package dependencies


**New tools sets**
New tool sets can be created in one of two ways:
1. Custom tools - this approach allows the custom_tools.yaml file to register allthe tool information.  This approach is suitable for tools that run predefined SQL against Teradata.
- using the custom_tools.yaml template 
- rename the the yaml file to the name of your tool set, ensuring that it ends in _tools.yaml
- ensure that the tool names correspond to the tool naming convention

2. New tool libraries - this approach does not require changing server wiring. Create a new module under `tools/<group>/` and implement functions beginning with `handle_...`. The app factory automatically discovers and registers them when enabled in `profiles.yml`.
- grouping name should start with up to 4 characters that describes the module function
- Template code can be found in:
[src/teradata_mcp_server/tools/tmpl](./src/teradata_mcp_server/tools/tmpl) - this will contain template tool set:
- __init__.py - will contain library imports
- tmpl_tools.py - will contain the tool handle code
- tmpl_prompts.py - will contain the prompt handle code
- tmpl_resources.py - will contain the resource handle code
- README.md - will describe the tools, prompts, resources, and package dependencies

The template code should be copied and prefixes for directory name and files should be modified to align to your grouping name.  Refer to other tool sets for examples.

[examples](./examples/) - contains various example configurations and client implementations.
- Configuration_Examples/ - example profiles.yml and custom objects YAML files
- Claude_Desktop_Config_Files/ - example Claude Desktop configuration files
- MCP_Client_Example/ - example MCP client implementations
- Simple_Agent/ - simple agent example
- MCP_VoiceClient/ - voice client example

[docs](./docs/) - contains package documentation.
- CHANGE_LOG.md - maintains the change log of releases.
- CLIENT_GUIDE.md - explains how to connect common clients to the server.
- CONTRIBUTING.md - guidelines for contributors
- GETTING_STARTED.md - explains how to get the server up and running
- SECURITY.md - explains how to register security issues

[docs/developer_guide](./docs/developer_guide) - contains developer package documentation.
- DEVELOPER_GUIDE.md - explains structural elements of the server for developers.
- HOW_TO_ADD_YOUR_FUNCTION.md - explains how to add tools to a module


<br>

## Configuration System

The server uses a **layered configuration system** that supports packaged defaults and user customizations. See the [Configuration Guide](../server_guide/CONFIGURATION.md) for complete user documentation.

### Configuration Types

The server uses two distinct types of configuration:

#### 1. Runtime Settings (CLI arguments & environment variables)
**Configured via:** Command-line arguments or environment variables
**Defined in:** `src/teradata_mcp_server/config/__init__.py` (Settings dataclass)
**Used for:** Server behavior, connections, transport settings

Examples:
- `--profile` / `PROFILE` - Which tools to load
- `--config_dir` / `CONFIG_DIR` - Where to find config files
- `--database_uri` / `DATABASE_URI` - Database connection string
- `--mcp_transport` / `MCP_TRANSPORT` - stdio, streamable-http, or sse
- `--logging_level` / `LOGGING_LEVEL` - Logging verbosity
- `LOGMECH`, `TD_POOL_SIZE`, `AUTH_MODE`, etc.

**Priority:** CLI arguments > Environment variables > .env file > Defaults

#### 2. Feature Configuration Files (YAML)
**Configured via:** YAML files in config directory
**Loaded by:** `config_loader.load_config()` function
**Used for:** Feature-specific settings (chat, RAG, SQL optimization, profiles, custom objects)

Files:
- `profiles.yml` - Define which tools/prompts/resources are available
- `chat_config.yml` - Chat completion configuration (model, API endpoint, etc.)
- `rag_config.yml` - RAG/vector store configuration
- `sql_opt_config.yml` - SQL optimizer configuration
- `*_objects.yml` - Custom tool/prompt/cube/glossary definitions

### Configuration File Loading Strategy

Configuration files are loaded in the order below using a **simple override strategy**:

1. **Built-in defaults** - Hardcoded defaults in the application code (if any)
2. **Packaged config** - Files in `src/teradata_mcp_server/config/` (source defaults, read-only in production)
3. **User config** - Files in the current working directory or in the config directory specified by `--config_dir` (runtime overrides)

**How overriding works:**
- Later layers override earlier layers
- **Top-level keys are replaced entirely** (no recursive merge)
- If a key exists in user config, it completely replaces the packaged config value
- Keys only in packaged config are preserved if not overridden

**Example:**
```python
# Packaged config/chat_config.yml
{
  "base_url": "http://localhost:11434",
  "model": "qwen",
  "databases": {"function_db": "openai_client", "default_db": "demo"}
}

# User config/chat_config.yml
{
  "base_url": "https://api.openai.com",
  "databases": {"function_db": "my_db"}
}

# Result (top-level keys replaced)
{
  "base_url": "https://api.openai.com",          # overridden
  "model": "qwen",                                # preserved (not in user config)
  "databases": {"function_db": "my_db"}          # ENTIRE "databases" replaced (default_db is gone)
}
```

**Important:** When overriding a dictionary key like `databases`, provide ALL values you need - the entire dictionary is replaced, not merged.

### Configuration File Examples

**profiles.yml** - Defines tool/prompt/resource profiles:
```yaml
all:
  tool: [".*"]
  prompt: [".*"]
  resource: [".*"]

dba:
  tool: ["^dba_*", "^base_*", "^sec_*"]
  prompt: ["^dba_*"]
```

**chat_config.yml** - Chat completion configuration:
```yaml
base_url: "http://localhost:11434"
model: "qwen2.5-coder:7b"
databases:
  function_db: "openai_client"
```

**custom_sales_objects.yml** - Custom tools, prompts, cubes:
```yaml
sales_top_customers:
  type: tool
  description: "Get the top 20 customers by lifetime value"
  sql: "SELECT TOP 20 * FROM customers ORDER BY lifetime_value DESC"
```

### For Developers:

The configuration system is implemented in:
- `src/teradata_mcp_server/config/__init__.py` - Runtime `Settings` dataclass (CLI/env configuration)
- `src/teradata_mcp_server/config_loader.py` - YAML file loading with simple override strategy
- `src/teradata_mcp_server/utils.py` - Helper functions for profiles and custom objects
- `src/teradata_mcp_server/app.py` - Wires everything together in `create_mcp_app(settings)`

Key functions:
- `settings_from_env()` - Create Settings from environment variables
- `config_loader.load_config(config_name, config_dir, defaults)` - Load a config file with override strategy
- `config_loader.set_global_config_dir(path)` - Set the global config directory (called at app startup)
- `config_loader.get_global_config_dir()` - Get the current config directory
- `load_profiles()` - Load packaged + user config directory profiles.yml
- `get_profile_config(profile_name)` - Get specific profile configuration

At runtime:
1. CLI arguments and environment variables are parsed into a `Settings` object
2. `Settings` is passed to `create_mcp_app(settings)`
3. The app sets the global config directory from `settings.config_dir`
4. Config files are loaded from that directory (with packaged defaults as fallback)

**Development Workflow:**
1. Packaged configs in `src/teradata_mcp_server/config/` provide defaults for all users
2. Create test configs in a separate directory (e.g., `./var/mcp-config/`)
3. Run with `--config_dir ./var/mcp-config/` to test overrides without modifying packaged files
4. Custom object files (`*_objects.yml`) are automatically discovered in the config directory

**Configuration Examples:**
See `examples/Configuration_Examples/` for complete example configurations that you can copy and customize.

<br>

## Tool/Prompt/Resource Naming Convention
To assist tool users we would like to align tool, prompt, and resources to a naming convention, this will assist MCP clients to group tools and understand its function.

- tool/prompt/resource name starts the grouping identifier (e.g. base).
- The tool/prompt/resource should have a descriptive name that is short, use lowercase with captials for new words.  (e.g. base_databaseList, qlty_missingValues, dba_tableSpace, dba_resusageUserSummary)

Two guides have been created to show how to add tools and prompts:
- [How to add new modules of tools](./HOW_TO_ADD_YOUR_FUNCTION.md)
- [Guidelines on how to specify prompts](./PROMPT_DEFINITION_GUIDELINES.md)

<br>

## Architecture Overview (for developers)

This section explains how the pieces fit together at runtime.

1) Entry point (`server.py`)
- Parses CLI args, merges with env using `Settings`.
- Calls `create_mcp_app(settings)`.
- Runs the chosen transport: `stdio`, `streamable-http`, or `sse`.

2) App factory (`app.py`)
- Sets up logging via `utils.setup_logging()` (skips console logs on stdio transport).
- Creates `FastMCP` instance.
- Initializes Teradata connections (SQLAlchemy engine), optional teradataml context and feature store config.
- Adds `RequestContextMiddleware` from `middleware.py` with:
  - stdio fast‑path (no headers/auth)
  - HTTP/SSE path that extracts headers, auth (if configured), client/session IDs, etc.
- Loads code‑defined tools via module loader and registers functions named `handle_*` that match `profiles.yml` patterns:
  - Wraps handlers with an internal `make_tool_wrapper` so MCP sees a clean signature.
  - The wrapper delegates execution to `execute_db_tool` which:
    - Injects a DB connection (SQLAlchemy `Connection` preferred)
    - Sets QueryBand based on request context (`tools/utils/queryband.py`)
- Dynamically registers `tdml_*` analytic function tools via the `teradata_lifespan` context manager, after the database connection and teradataml context are confirmed (see below).

### Dynamic teradataml Analytic Function Registration

The ~89 `tdml_*` tools (e.g., `tdml_KMeans`, `tdml_XGBoost`) are not defined as `handle_*` functions. Instead, `app.py` generates and registers them inside the `teradata_lifespan` async context manager at server startup, after the teradataml context is established:

1. **`tools/constants.py`** — `TD_ANALYTIC_FUNCS` is a `dict[str, str]` mapping each teradataml function name to a curated one-line summary (e.g., `"KMeans": "Groups observations into k clusters..."`). This dict is the authoritative list of which functions to register.

2. **`tools/utils/__init__.py`** — `build_tdml_tool_docstring(summary, func_metadata, partition_order_cols)` builds the compact MCP tool description at registration time. It reads parameter names, descriptions, Required/Optional, and types directly from `func_metadata.arguments` (teradataml's live JSON store, populated from the database), combining them with the curated summary.

3. **`app.py` (`teradata_lifespan`)** — After confirming the teradataml context is available, iterates `TD_ANALYTIC_FUNCS.items()`, queries the live JSON store for each function's metadata, generates a Python function string via `exec()`, and registers it with `server.tool()`. If a function from the dict is not present in the connected database's function list, it is skipped with a warning. Registration happens once at startup before any client connections are accepted.

**To add a new analytic function:** add one entry to `TD_ANALYTIC_FUNCS` in `tools/constants.py` with a concise one-line description. No other code changes are needed.

## Project Layout

A quick view of the important files and directories. Paths are relative to the repo root.

```
teradata-mcp-server/
├─ profiles.yml                     # Dev overrides for profiles (optional, not packaged)
├─ *_objects.yml                    # Dev/custom YAML objects (optional)
├─ logs/                            # Runtime logs (disabled on stdio by default)
└─ src/teradata_mcp_server/
   ├─ __init__.py                   # Package metadata + CLI entry main()
   ├─ __main__.py                   # Allows `python -m teradata_mcp_server`
   ├─ server.py                     # Slim entrypoint; parses CLI/env and runs app
   ├─ app.py                        # App factory: logging, middleware, tools, YAML, tdvs/EFS wiring
   ├─ utils.py                      # Logging setup, response formatting, config loaders
   ├─ middleware.py                 # Shared RequestContextMiddleware (stdio fast‑path + HTTP/SSE)
   ├─ config/                       # Packaged default profiles.yml
   │  └─ profiles.yml
   └─ tools/
      ├─ __init__.py               # Lazy module loader + explicit exports (e.g., TDConn)
      ├─ constants.py              # TD_ANALYTIC_FUNCS dict: teradataml function name → one-line summary
      ├─ module_loader.py          # Profiles → load only needed tool modules (+ YAMLs)
      ├─ td_connect.py             # SQLAlchemy connection + auth validation helpers
      ├─ utils/
      │  ├─ __init__.py            # JSON helpers, auth header parsing, tdml docstring builder
      │  └─ queryband.py           # Build Teradata QueryBand from request context
      ├─ base/ ...                 # Tool groups (base, dba, sec, qlty, rag, fs, tdvs, ...)
      └─ fs/...                    # Optional extras; imported only if profile enables them
```

Notes:
- EFS (fs) and tdvs (tdvs) modules are optional. They are loaded only if your profile enables tools with prefixes `fs_*` or `tdvs_*`. Missing dependencies result in a warning; the rest of the server continues to operate.
- Logging writes to a per‑user file location by default for HTTP/SSE transports; console logging is disabled for stdio to avoid polluting MCP protocol streams. Override with `LOG_DIR` or `NO_FILE_LOGS=1`.
    - Handles errors and response formatting
    - Reconnects when needed
- Loads YAML-defined tools, prompts, and resources and registers them.

3) Tools modules (`tools/*`)
- Contain Teradata-specific implementation.
- Handlers are plain Python (`handle_*`) and remain protocol‑agnostic; they receive a `Connection` and normal arguments.
- Docstrings are used as tool descriptions.

4) Configuration and Objects
- `profiles.yml` drives which tools/prompts/resources are enabled (by regex pattern) at startup.
- `*_objects.yml` define declarative tools, prompts, cubes, and glossaries.

This split keeps MCP concerns (transport, context, auth, formatting) in the server layer, and business/database logic in `tools`, making it easy to reuse tools with another protocol if desired.

## Interactive testing using the MCP Inspector

The [MCP inspector](https://www.npmjs.com/package/@modelcontextprotocol/inspector/v/0.9.0) provides you with a convenient way to browse and test tools, resources and prompts:

You can use the inspector to directly run the MCP server and connect over stdio:

**Using the development environment:**
```bash
 npx modelcontextprotocol/inspector uv run teradata-mcp-server
```

**Using the installed package:**
```bash
 npx modelcontextprotocol/inspector teradata-mcp-server
```

You may also run the MCP server as a separate process and connect to it form the inspector over http:

```bash
uv run teradata-mcp-server --mcp_transport streamable-http
npx modelcontextprotocol/inspector
```

## Build, Test, and Publish

We build with **uv** and publish via a GitHub Actions release workflow. Releases are not created on every commit — a release is triggered explicitly by pushing a git tag.

### Versions
- The CLI reads its version from package metadata (`importlib.metadata`).
- **Bump only in `pyproject.toml`** (do not hardcode in code).
- You **cannot overwrite** an existing version on PyPI/TestPyPI — always increment.

### Automated release workflow

The release workflow is defined in [`.github/workflows/release.yml`](../../.github/workflows/release.yml) and runs the following stages in order:

```
build & verify  →  create GitHub Release  →  publish TestPyPI  →  (approval)  →  publish PyPI
```

Each stage must succeed before the next starts. The `publish-pypi` job requires manual approval via the `pypi` GitHub Environment — this gives you time to verify the TestPyPI package before it goes to production.

#### One-time GitHub setup

> **VPN required** — you must be connected to the Teradata VPN to access the GitHub repository settings and to generate or retrieve API tokens from PyPI and TestPyPI.

**Secrets** — add these in *Settings → Secrets and variables → Actions*:

| Secret | Where to get it |
|---|---|
| `TEST_PYPI_TOKEN` | [test.pypi.org](https://test.pypi.org) → Account → API tokens |
| `PYPI_TOKEN` | [pypi.org](https://pypi.org) → Account → API tokens |

If you have previously published manually using Twine, your tokens are already stored locally in `~/.pypirc` — copy the `password` values from there rather than generating new ones.

**Environments** — create two environments in *Settings → Environments*:
- `test-pypi` — no protection rules required
- `pypi` — add yourself (or your team) as a **Required reviewer** to enable the approval gate

#### Triggering a release

Releases are grouped across multiple commits. When you are ready to ship:

```bash
# 1. Bump the version in pyproject.toml, commit, and push to main as normal
git add pyproject.toml
git commit -m "chore: bump version to 0.2.3"
git push

# 2. Tag the commit — pushing the tag fires the release workflow
git tag v0.2.3
git push origin v0.2.3
```

The tag must match the version in `pyproject.toml`. The workflow reads the version from `pyproject.toml` at build time and uses it throughout.

#### Approving a production release

After the TestPyPI publish and smoke test succeed, the workflow pauses before publishing to production PyPI and waits for a human to approve. Here is what happens:

1. GitHub sends you an **email notification** and a bell notification in the GitHub UI
2. Open the Actions run — you will see a yellow banner: *"This workflow is waiting for a review before continuing"*
3. Click **Review deployments**, tick the `pypi` environment checkbox, and click **Approve and deploy**
4. The `publish-pypi` job starts and the package is published to production PyPI

If something looks wrong (e.g., the TestPyPI smoke test installed the wrong version), click **Reject** instead — nothing is published to production and the run is cancelled. Fix the issue, bump the version, and start a new release.

> **Note:** Only the GitHub users configured as Required reviewers on the `pypi` environment can approve. The reviewer should confirm the TestPyPI smoke test passed before approving.

#### Re-running a failed publish

If a publish step fails (e.g., a transient network error), use the **Run workflow** button on the [Actions tab](https://github.com/Teradata/teradata-mcp-server/actions/workflows/release.yml) to re-trigger without creating a new tag.

#### What the workflow does

1. **Build & Verify** — runs `uv build --no-cache`, verifies metadata with `uvx twine check`, and smoke-tests the wheel locally
2. **Create GitHub Release** — creates a GitHub Release for the tag with auto-generated release notes and attaches the wheel and tarball as downloadable assets
3. **Publish to TestPyPI** — uploads with `uvx twine upload --repository testpypi`, then verifies installation with `uvx`
4. **Approval gate** — workflow pauses; reviewer approves in the GitHub UI after checking the TestPyPI package
5. **Publish to PyPI** — uploads with `uvx twine upload`, then runs a final smoke test from production PyPI

### Manual publish (fallback)

If you need to publish outside of CI, the steps below replicate what the workflow does.

#### 1) Build artifacts
```bash
uv build --no-cache
# Produces dist/teradata_mcp_server-<ver>-py3-none-any.whl and .tar.gz
```

#### 2) Test the wheel locally (no install)
```bash
# Run the installed console entry point from the wheel
uvx ./dist/teradata_mcp_server-<ver>-py3-none-any.whl teradata_mcp_server --version

# Or install as a persistent tool and run
uv tool install --reinstall ./dist/teradata_mcp_server-<ver>-py3-none-any.whl
~/.local/bin/teradata-mcp-server --help
```

#### 3) Verify metadata/README
```bash
uvx twine check dist/*
```

#### 4) Publish to **TestPyPI** (dress rehearsal)
```bash
# Upload
uvx twine upload --repository testpypi dist/*

# Try installing the just-published version with uvx
uvx --no-cache \
   --index-url https://test.pypi.org/simple \
   --extra-index-url https://pypi.org/simple \
   --index-strategy unsafe-best-match \
   "teradata-mcp-server==<ver>" --version
```
Notes:
- `--index-strategy unsafe-best-match` lets uv take our package from TestPyPI and other deps from PyPI.
- Use `--no-cache` to avoid stale wheels.

#### 5) Publish to **PyPI**
```bash
uvx twine upload dist/*
```
If you see `File already exists`, either:
- You haven't bumped the version in `pyproject.toml`. Do so, rebuild, and upload again.
- You have prior builds in the `./dist` directory. Remove them or specify the exact version (e.g., `uvx twine upload dist/*0.2.3*`).

#### 6) Post‑publish smoke test
```bash
# One‑off run
uvx "teradata-mcp-server==<ver>" --version

# Or persistent install
uv tool install "teradata-mcp-server==<ver>"
teradata-mcp-server --help
```

### Claude Desktop tips (stdio)
- For **no‑install** runs, point Claude to uvx:
```json
{
  "command": "/opt/homebrew/bin/uvx",
  "args": [
    "teradata-mcp-server==<ver>",
    "--profile", "all"
  ],
  "env": { "MCP_TRANSPORT": "stdio" }
}
```
- To test a **local wheel** in Claude, pass the wheel path instead of the name and run the module:
```json
{
  "command": "/opt/homebrew/bin/uvx",
  "args": [
    "/ABS/PATH/dist/teradata_mcp_server-<ver>-py3-none-any.whl",
    "python", "-m", "teradata_mcp_server", "--profile", "all"
  ],
  "env": { "MCP_TRANSPORT": "stdio" }
}
```

### Caching & indexes
- Refresh index data: `uvx --refresh …`
- Bypass caches: `--no-cache`
- Clean all caches: `uv cache clean`

## Tools testing

Use the provided testing tool to run tests, add tests if you add a new tool.

We have a "core" test suite for all the core tools provided with this server, separate ones for the add-ons (eg. Enterprise Feature Store, Enterprise Vector Store) and you can add more for your custom tools.

See guidelines and details in [our testing guide](/tests/README.md)

Run testing before PR, and copy/paste the test report status in the PR. 

**Development testing:**
```bash
python tests/run_mcp_tests.py "uv run teradata-mcp-server"
```

**Installed package testing:**
```bash
python tests/run_mcp_tests.py "teradata-mcp-server"
```

<br><br><br>

# Development Cycle

## Requesting Capabilities
- Go to github Issues tab
- click on New Issue
- click on Feature Request
- Fill out Feature Request form
    - Create a title
    - Add a description

## Raising incidents
- Go to github Issues tab
- click on New Issue
- click on Bug report
- Fill out Bug Report form
    - Create a title
    - Add a description


## Submitting Code
All contributions to the repository should be made through the Github pull request process.   [Contributing to a project step by step instuctions](https://docs.github.com/en/get-started/exploring-projects-on-github/contributing-to-a-project)

The repository admins will review the code for compliance and either provide feedback or merge the code.
