# Examples

This directory contains application examples and configurations for the Teradata MCP Server. These examples demonstrate different ways to customize, configure, and build upon the server.

## Server Customization

### [`server-customisation/`](./server-customisation/)
**Configuration examples for customizing the Teradata MCP Server**

Customizing the Teradata MCP server is easy and doesn't require you to write a single line of code!

You will fine example configuration files that show how to:

- Create custom profiles with specific toolsets, database connections and communication settings
- Define custom tools, prompts, cubes, and glossary entries
- Set up domain-specific configurations (e.g., sales, DBA tools)
- Organize configurations for different use cases

Key files:
- `example_profiles.yml` - Custom profile configurations
- `example_custom_objects.yml` - Custom tools, prompts, and resources
- `sales_domain_example.yml` - Complete sales domain setup
- `dba_tools_example.yml` - Database administrator focused tools

Simply copy these files to your working directory, customize the content, and run the server from that directory.

### [`app-testing-agent/`](./app-testing-agent/)
**Testing prompts and configurations for MCP Server validation**

Contains specialized prompts and configurations designed build agents that can test the functionality of the MCP server. Useful for:
- Validating server setup and configuration
- Testing custom tools and prompts
- Quality assurance workflows

Run the server with: `teradata-mcp-server --profile tester`

## Client Applications

### [`app-voice-agent/`](./app-voice-agent/)
**Voice assistant using Amazon Nova Sonic with Teradata integration**

A simple voice-enabled assistant that provides:
- Real-time bidirectional audio communication to Nova Sonic models on AWS Bedrock
- Profile-based configuration system, including language and voice options
- Access to Teradata via the MCP server tools and prompts

Useful for rapid prototyping of voice assistants leveraging your lakehouse data and compute minimal effort.

### [`app-adk-agent/`](./app-adk-agent/)
**Web-based agent using Google ADK framework**

A web interface agent built with Google's ADK framework featuring:
- Modern chat interface accessible via web browser
- Visual component execution timing
- Support for multiple LLM providers (AWS, Google, Azure, Ollama)
- Full access to MCP tools and resources

Use for rapid prototyping of interactive web-based data agents.

### [`app-bedrock-client/`](./app-bedrock-client/)
**Command-line agent using MCP client framework**

A simple command-line interface that provides:
- Terminal-based chat experience
- Direct access to all MCP tools, prompts, and resources
- AWS Bedrock integration
- Streamlined setup for quick interactions

Simple example to get started.

## Client Configuration

### [`client-claude-desktop/`](./client-claude-desktop/)
**Configuration for Claude Desktop integration**

Contains configuration files and setup instructions for integrating the Teradata MCP Server with Claude Desktop application.

## API Documentation

### [`server-api-spec/`](./server-api-spec/)
**API specification and documentation**

Contains OpenAPI/Swagger specifications for the server's HTTP endpoints.