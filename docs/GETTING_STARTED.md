# MCP Server - Getting Started

![Getting Started]![alt text](media/client-server-platform.png)

This document will cover the process and options for getting the teradata-mcp-server up and running

Assumes that you have a running Teradata environment, you should have the following information for your Teradata system:
1. host address - IP address or DNS address for the location of the server
2. user name - name you log into the teradata system with
3. user password - password for the corresponding user name
4. database - On Teradata systems this is typically the same as you user name

## Step 1: Installing the server

You have multiple deployment methods for this server.
1. [Install as a tool with uv (preferred)](#method-1-install-as-a-tool-with-uv-preferred) – fast, isolated, and does not pollute system Python.
2. [PyPI with pip in a virtualenv](#method-2-pypi-installation-with-pip) – classic Python install.
3. [Build from Source with uv](#method-3-build-from-source-with-uv-development) – for development.
4. [Using Docker](#using-docker) – for containerized deployments and REST API.

### Method 1: Install as a tool with uv (preferred)

Why uv? It installs CLI tools into isolated environments, is very fast, and avoids polluting your global Python/site‑packages.

Prerequisite: install uv (macOS: `brew install uv`, Windows: `winget install astral-sh.uv`).

Install the CLI tool from PyPI:
```bash
uv tool install "teradata-mcp-server"
```

Optional extras (Enterprise Feature Store, Enterprise Vector Store):
```bash
uv tool install "teradata-mcp-server[fs,evs]"
```

Upgrade later:
```bash
uv tool upgrade teradata-mcp-server
```

### Method 2: PyPI installation with pip

Recommended inside a virtual environment (venv):
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install --upgrade pip
pip install teradata-mcp-server
```

Install with extras:
```bash
pip install "teradata-mcp-server[fs,evs]"
```

### Method 3: Build from Source with uv (Development)

For development, customization, or to access the latest features:

**Step 0 - Installing development environment**
- [Git](https://git-scm.com/) for cloning the repository
- [uv package manager](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer) for dependency management
- Python 3.11 or greater ([Python.org](https://www.python.org/downloads/))

**Step 1 - Download the Software**
Clone the repository:

```bash
git clone https://github.com/Teradata/teradata-mcp-server.git
cd teradata-mcp-server
```

To stay up to date with the latest changes:
```bash
cd teradata-mcp-server
git pull origin main
```

## Step 2 - Adding modules (optional)

The server supports optional modules for additional functionality:
- **`fs`** - Teradata Enterprise Feature Store integration
- **`evs`** - Teradata Enterprise Vector Store integration

### With Source Build:
```bash
uv sync --extra fs --extra evs
```

## Step 3 - Run your server

We support three communication prototcols:

1. **Streamable-http (http)** - Communicates over HTTP, recommended for most use cases.
2. **Standard IO (stdio)** - Communications via standard input/output, suitable for servers bundled within the application and development.
3. **Server Side Events (SSE)** - Being deprecated by the MCP standard, not maintained.

**Prerequisites:** PyPI installation completed (Method 1 above)

**Configuration:**
We recommend that you store the pass the database credentials as an environment variable:

```bash
# Required: Database connection
export DATABASE_URI="teradata://username:password@host:1025/database"
```

**Run the server over http:**

```bash
teradata-mcp-server --mcp_transport streamable-http --mcp_host 127.0.0.1 --mcp_port 8001
```

or with uv:

```bash
uv run teradata-mcp-server --mcp_transport streamable-http --mcp_host 127.0.0.1 --mcp_port 8001
```

The server will be available at `http://127.0.0.1:8001/mcp/`

**Run the server over stdio:**

This is the default mode:

```bash
teradata-mcp-server
```

or with uv:

```bash
uv run teradata-mcp-server
```

**Available built-in profiles:**

We have a set of profiles pre-defined that expose a subset of MCP tools for different use cases:

- `all` - All tools and resources available (excludes test prompts)
- `tester` - Everything available including test prompts (for development/testing)
- `dba` - Database administration tools (dba_*, base_*, sec_* tools and dba prompts)
- `dataScientist` - Data science focused (base, rag, fs, qlty tools plus user permissions)
- `eda` - Exploratory Data Analysis (base tools except write operations, data quality tools)
- `custom` - Custom tools only (cust* tools/prompts/resources plus basic database listing)
- `sales` - Sales-specific tools, prompts, and resources

```bash
# Use a built-in profile
teradata-mcp-server --profile dba

# Use a data science profile
teradata-mcp-server --profile dataScientist
```

**Creating custom profiles:**

You can define your own profile by creating a profiles.yml in your working directory.

Custom profiles can include a `run` section that provides default values for command-line arguments.

```yaml
# profiles.yml example
analyst_dev:
  tool: [".*"]
  prompt: [".*"] 
  resource: [".*"]
  run:
    database_uri: "teradata://dev_user:dev_password@localhost:1025/dev_db"
    mcp_transport: "http-streamable"
    mcp_port: 8002

analyst_prod:
  tool: [".*"]
  prompt: [".*"] 
  resource: [".*"]
  run:
    database_uri: "${PROD_DB_URI}"
    mcp_transport: "http-streamable"
    mcp_port: 8001
```

```bash
teradata-mcp-server --profile analyst_dev
```

**Configuration Priority** (highest to lowest):
1. **CLI arguments** - `--database-uri`, `--mcp-port`, etc.
2. **Profile run section** - Values from `run:` in selected profile
3. **Environment variables** - `DATABASE_URI`, `MCP_PORT`, etc. 
4. **Script defaults** - Built-in default values

See [Configuration Examples](../examples/server-customization/) for complete examples.

**Creating custom tools, prompts and resources:**

We made it very simple to add custom objects to you server, refer to the [Customizing](CUSTOMIZING.md) instructions for more details.

You are now ready to connect your client. For details on client setup, refer to [Working with Clients](client_guide/CLIENT_GUIDE.md)

-------------------------------------------------------------------------------------- 


--------------------------------------------------------------------------------------

## Using Docker

You can use Docker to run the MCP server in streamable-http mode.

The server expects the Teradata URI string via the `DATABASE_URI` environment variable. You may:
- update the `docker-compose.yaml` file or 
- setup the environment variable with your system's connection details:

`export DATABASE_URI=teradata://username:password@host:1025/databaseschema`


```sh
docker compose up
```

To include optional modules or specify a profile, set environment variables:

```sh
# Build with Feature Store and Vector Store support
ENABLE_FS_MODULE=true ENABLE_EVS_MODULE=true docker compose build
docker compose up

# Run with a specific profile (e.g., 'dba')
PROFILE=dba docker compose up

# Combine optional modules and profile
ENABLE_FS_MODULE=true PROFILE=dba docker compose build
PROFILE=dba docker compose up
```

The server will be available on port 8001 (or the value of the `PORT` environment variable).

You are now ready to connect your client. For details on how to set up client tools, refer to [Working with Clients](client_guide/CLIENT_GUIDE.md)
<br><br><br>

--------------------------------------------------------------------------------------
## Development Environment Set Up with uv

Make sure you have uv installed on your system, installation instructions can be found at https://github.com/astral-sh/uv .

**Step 1** - Clone the mcp-server repository, sync the necessary libraries, and activate the environment with

On Windows
```
cd teradata-mcp-server
uv sync
.venv/Scripts/activate
```

On Mac/Linux
```
cd teradata-mcp-server
uv sync
source .venv/bin/activate
```

**Step 2** - Configure the server
For convenience, you can define your preferred configuration in a .env file at the project root (you can use the provided [env](../env) file and rename it).

1. **DATABASE_URI**

This is the database connection string using the following format:  `teradata://username:password@host:1025/[schemaname]`

2. **LOGMECH**

This is the login mechansim: TD or LDAP

3. **MCP_TRANSPORT**

The server will connect to your Teradata instance and to the clients using one of the following transport modes 
- Standard IO (stdio)
- server-sent events (SSE)  
- streamable-http (streamable-http). 

4. **TD_POOL_SIZE**

The TD_POOL_SIZE defaults to 5, this is used in the connection to Teradata.

5. **TD_MAX_OVERFLOW**

The TD_MAX_OVERFLOW defaults to 10, this is used in the connection to Teradata.

6. **TD_POOL_TIMEOUT**

The TD_POOL_TIMEOUT defaults to 30, this is used in the connection to Teradata.

7. **MCP_HOST**

This is the host address used when using the sse or streamable-http transport modes, default = localhost (127.0.0.1)

8. **MCP_PORT**

This is the port address used when using the sse or streamable-http transport modes, default = 8001

9. **MCP_PATH**

This is the path used for streamable_http transport mode, default to `\mcp`

10. **Enterprise Vector Store**
These are the parameters required when using the enterprise vector store tools.

TD_BASE_URL=        #Your UES_URI, strip off the trailing /open-analytics
TD_PAT=             #Your PAT string
TD_PEM=             #Your PEM location
VS_NAME=            #Your target Vector Store Name


Minimum Configuration example:
```
export DATABASE_URI=teradata://username:password@host:1025/schemaname
export LOGMECH=LDAP

# Enables transport communication as stdio, sse, streamable-http
export MCP_TRANSPORT=streamable-http 
export MCP_HOST=127.0.0.1
export MCP_PORT=8001
export MCP_PATH=/mcp/
```

**Step 3** - Run the server with uv in a terminal

`uv run teradata-mcp-server --profile all`

You are now ready to connect your client. For details on how to set up client tools, refer to [Working with Clients](client_guide/CLIENT_GUIDE.md)

--------------------------------------------------------------------
## Exposing the MCP server via REST

Alternatively, you can expose your tools, prompts and resources as REST endpoints using the `rest` profile.

You can set an API key using the environment variable `MCPO_API_KEY`. 
Caution: there is no default value, not no authorization needed by default.

The default port is 8002.

**Using uv:**
```sh
export DATABASE_URI=teradata://username:password@host:1025/databaseschema
export MCPO_API_KEY=top-secret
export TRANSPORT=stdio
uvx mcpo --port 8002 --api-key "top-secret" -- uv run teradata-mcp-server 
```

or **using docker**:
```sh
export DATABASE_URI=teradata://username:password@host:1025/databaseschema
export MCPO_API_KEY=top-secret
docker compose --profile rest up
```

You are now ready to connect your client. For details on how to set up client tools, refer to [Working with Clients](client_guide/CLIENT_GUIDE.md)

---------------------------------------------------------------------
## Remote Production Deployment

For production deployments that serve multiple clients, you have two options:

1. **Docker deployment** - Containerized setup with automatic restarts (includes REST option)
2. **System service** - Background service using either:
   - **Direct execution** - `teradata-mcp-server` (after pip/uv install, recommended)
   - **uv-managed execution** - `uv run teradata-mcp-server` (with dependency management)

For remote access, use the `streamable-http` transport protocol which communicates over HTTP.

Before you deploy, define your security strategy and review the [security patterns we provide](SECURITY.md).

## Using Docker
If the server is using docker compose and you wish to have it automatically start on system reboot, add the following entry to the docker-compose.yaml file to either or both service entries (```teradata-mcp-server:```, ```teradata-rest-server:```)
```sh
services:
  teradata-mcp-server:
    build: .
    image: teradata-mcp-server:latest
    restart: always
```

### System service
Configure the MCP server to run as a systemd service for automatic startup and management.

1. Create a service file in /etc/systemd/system/ named ```<your service name>.service```, e.g. ```teradata_mcp.service```
2. Copy the following configuration - modify for your environment:
```sh
[Unit]
Description=Teradata MCP Server
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=1
User=your-username
Environment=DATABASE_URI=teradata://username:password@host:1025/database
Environment=MCP_TRANSPORT=streamable-http
Environment=MCP_HOST=127.0.0.1
Environment=MCP_PORT=8001
ExecStart=/usr/local/bin/teradata-mcp-server --profile all

[Install]
WantedBy=multi-user.target
```
3. Run ```sudo systemctl start <your service name>.service``` to start the service
4. Run ```sudo systemctl status <your service name>.service``` to check status
5. Run ```sudo systemctl enable <your service name>.service``` to enable start on system boot
6. To be safe, test increasing restart intervals for stability.  Create a crontab for the service:
7. ```sudo crontab -e```
8. ```0 * * * * /bin/systemctl restart <your service name>.service```

You are now ready to connect your client. For details on how to set up client tools, refer to [Working with Clients](client_guide/CLIENT_GUIDE.md)

## Testing your server

Connect your preferred client, and validate that you see the server tools, prompts and resources.

If you want to rapidly check what's available, and does work or not, we provide an interactive testing method via the prompt `_testMyServer`. Simply load the prompt, specify a functional domain that you wish to test (or "all") and run.

This is a good way to validate and explore your setup, but not sufficent to carry actual unit or system testing.
