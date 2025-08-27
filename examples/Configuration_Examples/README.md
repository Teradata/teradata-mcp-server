# Configuration Examples

This directory contains example configuration files for the Teradata MCP Server.

## Files

- `example_profiles.yml` - Example custom profiles
- `example_custom_objects.yml` - Example custom tools, prompts, cubes, and glossary entries
- `sales_domain_example.yml` - Complete sales domain configuration example
- `dba_tools_example.yml` - DBA-focused tools and prompts example

## Usage

1. Copy any of these files to your working directory
2. Rename them (remove the `example_` prefix)
3. Customize the content for your needs
4. Run the server from that directory

Example:
```bash
mkdir my-config
cd my-config
cp ../examples/Configuration_Examples/example_profiles.yml profiles.yml
cp ../examples/Configuration_Examples/sales_domain_example.yml my_sales_tools.yml

# Edit the files as needed
teradata-mcp-server --profile sales
```