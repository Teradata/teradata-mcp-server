# 5-Minute Quick Start (Visual Studio Code with GitHub Copilot)

> **📍 Navigation:** [Documentation Home](../README.md) | [Server Guide](../README.md#-server-guide) | **Quick Start VS Code** | [Quick Start Claude](QUICK_START.md) | [Installation](INSTALLATION.md)

> **🎯 Goal:** Get a working MCP server connected to VS Code and GitHub Copilot in 5 minutes

![](../media/client-server-platform.png)

## ✅ Prerequisites (2 minutes)

Before starting, ensure you have:

1. **Teradata Database Access**
   - Host URL, username, password
   - [Get a free sandbox](https://www.teradata.com/getting-started/demos/clearscape-analytics) if needed

2. **Required Software**
   - [VS Code](https://code.visualstudio.com/) installed
   - [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
     - macOS: `brew install uv`
     - Windows: `winget install astral-sh.uv`

## 🚀 Step 1: Install and Test (1 minute)

Install the MCP server as a CLI tool:

```bash
# Install the server
uv tool install "teradata-mcp-server"

# Test installation
teradata-mcp-server --help
```

## 🔧 Step 2: Start HTTP Server (1 minute)

Start the server in HTTP mode for VS Code:

```bash
# Set your database connection
export DATABASE_URI="teradata://username:password@host:1025/database"

# Start HTTP server
teradata-mcp-server --mcp_transport streamable-http --mcp_port 8001 --profile all
```

You should see:
```
INFO: Started server process
INFO: Uvicorn running on http://127.0.0.1:8001
```

**Keep this terminal open** - the server is now running!

## 🔧 Step 3: Configure VS Code (1 minute)

Add MCP Server via Command Palette:
   - Open Command Palette (Ctrl+Shift+P)
   - Type "MCP: Add Server..." and select it
   - Choose server type: Select **"HTTP (HTTP or Server-Sent Events)"**
   - Enter the server URL: `http://127.0.0.1:8001/mcp/`
   - Press Enter to confirm, give your server a name and start it

You should see a configuration as follows in your mcp.json file:

![alt text](media/vscode-mcp-json.png)

## ✨ Step 4: Test It (30 seconds)

Test your Teradata MCP connection in VS Code:

1. Open the Copilot "Chat" pane
2. At the bottom of the chat window, select "Agent" mode, click "Tools"
3. Make sure the Teradata MCP server and tools you have just added is selected 

Invoke a tool in the chat window:

```
/dba_databaseVersion
```

Or direct a question to the server:
```
@teradata-mcp-server What's in my database?
```

You should see Copilot use your Teradata MCP server tools.!

## 🎉 What's Next?

**You now have Teradata MCP Server connected to VS Code and GitHub Copilot!**

### For Quick Exploration
- **Try different prompts**: Ask Copilot about your data schema, run SQL queries
- **Explore and customize profiles**: Change `"all"` to `"dataScientist"` or `"dba"` in your server startup
- **Connect other tools**: [Other client options](../client_guide/CLIENT_GUIDE.md)

### For Production Setup  

Use the following resources to deploy the server to a production environment and rollout it to your teams:

- **Installation**: [Available installation methods](INSTALLATION.md) for remote deployment options.
- **Security**: [Configure authentication](SECURITY.md) for team deployments
- **Custom Tools and profiles**: [Add business-specific tools](CUSTOMIZING.md) for your domain
- **Detailed VSCode Setup**: [Full VS Code guide](../client_guide/Visual_Studio_Code.md)

---
*This quick start gets you running with VS Code and GitHub Copilot. For Claude Desktop, see the [Claude Quick Start](QUICK_START.md).*