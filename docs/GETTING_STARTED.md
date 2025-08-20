# MCP Server - Getting Started

![Getting Started](media/MCP-quickstart.png)

This document will cover the process and options for getting the teradata-mcp-server up and running

Assumes that you have a running Teradata environment, you should have the following information for your Teradata system:
1. host address - IP address or DNS address for the location of the server
2. user name - name you log into the teradata system with
3. user password - password for the corresponding user name
4. database - On Teradata systems this is typically the same as you user name

## Step 0 - Installing environment
- Refer to the [git](https://git-scm.com/) website for download and installation instructions, git will be used to pull code from the github repository.
- Refer to the [Installing uv](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer) guide to assist with installing uv, uv is used to manage packages that are used.
- Refer to the [Python.org](https://www.python.org/downloads/) for downloading and installing python 3.11 or greater.

## Step 1 - Download the Software
Clone the mcp-server repository with: 

On Windows
```
git clone https://github.com/Teradata/teradata-mcp-server.git
cd teradata-mcp-server
```

On Mac/Linux
```
git clone https://github.com/Teradata/teradata-mcp-server.git
cd teradata-mcp-server
```

Changes are constantly happening to the server, we recommend that you come back occasionally to update the code.
```
cd teradata-mcp-server
git pull origin main
```

## Step 2 - You have a choice

![Choice](media/transport.png) 

Transport Modes (in order of preference)
1. Streamable-Http (http) - this transport mode uses the http protocol for communication, this is the recomended mode to use.
2. Standard IO (stdio) - all communications are published to standard input and output, this is suitable for a standalone server running on your laptop.
3. Server Side Events (SSE) - this transport mode is going to be decomissioned by the mcp standard hence we do not recommend using this.


Deployment Choice
1. Docker Container - the container will manage the libraries and starting the service.
2. UV - UV will manage the libraries (this approach is more suitable for development)
3. REST - The rest approach takes the docker container and wraps it in a Restful API

The recommended choice will be to deploy Streamable-http in a docker container. [Jump to next section](#step-5---using-docker) for the docker option.

<br>

## Step 3 - Customizing the server (optional)

The server supports optional modules for additional functionality:
- **`fs`** - Teradata Enterprise Feature Store integration
- **`evs`** - Teradata Enterprise Vector Store integration

Install with uv (recommended): `uv sync --extra fs --extra evs`
Or with pip: `pip install -e .[fs,evs]`

Refer to the [Customizing](CUSTOMIZING.md) instuctions 

<br>

## Step 4 - Starting your Server

You should pick one of the approaches below:
1. [Using Docker](#step-5a---using-docker) - Recommended.
2. [Using uv](#step-5b---uv-environment-set-up) - Good for developers
3. [Using rest](#step-5c---run-the-mcp-server-with-rest) - Good for operationalizing 
4. [Running as a Service](#step-5d---run-the-mcp-server-as-a-service) - Good for operationalizing 


--------------------------------------------------------------------------------------

### Step 4a - Using Docker

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
### Step 4b - UV Environment Set Up 

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
### Step 4c - Run the MCP server with REST

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
### Step 4d - Run the MCP Server as a service
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



