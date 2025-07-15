# Teradata MCP Server

## Overview
The Teradata MCP server provides sets of tools and prompts, grouped as modules for interacting with Teradata databases. Enabling AI agents and users to query, analyze, and manage their data efficiently. 



## Key features

### Available tools and prompts

We are providing groupings of tools and associated helpful prompts
- **Base** tools, prompts and resources to interact with your Teradata platform:
  - [Base Tools](src/teradata_mcp_server/tools/base/README.md)
- **DBA** tools, prompts and resources to facilitate your platform administration tasks:
  - [DBA Tools](src/teradata_mcp_server/tools/dba/README.md)
- **Data Quality** tools, prompts and resources accelerate exploratory data analysis:
  - [Data Quality Tools](src/teradata_mcp_server/tools/qlty/README.md)
- **Security** tools, prompts and resources to resolve permissions:
  - [Security Tools](src/teradata_mcp_server/tools/sec/README.md)
- **Feature Store** tools, prompts and resources to manage the Enterprise Feature Store:
  - [Feature Store Tools](src/teradata_mcp_server/tools/fs/README.md)
- **RAG** tools, prompts and resources to manage vector store creation and use
  - [RAG Tools](src/teradata_mcp_server/tools/rag/README.md)
- **Custom Tools** to easily implement tools for custom actions based on your data and business context. Refer to [developer guide](docs/developer_guide/HOW_TO_ADD_CUSTOM_FUNCTIONS.md)


## Getting Started

![Getting Started](docs/media/MCP.png)

**Step 1.** - Identify the running Teradata System, you need username, password and host details to populate "teradata://username:password@host:1025". If you do not have a Teradata system to conect to, then leverage [Teradata Clearscape Experience](https://www.teradata.com/getting-started/demos/clearscape-analytics)

**Step 2.** - To cofigure and run the MCP server, refer to the [Getting stated guide](docs/GETTING_STARTED.md).

**Step 3.** - There are many client options availale, the [Client Guide](docs/client_guide/CLIENT_GUIDE.md) explains how to configure and run a sample of different clients.




---------------------------------------------------------------------
## Certification
<a href="https://glama.ai/mcp/servers/@Teradata/teradata-mcp-server">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@Teradata/teradata-mcp-server/badge" alt="Teradata Server MCP server" />
</a>