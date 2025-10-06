# Using with any tool: REST interface

> **📍 Navigation:** [Documentation Home](../README.md) | [Server Guide](../README.md#-server-guide) | [Getting started](../server_guide/GETTING_STARTED.md) | [Architecture](../server_guide/ARCHITECTURE.md) | [Installation](../server_guide/INSTALLATION.md) | [Configuration](../server_guide/CONFIGURATION.md) | [Security](../server_guide/SECURITY.md) | [Customization](../server_guide/CUSTOMIZING.md) | [Client Guide](CLIENT_GUIDE.md)

You can use [mcpo](https://github.com/open-webui/mcpo) to expose this MCP tool as an OpenAPI-compatible HTTP server.

For example, using uv:

```
uvx mcpo --port 8002 --api-key "top-secret" -- uv run teradata-mcp-server
```

TOr with Docker, using the "rest"  profile:
```sh
export MCPO_API_KEY=top-secret
docker compose --profile rest up
```

Your Teradata tools are now available as local REST endpoints, view documentation and test it at http://localhost:8002/docs
