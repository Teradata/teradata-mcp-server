# Teradata MCP Server

## Overview
The Teradata MCP server provides a set of tools and prompts for interacting with Teradata databases, enabling AI agents and users to query, analyze, and manage their data efficiently. 

This is an open project and we welcome contributions via pull requests.

## TLDR; I want to try it locally now

If you have Docker and a client that can connect MCP servers via SSE, copy the code below, update the connection string set in `DATABASE_URI` with your database connection details and run it:

```
export DATABASE_URI=teradata://username:password@host:1025
git clone https://github.com/Teradata/teradata-mcp-server.git
cd teradata-mcp-server
docker compose up
```

You can now use it with clients supporting SSE such as [Visual Studio Code](#using-with-visual-studio-code-co-pilot).

## Key features

### Available tools and prompts

We are providing three sets of tools and associated helpful prompts
- **Base** tools, prompts and resources to interact with your Teradata platform:
- **DBA** tools, prompts and resources to facilitate your platform administration tasks:
- **Data Quality** tools, prompts and resources accelerate exploratory data analysis:
- **Custom Tools** to easily implement tools for custom actions based on your data and business context 

**Base** tools:

  - get_base_readQuery - runs a read query
  - write_base_writeQuery - runs a write query
  - get_base_tableDDL - returns the show table results
  - get_base_databaseList - returns a list of all databases
  - get_base_tableList - returns a list of tables in a database
  - get_base_columnDescription - returns description of columns in a table
  - get_base_tablePreview - returns column information and 5 rows from the table
  - get_base_tableAffinity - gets tables commonly used together
  - get_base_tableUsage - Measure the usage of a table and views by users in a given schema

**Base** Prompts:

  - base_query - Create a SQL query against the database
  - base_tableBusinessDesc - generates a business description of a table
  - base_databaseBusinessDesc - generates a business description of a databases based on the tables

**DBA** tools:

- get_dba_userSqlList - returns a list of recently executed SQL for a user
- get_dba_tableSqlList - returns a list of recently executed SQL for a table
- get_dba_tableSpace - returns CurrentPerm table space 
- get_dba_databaseSpace - returns Space allocated, space used and percentage used for a database
- get_dba_databaseVersion - returns the database version information
- get_dba_resusageSummary - Get the Teradata system usage summary metrics by weekday and hour for each workload type and query complexity bucket.
- get_dba_resusageUserSummary - Get the system usage for a user
- get_dba_flowControl - Get the Teradata system flow control metrics by day and hour
- get_dba_featureUsage - Get the user feature usage metrics
- get_dba_userDelay - Get the Teradata user delay metrics.
- get_dba_tableUsageImpact - measures the usage of a table / view by a user

**DBA** prompts:

- dba_databaseHealthAssessment - Create a database health assessment for a Teradata system
- dba_userActivityAnalysis - Create a user activity analysis for a Teradata system
- dba_tableArchive - Create a table archive strategy for database tables.
- dba_databaseLineage - Creates a directed lineage map of tables in a database.
- dba_tableDropImpact - assesses the impact of a table being dropped

**Data Quality** tools:

- get_qlty_missingValues - returns a list of column names with missing values
- get_qlty_negativeValues - returns a list of column names with negative values
- get_qlty_distinctCategories - returns a list of categories within a column
- get_qlty_standardDeviation - returns the mean and standard deviation for a column

### Adding custom tools
You may add define custom "query" tools in the `custom_tools.yaml` file or in any file ending with `_tools.yaml`. 
Simply specify the tool name, description and SQL query to be executed. No parameters are supported at this point.

The Test directory contains a simple ClientChatBot tool for testing tools.

--------------------------------------------------------------------------------------
## Environment Set Up

If you do not have a Teradata system, get a sandbox for free and right away at [ClearScape Analytics Experience](https://www.teradata.com/getting-started/demos/clearscape-analytics)!


The two recommended ways to run this server are using uv and Docker. 

[Jump to next section](#using-docker) for the docker option.

### Using uv

Make sure you have uv installed on your system, installation instructions can be found at https://github.com/astral-sh/uv .

**Step 1** - Clone the mcp-server repository with 

On Windows
```
git clone https://github.com/Teradata/teradata-mcp-server.git
cd teradata-mcp-server
uv sync
.venv/Scripts/activate
```

On Mac/Linux
```
git clone https://github.com/Teradata/teradata-mcp-server.git
cd teradata-mcp-server
uv sync
source .venv/bin/activate
```

**Step 2** - Configure the server

The server will connect to your Teradata instance and to the clients over stdio (default) or server-sent events (SSE) or streamable-http. To configure the connections set the following environment variables in your shell or in a .env file in the current directory (by updating and renaming the provided [env](./env) file).

**Database connection string** with the following format: `teradata://username:password@host:1025/[schemaname]`

Replace `username`, `password`, `host` with your systems and credential details, set default schema with `schemaname`


**Optionally, for transport connectivity**, SSE transport is in the process of being decommissioned and replaces with streamable-http, we will continue to support SSE for the moment. Set `MCP_TRANSPORT` to `sse` and your host IP and port number with `MCP_HOST` (defaults to `127.0.0.1`) and `MCP_PORT` (defaults to `8001`):

**Optionally, for transport connectivity**, set `MCP_TRANSPORT` to `streamable-http` and your host IP and port number with `MCP_HOST` (defaults to `127.0.0.1`) and `MCP_PORT` (defaults to `8001`) and `MCP_PATH` (defaults to `/mcp/`):

Configuration example:
```
export DATABASE_URI=teradata://username:password@host:1025/schemaname

# Enables transport communication as stdio, sse, streamable-http
export MCP_TRANSPORT=stdio 
export MCP_HOST=127.0.0.1
export MCP_PORT=8001
export MCP_PATH=/mcp
```

**Step 3** - Run the server with uv

`uv run teradata-mcp-server`

--------------------------------------------------------------------------------------
## Using Docker

Clone this repository
```
git clone https://github.com/Teradata/teradata-mcp-server.git
cd teradata-mcp-server
```

The server expects the Teradata URI string via the `DATABASE_URI` environment variable. You may update the `docker-compose.yaml` file or setup the environment variable with your system's connection details:

`export DATABASE_URI=teradata://username:password@host:1025/databaseschema`

### Run the MCP server with SSE (default)

This starts only the core Teradata MCP server (with stdio or SSE communication):

```sh
docker compose up
```

The server will be available on port 8001 (or the value of the `PORT` environment variable).

### Run the MCP server with REST

Alternatively, you can expose your tools, prompts and resources as REST endpoints using the `rest` profile.

You can set an API key using the environment variable `MCPO_API_KEY`. 
Caution: there is no default value, not no authorization needed by default.

The default port is 8002.

```sh
export MCPO_API_KEY=top-secret
docker compose --profile rest up
```

## Using with Visual Studio Code Co-pilot

Visual Studio Code Co-pilot provides a simple and interactive way to test this server. 
Follow the instructions below to run and configure the server, set co-pilot to Agent mode, and use it.

![alt text](./documentation/media/copilot-agent.png)

Detailed instructions on configuring MCP server with Visual Studio Code can be found [in Visual Studio Code documentation](https://code.visualstudio.com/docs/copilot/chat/mcp-servers).


### Using Server-Sent Events (SSE) (recommended)

You can use uv or Docker to start the server.

Using uv, ensure that SSE is enabled (not by default) and the host port are defined. You can do this with setting the environment variables below or in the `.env` file):

```
export MCP_TRANSPORT=sse
export MCP_HOST=127.0.0.1
export MCP_PORT=8001

uv run teradata-mcp-server
```

Alternatively, start with Docker (defaults to SSE):

```
docker compose up
```

Add the server in VS Code:

- Open the Command Palette (View>Command Palette)
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
                "url": "http://127.0.0.1:8001/sse"
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


## Using with Claude Desktop
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


## Using with AI Agents (stdio version)
### Option 1 - pydanticai chatbot
&nbsp;&nbsp;&nbsp;&nbsp; step 1 - confirm the MCP_TRANSPORT=stdio  in .env file 
```
MCP_TRANSPORT=stdio
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

### Option 2 - ADK Chatbot
&nbsp;&nbsp;&nbsp;&nbsp; step 1 - confirm the MCP_TRANSPORT=stdio  in .env file 
```
MCP_TRANSPORT=stdio
```
&nbsp;&nbsp;&nbsp;&nbsp; Step 2 - move into teradata_mcp_server/test directory From a terminal.
```
cd test
adk web
```
&nbsp;&nbsp;&nbsp;&nbsp; Step 3 - open [ADK Web Server ](http://0.0.0.0:8000) 

&nbsp;&nbsp;&nbsp;&nbsp; Step 4 - chat with the td_agent

### Option 3 - mcp_chatbot

&nbsp;&nbsp;&nbsp;&nbsp; step 0 - Modify server_config.json in the test directory, ensure path is correct.

&nbsp;&nbsp;&nbsp;&nbsp; step 1 - confirm the MCP_TRANSPORT=stdio  in .env file 
```
MCP_TRANSPORT=stdio
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
Query: /prompt base_databaseBusinessDesc database_name=demo_user
```


## Using with any tool: REST interface 
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

## Using with Open WebUI
[Open WebUI](https://github.com/open-webui/open-webui) is user-friendly self-hosted AI platform designed to operate entirely offline, supporting various LLM runners like Ollama. It provides a convenient way to interact with LLMs and MCP servers from an intuitive GUI. It can be integrated with this MCP server using the REST endpoints.

Run the MCP server as a REST server [in the section above](#using-with-any-tool-rest-interface).

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


You can now access the OpenAPI docs at: [http://localhost:8002/docs](http://localhost:8002/docs)


---

For more details on mcpo, see: https://github.com/open-webui/mcpo

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

---------------------------------------------------------------------
## Certification
<a href="https://glama.ai/mcp/servers/@Teradata/teradata-mcp-server">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@Teradata/teradata-mcp-server/badge" alt="Teradata Server MCP server" />
</a>