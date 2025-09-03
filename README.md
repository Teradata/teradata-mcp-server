# Teradata MCP Server

## Overview
The Teradata MCP server provides sets of tools and prompts, grouped as modules for interacting with Teradata databases. Enabling AI agents and users to query, analyze, and manage their data efficiently. 



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
  - [Semantic layer definitions](https://github.com/Teradata/teradata-mcp-server/blob/main/docs/CUSTOMIZING.md) to easily implement domain-specific tools, prompts and resources for your own business data models. 
- **Data Quality** tools, prompts and resources accelerate exploratory data analysis:
  - [Data Quality Tools](https://github.com/Teradata/teradata-mcp-server/blob/main/src/teradata_mcp_server/tools/qlty/README.md)
- **DBA** tools, prompts and resources to facilitate your platform administration tasks:
  - [DBA Tools](https://github.com/Teradata/teradata-mcp-server/blob/main/src/teradata_mcp_server/tools/dba/README.md)
  - [Security Tools](https://github.com/Teradata/teradata-mcp-server/blob/main/src/teradata_mcp_server/tools/sec/README.md)
- **BAR** tools, prompts and resources for backup and recovery operations:
  - [BAR Tools](https://github.com/Teradata/teradata-mcp-server/blob/main/src/teradata_mcp_server/tools/bar/README.md) to manage DSA disk file systems and backup operations.


## Getting Started

![Getting Started](https://raw.githubusercontent.com/Teradata/teradata-mcp-server/main/docs/media/MCP-quickstart.png)

**Step 1.** - Identify the running Teradata System, you need username, password and host details to populate "teradata://username:password@host:1025". If you do not have a Teradata system to connect to, then leverage [Teradata Clearscape Experience](https://www.teradata.com/getting-started/demos/clearscape-analytics)

**Step 2.** - To configure and run the MCP server, refer to the [Getting started guide](https://github.com/Teradata/teradata-mcp-server/blob/main/docs/GETTING_STARTED.md).

**Step 3.** - There are many client options available, the [Client Guide](https://github.com/Teradata/teradata-mcp-server/blob/main/docs/client_guide/CLIENT_GUIDE.md) explains how to configure and run a sample of different clients.

<br>

[A Video Library](https://github.com/Teradata/teradata-mcp-server/blob/main/docs/VIDEO_LIBRARY.md) has been curated to assist.

<br>


## Quick start with Claude Desktop (no installation)

Claude Desktop can get and start the Teradata MCP server in the background using `uv`. No permanent installation needed.

**Pre-requisites**
1. Get your Teradata database credentials or create a free sandbox at [Teradata Clearscape Experience](https://www.teradata.com/getting-started/demos/clearscape-analytics).
2. Install [Claude Desktop](https://claude.ai/download).
3. Install [uv](https://docs.astral.sh/uv/getting-started/installation/). If you are on MacOS, Use Homebrew: `brew install uv`.

Configure the claude_desktop_config.json (Settings>Developer>Edit Config) by adding the configuration below, updating the database username, password and URL:

```json
{
  "mcpServers": {
    "teradata": {
      "command": "uvx",
      "args": ["teradata-mcp-server", "--profile", "all"],
      "env": {
        "DATABASE_URI": "teradata://<USERNAME>:<PASSWORD>@<HOST_URL>:1025/<USERNAME>"
      }
    }
  }
}
```

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
Please refer to the [Contributing](https://github.com/Teradata/teradata-mcp-server/blob/main/docs/CONTRIBUTING.md) guide and the [Developer Guide](https://github.com/Teradata/teradata-mcp-server/blob/main/docs/developer_guide/DEVELOPER_GUIDE.md).


---------------------------------------------------------------------
## Certification
<a href="https://glama.ai/mcp/servers/@Teradata/teradata-mcp-server">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@Teradata/teradata-mcp-server/badge" alt="Teradata Server MCP server" />
</a>
