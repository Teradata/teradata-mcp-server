## Using with Claude Desktop

[Claude Desktop Instructions](https://modelcontextprotocol.io/quickstart/user)

Modify your claude desktop configuration file -  `claude_desktop_config.json` config file:

**Embedded server with stdio communication**

The simplest option is to start the mcp server with Claude and enable communication over stdio

Example can be found in [claude_desktop_stdio_config](../../examples/Claude_Desktop_Config_Files/claude_desktop_stdio_config)

Note: you will need to modify the directory path in the args for your system, this needs to be a complete path.  You may also need to have a complete path to uv in the command as well.

Note: this requires that `uv` is available to Claude in your system path or installed globally on your system (eg. uv installed with `brew` for Mac OS users).

Note: The PROFILE variable is optional, you can change its value to instantiate servers with different profiles (ie. pre-defined collections of tools, prompts and resources). See default profiles in [profiles config file](../../profiles.yml)

**Remote server with streamable-http communication**

If you have a Teradata MCP Server instance running and available via http (1), you can connect to it using the [mcp-remote npx package](https://www.npmjs.com/package/mcp-remote).

Example can be found in [claude_desktop_http_config](../../examples/Claude_Desktop_Config_Files/claude_desktop_http_config)

Note: The Claude Desktop example assumes a server running locally on port 8001 - modify as needed.

Note (1): See UV or Docker options in the [Getting Started](../GETTING_STARTED.md) guide to start the MCP server process with http-streamable.

**SSE (deprecated)**

Warning: We are not actively maintaining and testing the SSE functionality.

Example can be found in [claude_desktop_SSE_config](../../examples/Claude_Desktop_Config_Files/claude_desktop_SSE_config)

Note: you may need to modify the host in the args.