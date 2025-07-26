## Using with Visual Studio Code Co-pilot

Visual Studio Code Co-pilot provides a simple and interactive way to test this server. 
Follow the instructions below to run and configure the server, set co-pilot to Agent mode, and use it.

![alt text](../media/copilot-agent.png)

Detailed instructions on configuring MCP server with Visual Studio Code can be found [in Visual Studio Code documentation](https://code.visualstudio.com/docs/copilot/chat/mcp-servers).


### Using Streamable-http (recommended)

You can use uv or Docker to start the server.

Using uv, ensure that Streamable-http is enabled and the host port are defined. You can do this with setting the environment variables below or in the `.env` file):

```
export MCP_TRANSPORT=streamable-http
export MCP_HOST=127.0.0.1
export MCP_PORT=8001
export MCP_PATH=/mcp/

uv run teradata-mcp-server
```

Add the server in VS Code:

- Open the Command Palette (View>Command Palette)
- select "MCP: Add Server"
- select "HTTP or Server Sent Events"
- enter URL for the location of the server e.g. http://127.0.0.1:8001/mcp/
- enter name of the server for the id (e.g. teradata-http)
- select user space
- the settings.json file should open
- add the args so that it looks like:
```
   "mcp": {
        "servers": {
            "teradata-http": {
                "type": "http",
                "url": "http://127.0.0.1:8001/mcp/"
            }
        }
    }
```
- within the settings.json file or you can "MCP: Start Server"  
 
### Using stdio
To run the server with stdio set MCP_TRANSPORT=stdio in your .env file or via the `MCP_TRANSPORT` environment variable.

```
export MCP_TRANSPORT=stdio
uv run teradata-mcp-server
```

Add the server in VS Code:

- Open the Command Palette (View>Command Palette)
- select "MCP: Add Server"
- select "Command Stdio"
- enter "uv" at command to run
- enter name of the server for the id
- the settings.json file should open
- modify the directory path and ensure it is pointing to where you have the server installed
- add the args so that it looks like:

Note: you will need to modify the directory path in the args for your system, this needs to be a complete path.  You may also need to have a complete path to uv in the command as well.
```
    "mcp": {
        "servers": {
            "teradataStdio": {
                "type": "stdio",
                "command": "uv",
                "args": [
                    "--directory",
                    "<Full Path>/teradata-mcp-server",
                    "run",
                    "teradata-mcp-server"
                ],
                "env": {
                    "DATABASE_URI": "teradata://username:password@host:1025/databasename"
                }
            }
        }
    }
```
- you can start the server from within the settings.json file or you can "MCP: Start Server"
