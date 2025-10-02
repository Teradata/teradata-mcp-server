## Testing your server with MCP Inspector

MCP Inspector was developed by Anthropic to support the testing of servers.  It provides a GUI for you to connect to your server and make tool and prompt calls.  All developers should use this for initial testing of tools ad prompts. 

Step 0 - In a terminal move into teradata-mcp-server directory From a terminal and start the server.
```
cd teradata-mcp-server
uv run src/teradata_mcp_server
```

Step 1 - In a second terminal start the inspector, type the following in your terminal
The [MCP inspector](https://www.npmjs.com/package/@modelcontextprotocol/inspector/v/0.9.0) provides you with a convenient way to browse and test tools, resources and prompts:

You can use the inspector to directly run the MCP server and connect over stdio:

**Using the development environment:**
```bash
 npx modelcontextprotocol/inspector uv run teradata-mcp-server
```

**Using the installed package:**
```bash
 npx modelcontextprotocol/inspector teradata-mcp-server
```

You may also run the MCP server as a separate process and connect to it form the inspector over http:

```bash
uv run teradata-mcp-server --mcp_transport streamable-http
npx modelcontextprotocol/inspector
```
NOTE: If you are running this on a Windows machine and get npx, npm or node.js errors, install the required node.js software from here: https://github.com/nodists/nodist

Step 2 - Open the MCP Inspector
- You should open the inspector tool, go to http://127.0.0.1:6274 
- Click on tools
- Click on list tools
- Click on base_databaseList
- Click on run

Test the other tools, each should have a successful outcome

Control+c to stop the server in the terminal
