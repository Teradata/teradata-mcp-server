# Using with Claude Desktop

> **📍 Navigation:** [Documentation Home](../README.md) | [Server Guide](../README.md#-server-guide) | [Getting started](../server_guide/GETTING_STARTED.md) | [Architecture](../server_guide/ARCHITECTURE.md) | [Installation](../server_guide/INSTALLATION.md) | [Configuration](../server_guide/CONFIGURATION.md) | [Security](../server_guide/SECURITY.md) | [Customization](../server_guide/CUSTOMIZING.md) | [Client Guide](CLIENT_GUIDE.md)

[Claude Desktop Instructions](https://modelcontextprotocol.io/quickstart/user)

Modify your claude desktop configuration file -  `claude_desktop_config.json` config file:

Based on the transport mode of your server (Streamable-http, Stdio or SSE) you will pick on of the corresponding configuration approach:
- [Using with Claude Desktop](#using-with-claude-desktop)
  - [Option 1 - Remote server with streamable-http communication (Default)](#option-1---remote-server-with-streamable-http-communication-default)
  - [Option 2 - Embedded server with stdio communication](#option-2---embedded-server-with-stdio-communication)
  - [Option 3 - SSE (deprecated) - Not recommended](#option-3---sse-deprecated---not-recommended)



--------------------------------------------------------

### Option 1 - Remote server with streamable-http communication (Default)

If you have a Teradata MCP Server instance running and available via http (1), you can connect to it using the [mcp-remote npx package](https://www.npmjs.com/package/mcp-remote) (2).

Example can be found in [claude_desktop_http_config](../../examples/client-claude-desktop/claude_desktop_http_config)

Note: The Claude Desktop example assumes a server running locally on port 8001 - modify as needed.

Note (1): See UV or Docker options in the [Getting Started](../GETTING_STARTED.md) guide to start the MCP server process with http-streamable.

Note (2): You need Node installed on your system. Use [HomeBrew](https://formulae.brew.sh/formula/node) on mac (ie. `brew install nps`)

--------------------------------------------------------
### Option 2 - Embedded server with stdio communication

The simplest option is to start the mcp server with Claude and enable communication over stdio

Example can be found in [claude_desktop_stdio_config](../../examples/client-claude-desktop/claude_desktop_stdio_config)

Note: you will need to modify the directory path in the args for your system, this needs to be a complete path.  You may also need to have a complete path to uv in the command as well.

Note: this requires that `uv` is available to Claude in your system path or installed globally on your system (eg. uv installed with `brew` for Mac OS users).

Note: The PROFILE variable is optional, you can change its value to instantiate servers with different profiles (ie. pre-defined collections of tools, prompts and resources). See default profiles in [profiles config file](../../profiles.yml)

--------------------------------------------------------
### Option 3 - SSE (deprecated) - Not recommended

Warning: We are not actively maintaining and testing the SSE functionality.

Example can be found in [claude_desktop_SSE_config](../../examples/client-claude-desktop/claude_desktop_SSE_config)

Note: you may need to modify the host in the args.
