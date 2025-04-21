
# Teradata MCP Server Template

This code will form the basis for building Teradata MCP servers.

We have provided a base code under the /teradata_mcp directory that can be modified for the development of custom tools

We have also provided 4 servers:
1. teradata_businessinsight_mcp - this server will provide business descriptions for objects
2. teradata_datainsight_mcp - this server will enable the execution of DDL and SQL
3. teradata_dataquality_mcp - this server will provide data quality information for objects within Teradata
4. teradata_objectinsight_mcp - this server will provide object information


### Environment Set Up
Step 1 - The environment has been put together assuming you have the uv package installed on your local machine.  Installation instructions for uv can be found at https://github.com/astral-sh/uv 

Step 2 - Clone the mcp-server repository with 

```
mkdir MCP
cd MCP
git clone https://github.com/Teradata/mcp-server.git
cd mcp-server
uv sync
source .venv/bin/activate
```


Step 3 - You need to update the .env file
- Rename env file to .env 
- The database URI will have the following format  teradata:/username:password@host:1025/databasename, use a ClearScape Analytics Experience https://www.teradata.com/getting-started/demos/clearscape-analytics
    - the usename needs updating
    - the password needs updating
    - the Teradata host needs updating
    - the databasename needs updating

- LLM Credentials need to be available for /test/pydanticaiBedrock.py code to work

### Testing your server
Step 1 - Start the server, typer the following in your terminal
```
mcp dev ./teradata_objectinsight_mcp/src/server.py
```

Step 2 - Open the MCP Inspector
- You should open the inspector tool, go to http://127.0.0.1:6274 
- Click on tools
- Click on list tools
- Click on list_db
- Click on run

Test the other tools, each should have a successful outcome

Control+c to stop the server in the terminal

### Adding your sever to an Agent
Step 1 - run the test script, this will create an interactive session with the agent who has access to the MCP server.  

From a terminal.
```
cd mcp-server
python /test/pydanticaiBedrock.py
```

- Ask the agent to list the databases
- Ask the agent to list the table in a database
- Ask the agent to show all the objects in a database
- Ask the agent a question that requires SQL to run against a table
- Type "quit" to exit.

### Adding tools to Visual Studio Code Co-pilot
- In VS Code, "Show and Run Commands"
- select "MCP: Add Server"
- select "Command Stdio"
- enter "uv" at command to run
- enter name of the server for the id
- the settings.json file should open
- add the args so that it looks like:
```
 "teradata_dataisights_mcp": {
                "type": "stdio",
                "command": "uv",
                "args": [
                    "--directory",
                    "/Users/Daniel.Tehan/Code/MCP/mcp-server/teradata_datainsights_mcp/src",
                    "run",
                    "server.py"
                ]
            }
```
- you can start the server from within the settings.json file or you can "MCP: Start Server"

  

  
