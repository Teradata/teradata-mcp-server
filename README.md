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


## Getting Started

![Getting Started](https://raw.githubusercontent.com/Teradata/teradata-mcp-server/main/docs/media/MCP-quickstart.png)

**Step 1.** - Identify the running Teradata System, you need username, password and host details to populate "teradata://username:password@host:1025". If you do not have a Teradata system to connect to, then leverage [Teradata Clearscape Experience](https://www.teradata.com/getting-started/demos/clearscape-analytics)

**Step 2.** - To configure and run the MCP server, refer to the [Getting started guide](https://github.com/Teradata/teradata-mcp-server/blob/main/docs/GETTING_STARTED.md).

**Step 3.** - There are many client options available, the [Client Guide](https://github.com/Teradata/teradata-mcp-server/blob/main/docs/client_guide/CLIENT_GUIDE.md) explains how to configure and run a sample of different clients.

<br>

[A Video Library](https://github.com/Teradata/teradata-mcp-server/blob/main/docs/VIDEO_LIBRARY.md) has been curated to assist.

<br>



## Installation

### PyPI Installation (Recommended)

The easiest way to get started is to install from PyPI:

```bash
pip install teradata-mcp-server
```

### Quick start with Claude desktop

Once installed, you can use the MCP server with Claude Desktop:

1. Get your Teradata database credentials or create a free sandbox at [Teradata Clearscape Experience](https://www.teradata.com/getting-started/demos/clearscape-analytics).
2. Install [Claude Desktop](https://claude.ai/download)
3. Configure the claude_desktop_config.json (Settings>Developer>Edit Config) by adding the configuration below, updating the database username, password and URL:

```json
{
  "mcpServers": {
    "teradata": {
      "command": "teradata-mcp-server",
      "args": ["--profile", "all"],
      "env": {
        "DATABASE_URI": "teradata://<USERNAME>:<PASSWORD>@<HOST_URL>:1025/<USERNAME>"
      }
    }
  }
}
```

### Build from Source (Development)

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
