# Working with MCP Clients

![Getting Started](media/MCP.png)

This documet will cover the process and options for getting a client tool to connect to the teradata-mcp-server.  Note that you have many client options, we will cover some but not all.

The transport mode that the server is running needs to be the same as the client configuration.

![Client Server](media/clientServer.png)

If you configured the server as a Streamable-http transport mode then the client also needs to be configured as a streamable-http mode.


## Using with Claude Desktop

[Claude Desktop Instructions](https://modelcontextprotocol.io/quickstart/user)

Step1 - Modify your claude desktop configuration file -  `claude_desktop_config.json` config file:

**Streamable-http**

Example can be found in [claude_desktop_http_config](../test/Claude_Desktop_Config_Files/claude_desktop_http_config)

Note: you may need to modify the host in the args.


**Stdio**

Example can be found in [claude_desktop_stdio_config](../test/Claude_Desktop_Config_Files/claude_desktop_stdio_config)

Note: you will need to modify the directory path in the args for your system, this needs to be a complete path.  You may also need to have a complete path to uv in the command as well.

Note: this requires that `uv` is available to Claude in your system path or installed globally on your system (eg. uv installed with `brew` for Mac OS users).

**SSE**

Example can be found in [claude_desktop_SSE_config](../test/Claude_Desktop_Config_Files/claude_desktop_SSE_config)

Note: you may need to modify the host in the args.

<br><br>

## Using with Microsoft Copilot

Instructions are being worked on

<br><br>

## Using Google Agent Space

Instructions are beig worked on

<br>
<br>

# Testing Clients

There are a number of way to test a MCP server.


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

<br><br>

## Using with Visual Studio Code Co-pilot

Visual Studio Code Co-pilot provides a simple and interactive way to test this server. 
Follow the instructions below to run and configure the server, set co-pilot to Agent mode, and use it.

![alt text](media/copilot-agent.png)

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

docker compose up
```

Add the server in VS Code:

- Open the Command Palette (View>Command Palette)
- select "MCP: Add Server"
- select "HTTP or Server Sent Events"
- enter URL for the location of the server e.g. http://127.0.0.1:8001/mcp
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

<br><br>

## Using with Google ADK AI Agents (streamable-http version)

All the client tools below leverage a Large Language Model, the code provided as examples in the test directory assumes you have set up the environment variables for your model.  Alternatively you should add them to your .env file.

```
############################################
# These are only required for testing the server 
############################################
aws_role_switch=False
aws_access_key_id=
aws_secret_access_key=
aws_session_token=
aws_region=

############################################
OPENAI_API_KEY=

############################################
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=

############################################
azure_api_key=
azure_gpt-4o-mini=

############################################
ollama_api_base= 

```


<br><br>

### Option 1 - ADK Chatbot
&nbsp;&nbsp;&nbsp;&nbsp; step 1 - confirm the following is in .env file 
```
MCP_TRANSPORT=streamable-http
MCP_HOST=127.0.0.1
MCP_PORT=8001
MCP_PATH=/mcp/
```
&nbsp;&nbsp;&nbsp;&nbsp; Step 2 - move into teradata-mcp-server directory From a terminal and start the server.
```
cd teradata-mcp-server
uv run src/teradata_mcp-server
```
&nbsp;&nbsp;&nbsp;&nbsp; Step 3 - move into teradata_mcp_server/test/ADK_Client_Example directory From a terminal.
```
cd test
adk web
```
&nbsp;&nbsp;&nbsp;&nbsp; Step 4 - open [ADK Web Server ](http://0.0.0.0:8000) 

&nbsp;&nbsp;&nbsp;&nbsp; Step 5 - chat with the Simple_Agent or DBA_Agent

<br><br>

### Option 2 - mcp_chatbot

&nbsp;&nbsp;&nbsp;&nbsp; step 0 - Modify server_config.json in the test directory, ensure path is correct.

&nbsp;&nbsp;&nbsp;&nbsp; step 1 - confirm the following is in .env file 
```
MCP_TRANSPORT=streamable-http
MCP_HOST=127.0.0.1
MCP_PORT=8001
MCP_PATH=/mcp/
```
&nbsp;&nbsp;&nbsp;&nbsp; Step 2 - move into teradata-mcp-server directory From a terminal and start the server.
```
cd teradata-mcp-server
uv run src/teradata_mcp-server
```

&nbsp;&nbsp;&nbsp;&nbsp;Step 3 - move into teradata_mcp_server directory From a terminal and run the mcp_chatbot
```
uv run test/MCP_Client_Example/mcp_chatbot.py
```
&nbsp;&nbsp;&nbsp;&nbsp;Step 4 - list the prompts by typing /prompts
```
Query: /prompts
```
&nbsp;&nbsp;&nbsp;&nbsp;Step 5 - running a prompt to describe a database
```
Query: /prompt base_databaseBusinessDesc database_name=demo_user
```


<br><br>

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

<br><br>

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




You can now access the OpenAPI docs at: [http://localhost:8002/docs](http://localhost:8002/docs)



For more details on mcpo, see: https://github.com/open-webui/mcpo

---------------------------------------------------------------------

## Using with gemini-cli
1.	Make sure you have Teradata database access. (the most convenient way: Go to https://clearscape.teradata.com create account and login, start the environment and click on Run Demo)
2.	Go to https://github.com/Teradata/teradata-mcp-server run below lines in cmd terminal. (once build finished, you should see Teradata-mcp-server image in your docker desktop)
    * ```export DATABASE_URI=teradata://username:password@host:1025``` (use the username, password, host from above clearscape step)
    * ```git clone https://github.com/Teradata/teradata-mcp-server.git```
    * ```cd teradata-mcp-server```
    * ```docker compose up```
3.	Go to https://github.com/google-gemini/gemini-cli follow instruction to install
    * For authenticate, please use personal google email.
4.	Go to your project folder, create ```.gemini/settings.json``` accordingly
```
{
    "theme": "Default",
    "selectedAuthType" : "oauth-personal",

    "mepServers": {
        "teradatasse": {
            "type": "sse" ,
            "url" : "http://127.0.0.1:8001/SSe"
        }
    }
}
```
5. Open a cmd terminal, type ```gemini``` and hit enter, now you should see gemini-cli interface.
