# Testing agents for the MCP Server

You can find some additional prompts, helpful to build agents to test the functionality provided by this server.

## How to use it

To run the MCP Server with these promtps, simply move to this directory and start the server:

For example:

```sh
export DATABASE_URI=teradata://username:password@host:1025/schemaname
```

```sh
cd examples/MCP_Testing_Agent
uv run teradata-mcp-server --profile tester --mcp_transport=streamable-http --mcp_port=8001
```

Connect your agent or application, and load the prompts named `test_*`.