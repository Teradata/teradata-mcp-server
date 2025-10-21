# 5-Minute Quick Start (Open WebUI)

> **📍 Navigation:** [Documentation Home](../README.md) | [Server Guide](../README.md#-server-guide) | [Getting started](GETTING_STARTED.md) | [Architecture](ARCHITECTURE.md) | [Installation](INSTALLATION.md) | [Configuration](CONFIGURATION.md) | [Security](SECURITY.md) | [Customization](CUSTOMIZING.md) | [Client Guide](../client_guide/CLIENT_GUIDE.md)

> **🎯 Goal:** Get a working MCP server connected to Open WebUI in 5 minutes

![](../media/client-server-platform.png)

## ✅ Prerequisites (2 minutes)

Before starting, ensure you have:

1. **Teradata Database Access**
   - Host URL, username, password
   - [Get a free sandbox](https://www.teradata.com/getting-started/demos/clearscape-analytics) if needed

2. **Required Software**
   - [Docker and Docker Compose](https://docs.docker.com/get-docker/) installed
   - [Git](https://git-scm.com/downloads) for cloning the repository
   - [Python 3.11+](https://www.python.org/downloads/)

## 🚀 Step 1: Get the Server (1 minute)

Clone and prepare the MCP server:

```bash
# Clone the repository
git clone https://github.com/Teradata/teradata-mcp-server.git
cd teradata-mcp-server
```

## 🔧 Step 2: Start REST Server (1 minute)

You can use [mcpo](https://github.com/open-webui/mcpo) to expose the MCP server as a RESTful OpenAPI:

Start the server and expose as OpenAPI REST server for Open WebUI:

```bash
# Set your database connection
export DATABASE_URI="teradata://username:password@host:1025/database"
export MCPO_API_KEY=top-secret

# Start the REST interface
uvx mcpo --port 8002 --api-key "top-secret" -- uvx teradata-mcp-server
```

Alternatively, you can use Docker instead of uv:

```bash
# Start the REST interface
docker compose --profile rest up
```

You should see:
```
INFO: Started server process
Server running at http://localhost:8002
OpenAPI docs available at http://localhost:8002/docs#
```

**Keep this terminal open** - the server is now running!

## 🌐 Step 3: Install Open WebUI (1 minute)

In a new terminal, install and start Open WebUI:

```bash
# Create virtual environment
python -m venv ./env
source ./env/bin/activate  # On Windows: .\env\Scripts\activate

# Install Open WebUI
pip install open-webui   

# Start Open WebUI
open-webui serve
```

Open WebUI will start at http://localhost:8080

## ✨ Step 4: Connect to MCP Server (30 seconds)

Configure Open WebUI to use your Teradata MCP server:

1. **Access Open WebUI**: Navigate to http://localhost:8080
2. **Go to Settings**: Click on Settings in the interface
3. **Add Tools Connection**:
   - Navigate to **Settings > Tools > Add Connection**
   - Enter connection details:
     - **Host**: `localhost:8002`
     - **API Key**: `top-secret`
4. **Verify Connection**: You should see the Teradata tools appear in the Tools section

## 🧪 Step 5: Test It Works (30 seconds)

Test your Teradata MCP connection in Open WebUI:

1. **Start a New Chat**: Create a new conversation
2. **Enable Tools**: In the Chat Control Valves section (right panel), ensure Teradata tools are enabled
3. **Test with a Query**: Try asking:

```
What tables are available in my database?
```

## 🎉 Success! What's Next?

**You now have Teradata MCP Server connected to Open WebUI!**

### For Quick Exploration
- **Try different models**: Open WebUI supports various LLM runners so you can integrate your local model deployments or use cloud-based services.
- **Explore tools**: Check the Chat Control Valves to see all available Teradata tools
- **Custom queries**: Ask complex questions about your data schema and content

### For Production Setup  
- **Security**: Configure proper authentication for team deployments
- **Custom Tools**: [Add business-specific tools](CUSTOMIZING.md) for your domain
- **Model Configuration**: Set up your preferred LLM models in Open WebUI

### For Development
- **API Explorer**: Use http://localhost:8002/docs to explore and test REST endpoints
- **Custom Integration**: [REST API guide](../client_guide/Rest_API.md) for building custom applications

## 🆘 Troubleshooting

**Cannot use the MCP tools**
Not all models work well with MCP tools and resources, start with state-of-the art models such as OpenAI's or Anthropic's to validate that your setup is working and explore different models.

**REST server not starting?**
- Check your `DATABASE_URI` format: `teradata://user:pass@host:1025/database`
- Verify port 8002 isn't in use: `lsof -i :8002`
- Ensure Docker is running and you're in the correct directory

**Open WebUI can't connect to tools?**
- Verify the REST server is running at http://localhost:8002/docs
- Check the API key matches: `MCPO_API_KEY=top-secret`
- Restart both services if needed

**Tools not appearing in Open WebUI?**
- Check the connection settings in Settings > Tools
- Verify the host and API key are correct
- Look for connection errors in the Open WebUI logs

**Database connection fails?**
- Verify `DATABASE_URI` environment variable: `echo $DATABASE_URI`
- Ensure credentials are correct

**Want more help?**
- 📹 [Video tutorials](VIDEO_LIBRARY.md)
- 📖 [Detailed installation guide](INSTALLATION.md)
- 🔧 [Configuration options](CONFIGURATION.md)
- 🌐 [Open WebUI Documentation](https://docs.openwebui.com/)

---
*This quick start gets you running with Open WebUI. For other clients, see [Claude Quick Start](QUICK_START.md) or [VS Code Quick Start](QUICK_START_VSCODE.md).*