## Using with Claude Desktop

[Claude Desktop Instructions](https://modelcontextprotocol.io/quickstart/user)

Step1 - Modify your claude desktop configuration file -  `claude_desktop_config.json` config file:

**Streamable-http**

Example can be found in [claude_desktop_http_config](../../test/Claude_Desktop_Config_Files/claude_desktop_http_config)

Note: you may need to modify the host in the args.


**Stdio**

Example can be found in [claude_desktop_stdio_config](../../test/Claude_Desktop_Config_Files/claude_desktop_stdio_config)

Note: you will need to modify the directory path in the args for your system, this needs to be a complete path.  You may also need to have a complete path to uv in the command as well.

Note: this requires that `uv` is available to Claude in your system path or installed globally on your system (eg. uv installed with `brew` for Mac OS users).

**SSE**

Example can be found in [claude_desktop_SSE_config](../../test/Claude_Desktop_Config_Files/claude_desktop_SSE_config)

Note: you may need to modify the host in the args.