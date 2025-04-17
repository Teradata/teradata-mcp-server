
# Teradata MCP Server Template

This code will form the basis for building Teradata MCP servers.


### Environment Set Up
Step 1 - The environment has been put together assuming you have the uv package installed on your local machine.  Installation instructions for uv can be found at https://github.com/astral-sh/uv 

Step 2 - Clone the mcp-server repository with 

```
mkdir MCP
cd MCP
git clone https://github.com/Teradata/mcp-server.git
uv sync
```

Step 3 - You need to update the .env file
- The database URI will have the following format  teradata:/username:password@host:1025/databasename
    - the usename needs updating
    - the password needs updating
    - the Teradata host needs updating
    - the databasename needs updating

- LLM Credentials need to be available for pydantic-ai-example.ipynb code to work



