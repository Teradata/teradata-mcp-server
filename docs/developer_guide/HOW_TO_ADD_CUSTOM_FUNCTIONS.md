## 📚 How to add custom Functions into the MPC Server

### Custom tools and prompts file

1. Custom tools and prompts will reside in a file that ends in _tools.yaml
2. Files will be loaced in the base directory of the MCP server [teradata-mcp-server](../)

### File structure for tools

1. Each yaml snippet will define a single tool
2. Each yaml snippet will include:
    - type: tool
    - name: cust_nameOfTool
    - description: description of the tool, this is used by the llm to select the tool
    - sql: | SQL
3. Currently custom tools do not allow parameters

### File structure for prompts

1. Each yaml snippet will define a single prompt
2. Each yaml snippet will include:
    - type: prompt
    - name: cust_nameOfPrompt
    - description: description of the prompt
    - prompt: | prompt text
3. Currently custom prompts do not allow parameters


### Adding custom functions

The server will read the yaml files and create the custom tools and prompts.

### Testing custom functions

The mcp_chatbot.py client is capable of making all prompts available and callable for testing.

