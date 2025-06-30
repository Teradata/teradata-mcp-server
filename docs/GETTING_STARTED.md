# Getting Started

--------------------------------------------------------------------------------------
## Environment Set Up 

If you do not have a Teradata system, get a sandbox for free and right away at [ClearScape Analytics Experience](https://www.teradata.com/getting-started/demos/clearscape-analytics)!


The two recommended ways to run this server are using uv or Docker. 

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
To configure the connections set the following environment variables in your shell or in a .env file in the current directory (by updating and renaming the provided [env](./env) file).

1. **DATABASE_URI**

This is the database connection string using the following format:  `teradata://username:password@host:1025/[schemaname]`

2. **LOGMECH**

This is the login mechansim: TD or LDAP

3. **MCP_TRANSPORT**

The server will connect to your Teradata instance and to the clients using one of the following transport modes 
- Standard IO (stdio)
- server-sent events (SSE)  
- streamable-http (streamable-http). 

4. **MCP_HOST**

This is the host address used when using the sse or streamable-http transport modes, default = localhost (127.0.0.1)

5. **MCP_PORT**

This is the port address used when using the sse or streamable-http transport modes, default = 8001

6. **MCP_PATH**

This is the path used for streamable_http transport mode, default to `\mcp`

7. **Enterprise Vector Store**
These are the parameters required when using the enterprose vector store tools.

TD_BASE_URL=        #Your UES_URI, strip off the trailing /open-analytics
TD_PAT=             #Your PAT string
TD_PEM=             #Your PEM location
VS_NAME=            #Your target Vector Store Name


Minimum Configuration example:
```
export DATABASE_URI=teradata://username:password@host:1025/schemaname
export LOGMECH=LDAP

# Enables transport communication as stdio, sse, streamable-http
export MCP_TRANSPORT=stdio 
export MCP_HOST=127.0.0.1
export MCP_PORT=8001
export MCP_PATH=/mcp/
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

---------------------------------------------------------------------
## Client set up

For details on how to set up client tools, refer to [Working with Clients](docs/CLIENT_GUIDE.md)

