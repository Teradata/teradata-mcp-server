# 5-Minute Quick Start with Claude

> **📍 Navigation:** [Documentation Home](../README.md) | [Server Guide](../README.md#-server-guide) | **Quick Start** | [Installation](INSTALLATION.md) | [Configuration](CONFIGURATION.md)

> **🎯 Goal:** Get a working MCP server connected to Claude Desktop in 5 minutes

![](../media/client-server-platform.png)

## ✅ Prerequisites (2 minutes)

Before starting, ensure you have:

1. **Teradata Database Access**
   - Host URL, username, password
   - [Get a free sandbox](https://www.teradata.com/getting-started/demos/clearscape-analytics) if needed

2. **Required Software**
   - [Claude Desktop](https://claude.ai/download) installed
   - [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
     - macOS: `brew install uv`
     - Windows: `winget install astral-sh.uv`

## 🚀 Step 1: Test the Server (1 minute)

Run this command to test your database connection:

```bash
uvx teradata-mcp-server --help
```

If that works, test with your database:

```bash
uvx teradata-mcp-server --database_uri "teradata://username:password@host:1025/database"
```

You should see "Created tool: [tool_name]" messages. Press `Ctrl+C` to stop.

## 🔧 Step 2: Configure Claude Desktop (2 minutes)

1. Open Claude Desktop
2. Go to **Settings** → **Developer** → **Edit Config**
3. Add this configuration (update with your database details):

```json
{
  "mcpServers": {
    "teradata": {
      "command": "uvx",
      "args": ["teradata-mcp-server", "--profile", "all"],
      "env": {
        "DATABASE_URI": "teradata://USERNAME:PASSWORD@HOST:1025/DATABASE"
      }
    }
  }
}
```

4. **Save** and **restart Claude Desktop**

## ✨ Step 3: Test It Works (30 seconds)

In Claude Desktop, try this prompt:

```
List the first 5 tables in my database
```

You should see Claude connect to your Teradata database and return results!

## 🎉 Success! What's Next?

**You now have a working Teradata MCP Server!** Here are your next options:

### For Quick Exploration
- **Try different profiles**: Change `"all"` to `"dataScientist"` or `"dba"` in your config
- **Connect other clients**: [Visual Studio Code](../client_guide/Visual_Studio_Code.md), [Google Gemini](../client_guide/Google_Gemini_CLI.md)

### For Production Setup  
- **Security**: [Configure authentication](SECURITY.md) for team deployments
- **Custom Tools**: [Add business-specific tools](CUSTOMIZING.md) for your domain
- **Advanced Install**: [Docker deployment](INSTALLATION.md#using-docker) for production

### For Development
- **Custom Functions**: [Add your own tools](../developer_guide/HOW_TO_ADD_YOUR_FUNCTION.md)
- **Contributing**: [Developer Guide](../developer_guide/DEVELOPER_GUIDE.md)

## 🆘 Troubleshooting

**Server won't start?**
- Check your `DATABASE_URI` format
- Verify database connectivity: `ping your-host`
- Rollback to a prior version changing your config file: `"args": ["teradata-mcp-server==0.1.3", "--profile", "all"],`
- See [Installation Guide](INSTALLATION.md) for alternative methods

**Claude can't see tools?**
- Restart Claude Desktop after config changes
- Check Claude's system messages for connection errors
- Try the test command from Step 1 first

**Want more help?**
- 📹 [Video tutorials](VIDEO_LIBRARY.md)
- 📖 [Detailed installation guide](INSTALLATION.md)
- 🔧 [Configuration options](CONFIGURATION.md)

---
*This quick start gets you running fast. For production deployments or team setups, see the [Installation Guide](INSTALLATION.md).*