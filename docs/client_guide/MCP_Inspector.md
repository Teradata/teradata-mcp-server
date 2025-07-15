## Testing your server with MCP Inspector

MCP Inspector was developed by Anthropic to support the testing of servers.  It provides a GUI for you to connect to your server and make tool and prompt calls.  All developers should use this for initial testing of tools ad prompts. 


Step 1 - Start the server, typer the following in your terminal
```
uv run mcp dev ./src/teradata_mcp_server/server.py
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
