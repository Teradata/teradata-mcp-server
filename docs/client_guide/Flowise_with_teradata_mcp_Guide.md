# Teradata MCP server in Flowise

> **📍 Navigation:** [Documentation Home](../README.md) | [Server Guide](../README.md#-server-guide) | [Getting started](../server_guide/GETTING_STARTED.md) | [Architecture](../server_guide/ARCHITECTURE.md) | [Installation](../server_guide/INSTALLATION.md) | [Configuration](../server_guide/CONFIGURATION.md) | [Security](../server_guide/SECURITY.md) | [Customization](../server_guide/CUSTOMIZING.md) | [Client Guide](CLIENT_GUIDE.md)

1.	**Make sure you have Teradata database access.** (the most convenient way: Go to https://clearscape.teradata.com create account and login, start the environment and click on Run Demo)
2.	**Build Teradata mcp server container image** from https://github.com/Teradata/teradata-mcp-server,  run below lines in cmd terminal.
```
git clone https://github.com/Teradata/teradata-mcp-server.git
cd teradata-mcp-server
# build container from Source code
docker build --build-arg ENABLE_FS_MODULE=true \
   --build-arg ENABLE_TDML_MODULE=true \
   --build-arg ENABLE_TDVS_MODULE=true \
   -t teradata-mcp-server:latest .

```
3. **Build Flowise Container Image** from https://github.com/FlowiseAI/Flowise,  run below lines in cmd terminal.

```
git clone https://github.com/FlowiseAI/Flowise.git
cd Flowise
docker build --no-cache -t flowise:latest .
```

4.	**Create Common .env file** for teradata-mcp-server and flowise container, 
```
mkdir ~/td_ai_stack
cd ~/td_ai_stack
vi .env
```
```
# ----------- MCP server and Database Env variables ------------#
DATABASE_URI=teradata://username:password@host:1025/databasename
LOGMECH=TD2  #TD2 or LDAP
TD_POOL_SIZE=5
TD_MAX_OVERFLOW=10
TDPOOL_TIMEOUT=30
PROFILE=dataScientist
DATABASE_HOST=IP_OF_DB_NODE

MCP_TRANSPORT=streamable-http  #stdio, sse, streamable-http
MCP_HOST=0.0.0.0
MCP_PORT=8001
MCP_PATH=/mcp/

# ----- Enterprise Vector Store ----------
TD_BASE_URL=https://host/api/accounts/40c83ff23b2e    #Your UES_URI, strip off the trailing /open-analytics
#TD_PAT=gwxhQG2UZcDqQlp9LKWjEBfXB7                     #Your PAT if you have Teradata Lake system.
TD_PEM=/root/td_ai_stack/demo_key.pem                 #Your PEM with full path where you kept on host                            
VS_NAME=vs_example                                    #Your target Vector Store Name

# ------------ Flowise env varieable -------------------#
PORT=3000
CORS_ORIGINS=*
IFRAME_ORIGINS=*
DATA_DIR=~/td_ai_stack/.flowise               # host dir to persist data of flowise
```
5. **Create docker-compose.yaml file** to up teradata-mcp-server and flowise containers
```
cd ~/td_ai_stack
vi  docker-compose.yaml

```
```
services:
    flowise:
        image: flowise:latest
        restart: always
        environment:
            - PORT=${PORT}
            # LOGGING
            - DEBUG=${DEBUG}
            # SETTINGS
            - CORS_ORIGINS=${CORS_ORIGINS}
            - IFRAME_ORIGINS=${IFRAME_ORIGINS}
           # Default Teradata Configuration env to refer into flowise
            - TD_MCP_SERVER=http://teradata-mcp-server:8001/mcp
        ports:
            - "${PORT}:${PORT}"
        extra_hosts:
            - "dbccop1:${DATABASE_HOST}"
        container_name: flowise
        healthcheck:
            test: ['CMD', 'curl', '-f', 'http://localhost:${PORT}/api/v1/ping']
            interval: 10s
            timeout: 5s
            retries: 5
            start_period: 30s
        volumes:
            - ${DATA_DIR}/.flowise:/root/.flowise
    teradata-mcp-server:
        image: teradata-mcp-server:latest
        restart: always
        environment:
            - DATABASE_URI=${DATABASE_URI}
            - LOGMECH=${LOGMECH}
            - MCP_TRANSPORT=${MCP_TRANSPORT}
            - MCP_PATH=${MCP_PATH}
            - MCP_HOST=${MCP_HOST}
            - MCP_PORT=${MCP_PORT}
            - PROFILE=${PROFILE}
            - TD_BASE_URL=${TD_BASE_URL}
            - TD_PAT=${TD_PAT}
            - TD_PEM=${TD_PEM}
            - VS_NAME=${VS_NAME}
        container_name: teradata-mcp-server
        extra_hosts:
            - "dbccop1:${DATABASE_HOST}"
        ports:
            - "${MCP_PORT}:${MCP_PORT}"
        volumes:
            - ${TD_PEM}:${TD_PEM}
        tty: true
networks:
  default:
    name: td-ai-stack
    external: false
```

6.  **Up teradata MCP server and flowise container**
```
cd ~/td_ai_stack
mkdir ~/td_ai_stack/.flowise
docker image ls   # make sure teradata-mcp-server and flowise container images are available
docker compose up -d --remove-orphans
```

7. **Validate docker container status**
```
docker ps
# teradata-mcp-server container logs
docker logs teradata-mcp-server -f
# Flowise Container logs
docker logs flowise -f
```

8. **Login to flowise**
http://IP:3000 or http://127.0.0.1:3000

first time login - Complete organization setup (set any username and password)

![alt text](../media/flowise/flowise-org-setup.png)

9. **How to configure Teradata MCP server into Flowise Agentflow**

   - 9.1. Go Into Agentflows menu and Add new
   ![alt text](../media/flowise/Agentflow-add.png)
   - 9.2. Drag and Drop Agent and connect it with Start Node
   ![alt text](../media/flowise/Drag-Agent.png)
   ![alt text](../media/flowise/conntect-Agent-with-StartNode.png)
   - 9.3. Set up LLM credentials and LLM for Agent

        - Double click on Agent-0 , it will show Model to select model from various provider
        - select provider like Azure ChatOpenAI and set Azure ChatOpenAI Parameters, 
        - for connect Credentails select -Create New-, fill details and Add
        ![alt text](../media/flowise/Select-LLM-Provider.png)
        ![alt text](../media/flowise/Configure-LLM-Model.png)
        ![alt text](../media/flowise/configure-LLM-creds.png)
   - 9.4. Add Teradata MCP server as custom MCP server for Tools
       - Click on Add Tools
       - Select Custom MCP server
       - Setup - Custom MCP Server Parameters

        ```
        {
            "url": "http://teradata-mcp-server:8001/mcp",
            
        }
        ```

       - Refresh Button of Available Actions
       - Click on Drop down to select tools for Agent
       ![alt text](../media/flowise/Select-custom-mcp.png)![alt text](../media/flowise/Configure-custom-mcp.png)
       ![alt text](../media/flowise/MCP-tools-Drop-down.png)![alt text](../media/flowise/Select-tools-from-mcp.png)

10.  **Save Agentflow with anyName**
![alt text](../media/flowise/Save-AgentFlow.png)

11. **Execute AgentFlow**
![alt text](../media/flowise/Execute-Agent-Flow.png)

![alt text](../media/flowise/tool-execution.png)