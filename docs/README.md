# Teradata MCP Server Documentation

> **📍 Navigation:** [Documentation Home](../README.md) | **Server Guide** 

This guide will help you get started, configure, and customize your Teradata MCP Server setup.

## 🚀 Quick Start

New to Teradata MCP Server? Choose your 5-minute quickstart to rapidly evaluate the server with your favorite tool:

| **Client** | **Deployment** | **Communication** | **Best For** |
|------------|----------------|------------------|--------------|
| [Claude Desktop](server_guide/QUICK_START.md) | CLI (uv/pipx) | stdio | Exploratory Data Analytics, Platform Administration, general evaluation |
| [VS Code + Copilot](server_guide/QUICK_START_VSCODE.md) | CLI (uv/pipx) | HTTP | Data Engineering, Agentic app development |
| [Open WebUI](server_guide/QUICK_START_OPEN_WEBUI.md) | Docker | REST | Local AI, evaluate new LLMs |
| [Code examples](../examples/README.md) | Python | HTTP | Build your own client. Example library using ADK, Bedrock, Langchain... |

**Other Options:**
- **[Getting Started Guide](server_guide/GETTING_STARTED.md)** - Detailed path selection and role-based recommendations
- **[Video Library](server_guide/VIDEO_LIBRARY.md)** - Watch step-by-step tutorials

## 📖 Documentation Sections

### 🛠 Server Guide
Everything you need to know about running and configuring the MCP server:

- **[Getting Started](server_guide/GETTING_STARTED.md)** - Choose your path (routing guide)
- **[Installation](server_guide/INSTALLATION.md)** - Deployment methods and options
- **[Configuration](server_guide/CONFIGURATION.md)** - Server settings and tuning
- **[Architecture](server_guide/ARCHITECTURE.md)** - How components work together
- **[Customizing](server_guide/CUSTOMIZING.md)** - Add your own tools and business logic
- **[Security](server_guide/SECURITY.md)** - Authentication and access control


### 👥 Client Guide
Connect different AI clients to your Teradata MCP Server:

- **[Client Overview](client_guide/CLIENT_GUIDE.md)** - Supported clients and general setup
- **[Claude Desktop](client_guide/Claude_desktop.md)** - Desktop AI assistant
- **[Visual Studio Code](client_guide/Visual_Studio_Code.md)** - IDE integration
- **[Google Gemini CLI](client_guide/Google_Gemini_CLI.md)** - Command-line interface
- **[Microsoft Copilot](client_guide/Microsoft_copilot.md)** - Enterprise integration
- **[Open WebUI](client_guide/Open_WebUI.md)** - Web-based interface
- **[REST API](client_guide/Rest_API.md)** - HTTP/API integration
- **[MCP Inspector](client_guide/MCP_Inspector.md)** - Debugging and testing tool

### 🔧 Developer Guide
Extend and contribute to the Teradata MCP Server:

- **[Developer Guide](developer_guide/DEVELOPER_GUIDE.md)** - Architecture and development setup
- **[Contributing](developer_guide/CONTRIBUTING.md)** - How to contribute code
- **[Adding Functions](developer_guide/HOW_TO_ADD_YOUR_FUNCTION.md)** - Create custom tools
- **[Prompt Guidelines](developer_guide/PROMPT_DEFINITION_GUIDELINES.md)** - Best practices for prompts

## 🎯 Common Use Cases

### For Data Engineers & Analysts
- **Quick Setup**: [5-Minute Quick Start](server_guide/QUICK_START.md) → [Claude Desktop](client_guide/Claude_desktop.md)
- **Custom Business Logic**: [Customizing Guide](server_guide/CUSTOMIZING.md)
- **Security Setup**: [Security Configuration](server_guide/SECURITY.md)

### For Developers & DevOps
- **API Integration**: [REST API Guide](client_guide/Rest_API.md)
- **Custom Tools**: [Adding Functions](developer_guide/HOW_TO_ADD_YOUR_FUNCTION.md)
- **Contributing**: [Developer Guide](developer_guide/DEVELOPER_GUIDE.md)

### for IT Administrators
- **Enterprise Deployment**: [Security Guide](server_guide/SECURITY.md)
- **Client Management**: [Client Guide](client_guide/CLIENT_GUIDE.md)

## 🆘 Need Help?

- 📹 **Visual Learner?** Check our [Video Library](server_guide/VIDEO_LIBRARY.md)
- 🤝 **Want to contribute?** See our [Contributing Guide](developer_guide/CONTRIBUTING.md)
- 💡 **Have Ideas or identified a bug?** Open an issue on GitHub