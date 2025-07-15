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
