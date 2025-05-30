# Teradata MCP Server Template

### Overview
The Teradata MCP server is a open source project, we welcome contributions via pull requests.

We are providing three sets of tools and associated helpful prompts
1. td_base tools / prompts / resources:
    - get_td_base_readQuery - runs a read query
    - write_td_base_writeQuery - runs a write query
    - get_td_base_tableDDL - returns the show table results
    - get_td_base_databaseList - returns a list of all databases
    - get_td_base_tableList - returns a list of tables in a database
    - get_td_base_columnDescription - returns description of columns in a table
    - get_td_base_tablePreview - returns column information and 5 rows from the table
    - get_td_base_tableAffinity - gets tables commonly used together
    - get_td_base_tableUsage - Measure the usage of a table and views by users in a given schema

    - prompt_td_base_query - Create a SQL query against the database
    - prompt_td_base_tableBusinessDesc - generates a business description of a table
    - prompt_td_base_databaseBusinessDesc - generates a business description of a databases based on the tables

2. td_dba tools / prompts / resources:
    - get_td_dba_userSqlList - returns a list of recently executed SQL for a user
    - get_td_dba_tableSqlList - returns a list of recently executed SQL for a table
    - get_td_dba_tableSpace - returns CurrentPerm table space 
    - get_td_dba_databaseSpace - returns Space allocated, space used and percentage used for a database
    - get_td_dba_databaseVersion - returns the database version information
    - get_td_dba_resusageSummary - Get the Teradata system usage summary metrics by weekday and hour for each workload type and query complexity bucket.
    - get_td_dba_resusageUserSummary - Get the system usage for a user
    - get_td_dba_flowControl - Get the Teradata system flow control metrics by day and hour
    - get_td_dba_featureUsage - Get the user feature usage metrics
    - get_td_dba_userDelay - Get the Teradata user delay metrics.
    - get_td_dba_tableUsageImpact - measures the usage of a table / view by a user

    - prompt_td_dba_tableArchive - Create a table archive strategy for database tables.
    - prompt_td_dba_databaseLineage - Creates a directed lineage map of tables in a database.
    - prompt_td_dba_tableDropImpact - assesses the impact of a table being dropped

3. td_qlty tools / prompts / resources:
    - get_td_qlty_missingValues - returns a list of column names with missing values
    - get_td_qlty_negativeValues - returns a list of column names with negative values
    - get_td_qlty_distinctCategories - returns a list of categories within a column
    - get_td_qlty_standardDeviation - returns the mean and standard deviation for a column

You may add define custom "query" tools in the `custom_tools.yaml` file or in any file ending with `_tools.yaml`. 
Simply specify the tool name, description and SQL query to be executed. No parameters are supported at this point.

The Test directory contains a simple ClientChatBot tool for testing tools.

--------------------------------------------------------------------------------------
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
.venv/Scripts/activate
```

On Mac/Linux
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

- LLM Credentials need to be available for test code to work

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

--------------------------------------------------------------------------------------
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

### Running the server
You can simply run the server with:
`uv run teradata-mcp-server`

### Adding your sever to an Agent using stdio
#### Option 1 - pydanticai chatbot
&nbsp;&nbsp;&nbsp;&nbsp; step 1 - confirm the SSE flag in .env file has been set to False
```
SSE=False
```
&nbsp;&nbsp;&nbsp;&nbsp; Step 2 - Modify the ./test/ClientChatBot.py script to point to where you installed the server, you will need to modify the following line
```
    td_mcp_server = MCPServerStdio('uv', ["--directory", "/Users/Daniel.Tehan/Code/MCP/teradata-mcp-server", "run", "teradata-mcp-server"])
```

&nbsp;&nbsp;&nbsp;&nbsp; Step 3 - run the ./test/ClientChatBot.py script, this will create an interactive session with the agent who has access to the MCP server.  From a terminal.
```
uv run ./test/ClientChatBot.py
```

- Ask the agent to list the databases
- Ask the agent to list the table in a database
- Ask the agent to show all the objects in a database
- Ask the agent a question that requires SQL to run against a table
- Type "quit" to exit.

#### Option 2 - ADK Chatbot
&nbsp;&nbsp;&nbsp;&nbsp; step 1 - confirm the SSE flag in .env file has been set to False
```
SSE=False
```
&nbsp;&nbsp;&nbsp;&nbsp; Step 2 - move into teradata_mcp_server/test directory From a terminal.
```
cd test
adk web
```
&nbsp;&nbsp;&nbsp;&nbsp; Step 3 - open [ADK Web Server ](http://0.0.0.0:8000) 

&nbsp;&nbsp;&nbsp;&nbsp; Step 4 - chat with the td_agent

#### Option 3 - mcp_chatbot

&nbsp;&nbsp;&nbsp;&nbsp; step 0 - Modify server_config.json in the test directory, ensure path is correct.

&nbsp;&nbsp;&nbsp;&nbsp; step 1 - confirm the SSE flag in .env file has been set to False
```
SSE=False
```
&nbsp;&nbsp;&nbsp;&nbsp;Step 2 - move into teradata_mcp_server directory From a terminal and run the mcp_chatbot
```
uv run test/mcp_chatbot.py
```
&nbsp;&nbsp;&nbsp;&nbsp;Step 3 - list the prompts by typing /prompts
```
Query: /prompts
```
&nbsp;&nbsp;&nbsp;&nbsp;Step 4 - running a prompt to describe a database
```
Query: /prompt prompt_td_base_databaseBusinessDesc database_name=demo_user
```



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

Note: you will need to modify the directory path in the args for your system, this needs to be a complete path.  You may also need to have a complete path to uv in the command as well.
```
    "mcp": {
        "servers": {
            "teradataStdio": {
                "type": "stdio",
                "command": "uv",
                "args": [
                    "--directory",
                    "/Users/Daniel.Tehan/Code/MCP/teradata-mcp-server",
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

### Adding tools using SSE to Visual Studio Code Co-pilot
- confirm the SSE flag in .env file has been set to False
```
SSE=True
SSE_HOST=127.0.0.1
SSE_PORT=8001
```
- you need to start the server from a terminal
```
uv run teradata-mcp-server
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
            "teradataSSE": {
                "type": "sse",
                "url": "http://127.0.0.1:8001/sse",
                "env": {
                    "DATABASE_URI": "teradata://username:password@host:1025/databasename"
                }
            }
        }
    }
```
- within the settings.json file or you can "MCP: Start Server"  

### Adding the MCP server to Claude Desktop
You can add this server Claude desktop adding this entry to your `claude_desktop_config.json` config file:

Note: you will need to modify the directory path in the args for your system, this needs to be a complete path.  You may also need to have a complete path to uv in the command as well.

Note: this requires that `uv` is available to Claude in your system path or installed globally on your system (eg. uv installed with `brew` for Mac OS users).

```
{
  "mcpServers": {
    "teradataStdio": {
      "command": "uv",
      "args": [
        "--directory",
        "/path_to_code/teradata-mcp-server",
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



### Exposing tools as REST endpoints with mcpo
You can use [mcpo](https://github.com/open-webui/mcpo) to expose this MCP tool as an OpenAPI-compatible HTTP server.

For example, using uv:
`uvx mcpo --port 8001 --api-key "top-secret" -- uv run teradata-mcp-server`

Your Teradata tools are now available as local REST endpoints, view documentation and test it at http://localhost:8001/docs

### Using the server with Open WebUI
[Open WebUI](https://github.com/open-webui/open-webui) is user-friendly self-hosted AI platform designed to operate entirely offline, supporting various LLM runners like Ollama. It provides a convenient way to interact with LLMs and MCP servers from an intuitive GUI. It can be integrated with this MCP server using the [mcpo](https://github.com/open-webui/mcpo) component.

First run mcpo as specified [in the section above](#exposing-tools-as-rest-endpoints-with-mcpo).

```
python -m venv ./env
source ./env/bin/activate
pip install open-webui   
open-webui serve
```

Access the UI at http://localhost:8080.
To add the MCP tools, navigate to Settings > Tools > Add Connection, and enter your mcpo server connection details (eg. `localhost:8001`, password = `top-secret` if you have executed the command line in the mcpo section).

You should be able to see the tools in the Chat Control Valves section on the right and get your models to use it.

---

## Docker & Docker Compose Usage

### Build the Docker image

```sh
docker compose build
```

The server expects the Teradata URI string via the `DATABASE_URI` environment variable. You may update the `docker-compose.yaml` file or setup the environment variable with your system's connection details:

`export DATABASE_URI=teradata://username:password@host:1025/databasename`

### Run the MCP server (default)

This starts only the core Teradata MCP server (with stdio or SSE communication):

```sh
docker compose up
```

The server will be available on port 8080 (or the value of the `PORT` environment variable).

### Run the REST API server (mcpo) as an option

To expose your tools as REST endpoints via mcpo, use the `rest` profile.

You can set an API key using the environment variable `MCPO_API_KEY`. The default value is 'top-secret'.

```sh
docker compose --profile rest up
```

You can now access the OpenAPI docs at: [http://localhost:8001/docs](http://localhost:8001/docs)

#### Environment Variables
- Set `DATABASE_URI` in your environment or in a `.env` file in the project root.
- Only `DATABASE_URI` is required for the REST server.

#### Example `.env` file
```
DATABASE_URI=teradata://username:password@host:1025/databasename
```

---

For more details on mcpo, see: https://github.com/open-webui/mcpo

---------------------------------------------------------------------
## Certification
<a href="https://glama.ai/mcp/servers/@Teradata/teradata-mcp-server">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@Teradata/teradata-mcp-server/badge" alt="Teradata Server MCP server" />
</a>
