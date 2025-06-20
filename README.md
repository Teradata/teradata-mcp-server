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
- **Custom Tools** to easily implement tools for custom actions based on your data and business context. 

### Adding custom tools
You may add define custom "query" tools in the `custom_tools.yaml` file or in any file ending with `_tools.yaml`. 
Simply specify the tool name, description and SQL query to be executed. No parameters are supported at this point.


--------------------------------------------------------------------------------------

## TLDR; I want to try it locally now

If you have Docker and a client that can connect MCP servers via SSE, copy the code below, update the connection string set in `DATABASE_URI` with your database connection details and run it:

```
export DATABASE_URI=teradata://username:password@host:1025
git clone https://github.com/Teradata/teradata-mcp-server.git
cd teradata-mcp-server
docker compose up
```

You can now use it with clients supporting SSE such as [Visual Studio Code](docs/CLIENT_GUIDE.md#using-with-visual-studio-code-co-pilot).




---------------------------------------------------------------------
## Certification
<a href="https://glama.ai/mcp/servers/@Teradata/teradata-mcp-server">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@Teradata/teradata-mcp-server/badge" alt="Teradata Server MCP server" />
</a>