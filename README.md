<p align="center">
  <!-- Optional: replace with a logo if you have one -->
  <!-- <img src="docs/media/logo.svg" alt="Teradata MCP Server" width="120"> -->
  
</p>

<h1 align="center">Teradata MCP Server</h1>

<p align="center">
  <a href="https://github.com/Teradata/teradata-mcp-server/blob/main/docs/README.md">
    <img alt="docs" src="https://img.shields.io/badge/docs-readme-555?logo=readthedocs">
  </a>
  <a href="https://github.com/Teradata/teradata-mcp-server/releases">
    <img alt="release" src="https://img.shields.io/github/v/release/Teradata/teradata-mcp-server?display_name=tag&sort=semver">
  </a>
  <a href="https://pypi.org/project/teradata-mcp-server/">
    <img alt="PyPI" src="https://img.shields.io/pypi/v/teradata-mcp-server">
  </a>
  <a href="https://pypi.org/project/teradata-mcp-server/">
    <img alt="downloads" src="https://img.shields.io/pypi/dm/teradata-mcp-server?label=downloads&color=2ea44f">
  </a>
</p>

<p align="center">
  Model Context Protocol (MCP) server for Teradata
 </p>

<p align="center">
  ✨ <a href="https://github.com/Teradata/teradata-mcp-server?tab=readme-ov-file#quick-start-with-claude-desktop-no-installation">Quickstart with Claude Desktop </a> or <a href="https://github.com/Teradata/teradata-mcp-server/blob/main/docs/README.md#-quick-start"> your favorite tool</a> in <5 minute ✨
</p>

## Overview
The Teradata MCP server provides sets of tools and prompts, grouped as modules for interacting with Teradata databases. Enabling AI agents and users to query, analyze, and manage their data efficiently. 

![Getting Started](https://raw.githubusercontent.com/Teradata/teradata-mcp-server/main/docs/media/client-server-platform.png)

## Key features

### Available tools and prompts

We are providing groupings of tools and associated helpful prompts to support all type of agentic applications on the data platform.

![Teradata MCP Server diagram](https://raw.githubusercontent.com/Teradata/teradata-mcp-server/main/docs/media/teradata-mcp-server.png)

- **Search** tools, prompts and resources to search and manage vector stores.
  - [RAG Tools](https://github.com/Teradata/teradata-mcp-server/blob/main/src/teradata_mcp_server/tools/rag/README.md) rapidly build RAG applications.
- **Query** tools, prompts and resources to query and navigate your Teradata platform:
  - [Base Tools](https://github.com/Teradata/teradata-mcp-server/blob/main/src/teradata_mcp_server/tools/base/README.md)
- **Table** tools, to efficiently and predictably access structured data models:
  - [Feature Store Tools](https://github.com/Teradata/teradata-mcp-server/blob/main/src/teradata_mcp_server/tools/fs/README.md) to access and manage the Teradata Enterprise Feature Store.
  - [Semantic layer definitions](https://github.com/Teradata/teradata-mcp-server/blob/main/docs/server_guide/CUSTOMIZING.md) to easily implement domain-specific tools, prompts and resources for your own business data models. 
- **Data Quality** tools, prompts and resources accelerate exploratory data analysis:
  - [Data Quality Tools](https://github.com/Teradata/teradata-mcp-server/blob/main/src/teradata_mcp_server/tools/qlty/README.md)
- **DBA** tools, prompts and resources to facilitate your platform administration tasks:
  - [DBA Tools](https://github.com/Teradata/teradata-mcp-server/blob/main/src/teradata_mcp_server/tools/dba/README.md)
  - [Security Tools](https://github.com/Teradata/teradata-mcp-server/blob/main/src/teradata_mcp_server/tools/sec/README.md)

## Quick start with Claude Desktop (no installation)
> Prefer to use other tools? Check out our Quick Starts for [VS Code/Copilot](https://github.com/Teradata/teradata-mcp-server/blob/main/docs/server_guide/QUICK_START_VSCODE.md), [Open WebUI](https://github.com/Teradata/teradata-mcp-server/blob/main/docs/server_guide/QUICK_START_OPEN_WEBUI.md), or dive into [simple code examples](https://github.com/Teradata/teradata-mcp-server/blob/main/examples/README.md#client-applications)!
You can use Claude Desktop to give the  Teradata MCP server a quick try, Claude can manage the server in the background using `uv`. No permanent installation needed.

**Pre-requisites**
1. Get your Teradata database credentials or create a free sandbox at [Teradata Clearscape Experience](https://www.teradata.com/getting-started/demos/clearscape-analytics).
2. Install [Claude Desktop](https://claude.ai/download).
3. Install [uv](https://docs.astral.sh/uv/getting-started/installation/). If you are on MacOS, Use Homebrew: `brew install uv`, on Windows you may use `pip install uv` as an alternative to the installer.

Configure the claude_desktop_config.json (Settings>Developer>Edit Config) by adding the configuration below, updating the database username, password and URL:

```json
{
  "mcpServers": {
    "teradata": {
      "command": "uvx",
      "args": ["teradata-mcp-server"],
      "env": {
        "DATABASE_URI": "teradata://<USERNAME>:<PASSWORD>@<HOST_URL>:1025/<USERNAME>"
      }
    }
  }
}
```

## Setting up your environment

Follow this process to install your server, connect it to your Teradata platform and integrated your tools.

**Step 1.** - Identify the running Teradata System, you need username, password and host details. If you do not have a Teradata system to connect to, then leverage [Teradata Clearscape Experience](https://www.teradata.com/getting-started/demos/clearscape-analytics)

**Step 2.** - To install, configure and run the MCP server, refer to the [Getting started guide](https://github.com/Teradata/teradata-mcp-server/blob/main/docs/server_guide/GETTING_STARTED.md), or see below for a quick [CLI installation](#CLI-Installation). You can easily [customize the server with your own tools, prompts and resources](docs/server_guide/CUSTOMIZING.md).

**Step 3.** - There are many client options available, the [Client Guide](https://github.com/Teradata/teradata-mcp-server/blob/main/docs/README.md#-client-guide) explains how to configure and run a sample of different clients.

<br>

Check out our [documentation](https://github.com/Teradata/teradata-mcp-server/blob/main/docs/README.md) and libraries of [curated examples](https://github.com/Teradata/teradata-mcp-server/blob/main/examples/) or [video guides](https://github.com/Teradata/teradata-mcp-server/blob/doc-v1.4/docs/server_guide/VIDEO_LIBRARY.md).

<br>

## CLI Installation

We recommend `uv` or `pipx` to install teradata-mcp-server as a CLI tool on your system. 
They provide isolated environments and ensure the `teradata-mcp-server` command is available system-wide without interfering with system Python.

```bash
uv tool install "teradata-mcp-server"
```

or with pipx

```bash
pipx install "teradata-mcp-server"
```

To install the optional Enterprise Feature Store (fs) and Enterprise Vector Store (evs) packages:
```bash
uv tool install "teradata-mcp-server[fs,evs]"
```

Alternatively, you may use pip in a virtual environment (Python>=3.11):

```bash
pip install teradata-mcp-server
```

For usage:

```bash
teradata-mcp-server --help
```

**Troubleshooting**
When using uv, If the tool's path isn't resolved add it to your shell using `uv tool update-shell` and restart the terminal.

## Build from Source (Development)

For development or customization, you can build from source:

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/). If you are on macOS, use Homebrew: `brew install uv`
2. Clone this repository: `git clone https://github.com/Teradata/teradata-mcp-server.git`
3. Navigate to the directory: `cd teradata-mcp-server`
4. Run the server: `uv run teradata-mcp-server`

For Claude Desktop with development build, use this configuration:

```json
{
  "mcpServers": {
    "teradata": {
      "command": "uv",
      "args": [
        "--directory",
        "<PATH_TO_DIRECTORY>/teradata-mcp-server",
        "run",
        "teradata-mcp-server"
      ],
      "env": {
        "DATABASE_URI": "teradata://<USERNAME>:<PASSWORD>@<HOST_URL>:1025/<USERNAME>",
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

## Contributing
Please refer to the [Contributing](https://github.com/Teradata/teradata-mcp-server/blob/main/docs/developer_guide/CONTRIBUTING.md) guide and the [Developer Guide](https://github.com/Teradata/teradata-mcp-server/blob/main/docs/developer_guide/DEVELOPER_GUIDE.md).


---------------------------------------------------------------------
## Certification
<a href="https://glama.ai/mcp/servers/@Teradata/teradata-mcp-server">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@Teradata/teradata-mcp-server/badge" alt="Teradata Server MCP server" />
</a>
