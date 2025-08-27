# MCP Server - Getting Started

![Getting Started](media/MCP-quickstart.png)

This document will cover the process and options for getting the teradata-mcp-server up and running

Assumes that you have a running Teradata environment, you should have the following information for your Teradata system:
1. host address - IP address or DNS address for the location of the server
2. user name - name you log into the teradata system with
3. user password - password for the corresponding user name
4. database - On Teradata systems this is typically the same as you user name

## Installation Methods

### Method 1: PyPI Installation (Recommended)

The easiest way to get started is to install from PyPI:

**Step 0 - Prerequisites**
- Python 3.11 or greater ([Python.org](https://www.python.org/downloads/))

**Step 1 - Install the package**
```bash
pip install teradata-mcp-server
```

**Step 2 - Run the server**
```bash
# Set your database connection
export DATABASE_URI="teradata://username:password@host:1025/database"

# Run with all tools available
teradata-mcp-server --profile all
```

That's it! The server is now running with all default configurations included. Jump to [Step 3 - Choose Your Transport](#step-3---choose-your-transport) to configure how clients connect to your server.

### Method 2: Build from Source (Development)

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

## Step 2 - Customizing the server (optional)

The server supports optional modules for additional functionality:
- **`fs`** - Teradata Enterprise Feature Store integration
- **`evs`** - Teradata Enterprise Vector Store integration

### With PyPI Installation:
```bash
pip install teradata-mcp-server[fs,evs]
```

### With Source Build:
```bash
uv sync --extra fs --extra evs
```

Refer to the [Customizing](CUSTOMIZING.md) instructions for more details.

## Step 3 - Choose Your Transport

![Choice](media/transport.png) 

Transport Modes (in order of preference):
1. **Streamable-Http (http)** - Uses HTTP protocol for communication, recommended for production use
2. **Standard IO (stdio)** - Communications via standard input/output, suitable for standalone servers and development
3. **Server Side Events (SSE)** - Being deprecated by the MCP standard, not recommended

Deployment Options:
1. **PyPI Package** - Simple installation and configuration (recommended for most users)
2. **Docker Container** - Containerized deployment with managed dependencies
3. **UV Development** - Source-based development environment  
4. **REST** - RESTful API wrapper around the MCP server

Choose your preferred deployment method below:

## Step 4 - Starting your Server

You should pick one of the approaches below:
1. [PyPI Package with HTTP](#step-4a---pypi-package-with-http) - **Recommended for most users**
2. [Using Docker](#step-4b---using-docker) - Good for containerized deployments
3. [Using uv (Development)](#step-4c---uv-environment-set-up) - Good for developers
4. [Using REST](#step-4d---run-the-mcp-server-with-rest) - Good for REST API integration
5. [Running as a Service](#step-4e---run-the-mcp-server-as-a-service) - Good for production services

### Step 4a - PyPI Package with HTTP

**Prerequisites:** PyPI installation completed (Method 1 above)

**Configuration:**
```bash
# Required: Database connection
export DATABASE_URI="teradata://username:password@host:1025/database"

# Optional: Transport configuration (defaults shown)
export MCP_TRANSPORT=streamable-http
export MCP_HOST=127.0.0.1
export MCP_PORT=8001
export MCP_PATH=/mcp/
```

**Run the server:**
```bash
teradata-mcp-server --profile all --mcp_transport streamable-http --mcp_host 127.0.0.1 --mcp_port 8001
```

The server will be available at `http://127.0.0.1:8001/mcp/`

**With custom profiles:**
```bash
# Create custom profiles.yml in your working directory (optional)
# The server will merge it with packaged defaults

teradata-mcp-server --profile dba
```

You are now ready to connect your client. For details on client setup, refer to [Working with Clients](./client_guide/CLIENT_GUIDE.md)

-------------------------------------------------------------------------------------- 


--------------------------------------------------------------------------------------

### Step 4b - Using Docker

The server expects the Teradata URI string via the `DATABASE_URI` environment variable. You may:
- update the `docker-compose.yaml` file or 
- setup the environment variable with your system's connection details:

`export DATABASE_URI=teradata://username:password@host:1025/databaseschema`

Run the MCP server with Streamable-Http (default)

This starts only the core Teradata MCP server (with stdio or SSE communication):

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

You are now ready to connect your client, For details on how to set up client tools, refer to [Working with Clients](./client_guide/CLIENT_GUIDE.md)
<br><br><br>

--------------------------------------------------------------------------------------
### Step 4c - UV Environment Set Up (Development) 

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

You are now ready to connect your client, For details on how to set up client tools, refer to [Working with Clients](./client_guide/CLIENT_GUIDE.md)

--------------------------------------------------------------------
### Step 4d - Run the MCP server with REST

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

You are now ready to connect your client, For details on how to set up client tools, refer to [Working with Clients](./client_guide/CLIENT_GUIDE.md)

---------------------------------------------------------------------
### Step 4e - Run the MCP Server as a service
There are two options to configure the MCP server for automatic restart:

### Using Docker
If the server is using docker compose and you wish to have it automatically start on system reboot, add the following entry to the docker-compose.yaml file to either or both service entries (```teradata-mcp-server:```, ```teradata-rest-server:```)
```sh
services:
  teradata-mcp-server:
    build: .
    image: teradata-mcp-server:latest
    restart: always
```

### Using UV in the user environment
If the server is set up to run locally using ```uv run...```, it can be configured to run as a systemd service.
1. Create a file in /etc/systemd/service named ```<your service name>.service```, e.g. ```teradata_mcp.service```
2. Copy the following entries - modify for your environment:
```sh
[Unit]
Description=Teradata MCP  demo service
After=network.target
StartLimitIntervalSec=0
[Service]
Type=simple
Restart=always
RestartSec=1
WorkingDirectory=/home/ec2-user/teradata-mcp-server
User=ec2-user
ExecStart=/home/ec2-user/.local/bin/uv run /home/ec2-user/teradata-mcp-server/src/teradata_mcp_server/server.py > /dev/null

[Install]
WantedBy=multi-user.target
```
3. Run ```sudo systemctl start <your service name>.service``` to start the service
4. Run ```sudo systemctl status <your service name>.service``` to check status
5. Run ```sudo systemctl enable <your service name>.service``` to enable start on system boot
6. To be safe, test increasing restart intervals for stability.  Create a crontab for the service:
7. ```sudo crontab -e```
8. ```0 * * * * /bin/systemctl restart <your service name>.service```

You are now ready to connect your client, For details on how to set up client tools, refer to [Working with Clients](./client_guide/CLIENT_GUIDE.md)



## Testing your server

Connect your preferred client, and validate that you see the server tools, prompts and resources.

If you want to rapidly check what's available, and does work or not, we provide an interactive testing method via the prompt `_testMyServer`. Simply load the prompt, specify a functional domain that you wish to test (or "all") and run.

This is a good way to validate and explore your setup, but not sufficent to carry actual unit or system testing.
