
# Teradata MCP Server Template

This code will form the basis for building Teradata MCP servers.

We have provided a base code under the /teradata_mcp_server directory that can be modified for the development of custom tools



### Environment Set Up
Step 1 - The environment has been put together assuming you have the uv package installed on your local machine.  Installation instructions for uv can be found at https://github.com/astral-sh/uv 

Step 2 - Clone the mcp-server repository with 

On Windows
```
mkdir MCP
cd MCP
git clone https://github.com/Teradata/teradata-mcp-server.git
cd teradata-mcp-server
uv sync
source .venv/Scripts/activate
```

On Mac
```
mkdir MCP
cd MCP
git clone https://github.com/Teradata/teradata-mcp-server.git
cd teradata-mcp-server
uv sync
source .venv/bin/activate
```

Step 3 - You need to update the .env file
- Rename env file to .env 
- The database URI will have the following format  teradata://username:password@host:1025/databasename, use a ClearScape Analytics Experience https://www.teradata.com/getting-started/demos/clearscape-analytics
    - the usename needs updating
    - the password needs updating
    - the Teradata host needs updating
    - the databasename needs updating

- LLM Credentials need to be available for /test/pydanticaiBedrock.py code to work
- SSE setting 
    - SSE : Boolean to determine if your server will be using the SSE transport (SSE = True) or the stdio transport (SSE=False)
    - SSE_HOST: IP address that the server can be found at, default should be 127.0.0.1
    - SSE_PORT: Port address that the server can be fount at, default should be 8001

Example .env file
```
############################################
DATABASE_URI=teradata://username:password@host:1025/databasename
SSE=False
SSE_HOST=127.0.0.1
SSE_PORT=8001

############################################
aws_access_key_id=
aws_secret_access_key=
aws_session_token=
aws_region_name=

############################################
OPENAI_API_KEY=

```


### Testing your server with MCP Inspector
Step 1 - Start the server, typer the following in your terminal
```
uv run mcp dev ./src/teradata_mcp_server/server.py
```
NOTE: If you are running this on a Windows machine and get npx, npm or node.js errors, install the required node.js software from here: https://github.com/nodists/nodist

Step 2 - Open the MCP Inspector
- You should open the inspector tool, go to http://127.0.0.1:6274 
- Click on tools
- Click on list tools
- Click on read_database_list
- Click on run

Test the other tools, each should have a successful outcome

Control+c to stop the server in the terminal

### Adding your sever to an Agent using stdio
step 1 - confirm the SSE flag in .env file has been set to False
```
SSE=False
```

Step 2 - Modify the ./test/ClientChatBot.py script to point to where you installed the server, you will need to modify the following line
```
    td_mcp_server = MCPServerStdio('uv', ["--directory", "/Users/Daniel.Tehan/Code/MCP/teradata-mcp-server/src/teradata_mcp_server", "run", "server.py"])
```

Step 2 - run the ./test/ClientChatBot.py script, this will create an interactive session with the agent who has access to the MCP server.  

From a terminal.
```
uv run ./test/ClientChatBot.py
```

- Ask the agent to list the databases
- Ask the agent to list the table in a database
- Ask the agent to show all the objects in a database
- Ask the agent a question that requires SQL to run against a table
- Type "quit" to exit.

### Adding tools using stdio to Visual Studio Code Co-pilot
- confirm the SSE flag in .env file has been set to False
```
SSE=False
```
- In VS Code, "Show and Run Commands"
- select "MCP: Add Server"
- select "Command Stdio"
- enter "uv" at command to run
- enter name of the server for the id
- the settings.json file should open
- modify the directory path and ensure it is pointing to where you have the server installed
- add the args so that it looks like:
```
    "mcp": {
        "servers": {
            "TeradataStdio": {
                "type": "stdio",
                "command": "uv",
                "args": [
                    "--directory",
                    "/Users/Daniel.Tehan/Code/MCP/teradata-mcp-server/src/teradata_mcp_server",
                    "run",
                    "server.py"
                ]
            }
        }
    }
```
- you can start the server from within the settings.json file or you can "MCP: Start Server"

### Adding tools using SSE to Visual Studio Code Co-pilot
- confirm the SSE flag in .env file has been set to False
```
SSE=True
SSE_HOST=127.0.0.1
SSE_PORT=8001
```
- you need to start the server from a terminal
```
uv run ./src/teradata_mcp_server/server.py
```
- In VS Code, "Show and Run Commands"
- select "MCP: Add Server"
- select "HTTP Server Sent Events"
- enter URL for the location of the server e.g. http://127.0.0.1:8001/sse
- enter name of the server for the id
- select user space
- the settings.json file should open
- add the args so that it looks like:
```
   "mcp": {
        "servers": {
            "TeradataSSE": {
                "type": "sse",
                "url": "http://127.0.0.1:8001/sse"
            }
        }
    }
```
- within the settings.json file or you can "MCP: Start Server"  

  
