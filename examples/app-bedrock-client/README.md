# Simple Agent using mcp client framework (stdio version)

This is a simple agent developed with the mcp client framework that can use LLM.

A command line experience.

## Features
- Command line chat interface
- Access to all tools
- Access to all prompts
- Access to all resources


## Prerequisites

- Installed teradata-mcp-server
- LLM access
    - AWS 
        - Account with Bedrock access
        - AWS CLI configured with appropriate credentials

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
```

4. Modify server_config.json file

- Modify the Path, so that the complete path to your server is defined
- Modify the DATABASE_URI, so that your connection string to Teradata is valid

<br><br>

## Usage 
1. confirm the following is in .env file 
```
MCP_TRANSPORT=stdio
```

2. In a termial start the server.
```
uv run examples/MCP_Client_Example/mcp_chatbot.py
```

3. list the prompts by typing /prompts
```
Query: /prompts
```

4. running a prompt to describe a database
```
Query: /prompt base_databaseBusinessDesc database_name=demo_user
```




