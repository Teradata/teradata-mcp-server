# Development Conventions

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

> Tip: add extras for full dev (feature store, EVS) if you use them:
```bash
uv sync --extra fs --extra evs
```

### 3) Run the server from source
```bash
uv run teradata-mcp-server --profile all
```

### 4) MCP Inspector (interactive testing)
```bash
uv run mcp dev ./src/teradata_mcp_server/server.py
```

### 5) Run tests

Always run tests before submitting a PR:

```bash
# core tests
python tests/run_mcp_tests.py "uv run teradata-mcp-server"
```
Most users use the MCP server with Claude, stdio, so always test Claude's behaviour with your code or build before pushing it. 

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

[src/teradata_mcp_server](./src/teradata_mcp_server) - this will contain all source code.
- __init__.py - will contain server imports  
- server.py - contains the main server script and will decorate tools, prompts, and resources
- utils.py - utilities for configuration management and other server functions
- config/ - packaged configuration files (default profiles.yml and other configuration defaults)
- testing/ - testing framework and utilities


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

2. New tool libraries - this approach requires changes to the server code, as defined below.
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

The server uses a hierarchical configuration system that supports both packaged defaults and user customizations:

### Configuration Hierarchy (highest to lowest priority):
1. **CLI arguments** - Command line flags override everything
2. **Environment variables** - Standard environment variable configuration  
3. **Working directory configs** - External `profiles.yml` and `*_objects.yml` files
4. **Packaged defaults** - Built-in configurations shipped with the package

### Package vs Development Configuration:

**PyPI Installation:**
- Default configurations are packaged in `src/teradata_mcp_server/config/`
- Users can create local `profiles.yml` and `*_objects.yml` files to override/extend
- Configurations are automatically merged at runtime

**Development Environment:**
- External configuration files in repository root are used for development
- Same merging logic applies, but external files take precedence

### Configuration Files:

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

***_objects.yml** - Define custom tools, prompts, cubes, and glossaries:
```yaml
my_custom_tool:
  type: tool
  description: "My custom SQL tool"
  sql: "SELECT COUNT(*) FROM my_table"
```

### For Developers:

The configuration system is implemented in `src/teradata_mcp_server/utils.py` and provides simple functions:
- `load_profiles()` - Load packaged + working directory profiles.yml
- `get_profile_config(profile_name)` - Get specific profile configuration  
- `load_all_objects()` - Load all packaged + working directory YAML objects

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

## Interactive testing using the MCP Inspector

The MCP inspector provides you with a convenient way to browse and test tools, resources and prompts:

**For development environment:**
```bash
uv run mcp dev ./src/teradata_mcp_server/server.py
```

**For installed package:**
```bash
mcp dev teradata-mcp-server
```

## Build, Test, and Publish

We build with **uv**, test locally (wheel), then push to **TestPyPI** before PyPI.

### Versions
- The CLI reads its version from package metadata (`importlib.metadata`).
- **Bump only in `pyproject.toml`** (do not hardcode in code).
- You **cannot overwrite** an existing version on PyPI/TestPyPI — always increment.

### 1) Build artifacts
```bash
uv build --no-cache
# Produces dist/teradata_mcp_server-<ver>-py3-none-any.whl and .tar.gz
```

### 2) Test the wheel locally (no install)
```bash
# Run the installed console entry point from the wheel
uvx ./dist/teradata_mcp_server-<ver>-py3-none-any.whl \
    python -m teradata_mcp_server --version

# Or install as a persistent tool and run
uv tool install --reinstall ./dist/teradata_mcp_server-<ver>-py3-none-any.whl
~/.local/bin/teradata-mcp-server --help
```

### 3) Verify metadata/README
```bash
twine check dist/*
```

### 4) Publish to **TestPyPI** (dress rehearsal)
```bash
# Upload
python -m twine upload --repository testpypi dist/*

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

### 5) Publish to **PyPI**
```bash
python -m twine upload dist/*
```
If you see `File already exists`, bump the version in `pyproject.toml`, rebuild, and upload again.

### 6) Post‑publish smoke test
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
