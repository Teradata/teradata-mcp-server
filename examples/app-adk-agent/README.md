# Simple Agent - Using Google ADK framework (streamable-http version)

This is a simple agent developed with the Google ADK framework that can use LLM.

The ADK framework provides a simple user experience with adk web functionality.

## Features
- Chat interface
- Access to all tools
- visibility into LLM messages 
- visibility into componenet execution time


## Prerequisites

- Python 3.13
- LLM access (one of the following)
    - AWS 
        - Account with Bedrock access
        - AWS CLI configured with appropriate credentials
    - Google
        - Google account with API key
    - Azure
        - Azure account with credentials
        - Azure model API key
    - Ollama
        - Ollama installed with MCP compliant model

- Teradata MCP server and Teradata system.

## Installation

1. Install all client dependencies:

With the server virtual environment activated, install the required packages:

```bash
uv pip install -r examples/MCP_Client_Example/requirements.txt --force-reinstall
```

2. Configure Client Credentials:

Assumes you have set up the environment variables for your model.  Alternatively you should add them to your .env file.

```
# When using AWS 
aws_role_switch=False
aws_access_key_id=
aws_secret_access_key=
aws_session_token=
aws_region=

# When using OpenAI 
OPENAI_API_KEY=

# When using Google
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=

# When using Azure 
azure_api_key=
azure_gpt-4o-mini=

# When using Ollama
ollama_api_base= 

```

4. Modify agent.py file lines 55 - 78 to reflect the LLM model you are using. Default is usig AWS, to change, comment out the AWS model definition and uncomment the model you would like to use.

<br><br>

## Usage 
1. confirm the following is in .env file 
```
MCP_TRANSPORT=streamable-http
MCP_HOST=127.0.0.1
MCP_PORT=8001
MCP_PATH=/mcp/
```

2. In a termial start the server.
```
cd teradata-mcp-server
uv run src/teradata_mcp_server/server.py
```

3. In a second terminal start the client.
```
cd teradata-mcp-server
source .venv/bin/activate
cd examples
adk web
```

4. open [ADK Web Server ](http://0.0.0.0:8000) 

5. Select the Simple_Agent 

6. Chat with the agent




