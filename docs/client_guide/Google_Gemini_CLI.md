# Using with gemini-cli

> **📍 Navigation:** [Documentation Home](../README.md) | [Server Guide](../README.md#-server-guide) | [Getting started](../server_guide/GETTING_STARTED.md) | [Architecture](../server_guide/ARCHITECTURE.md) | [Installation](../server_guide/INSTALLATION.md) | [Configuration](../server_guide/CONFIGURATION.md) | [Security](../server_guide/SECURITY.md) | [Customization](../server_guide/CUSTOMIZING.md) | [Client Guide](CLIENT_GUIDE.md)

1.	Make sure you have Teradata database access. (the most convenient way: Go to https://clearscape.teradata.com create account and login, start the environment and click on Run Demo)
2.	Go to https://github.com/Teradata/teradata-mcp-server run below lines in cmd terminal. (once build finished, you should see Teradata-mcp-server image in your docker desktop)
    * ```export DATABASE_URI=teradata://username:password@host:1025``` (use the username, password, host from above clearscape step)
    * ```git clone https://github.com/Teradata/teradata-mcp-server.git```
    * ```cd teradata-mcp-server```
    * ```docker compose up```
3.	Go to https://github.com/google-gemini/gemini-cli follow instruction to install
    * For authenticate, please use personal google email.
4.	Go to your project folder, create ```.gemini/settings.json``` accordingly
```
{
    "theme": "Default",
    "selectedAuthType" : "oauth-personal",

    "mcpServers": {
        "teradata-http": {
            "httpUrl" : "http://127.0.0.1:8001/mcp/",
            "timeout" : 5000
        }
    }
}
```
5. Open a cmd terminal, type ```gemini``` and hit enter, now you should see gemini-cli interface.
