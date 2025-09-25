# Using with Perplexity Desktop

Perplexity Desktop Instructions (https://www.perplexity.ai/help-center/en/articles/11502712-local-and-remote-mcps-for-perplexity)

Step 1 - Open your account settings and click on Connectors

Note: Before you can add MCP Connectors, you have to install the helper application PerplexityXPC so that Perplexity can securely connect to your local MCP servers.

Step 2 - Add connector -> Advanced Tab. Copy the below JSON and use your actual credentials - $TD_USER , $TD_PASSWORD, $TD_HOSTNAME, $TD_DEFAULT_DB 

```json
{
  "args" : [
    "--directory",
    "/path/of/your/teradata-mcp-server",
    "run",
    "teradata-mcp-server"
  ],
  "command" : "uv",
  "env" : {
    "DATABASE_URI" : "teradata://$TD_USER:$TD_PASSWORD@$TD_HOSTNAME:1025/$TD_DEFAULT_DB"
  }
}
```

Note: you will need to modify the directory path in the args for your system, this needs to be a complete path. You may also need to have a complete path to uv in the command as well.
