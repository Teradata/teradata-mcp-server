# Configuration Examples

This directory contains example configuration files for the Teradata MCP Server.

## Files

- `example_profiles.yml` - Example custom profiles
- `example_custom_objects.yml` - Example custom tools, prompts, cubes, and glossary entries
- `sales_domain_example.yml` - Complete sales domain configuration example
- `dba_tools_example.yml` - DBA-focused tools and prompts example

## Usage

1. Copy any of these files to your working directory
2. Rename them so it's meaningful.
3. Customize the content for your needs
4. Run the server from that directory

Example:
```bash
mkdir my-tdmcp-config
cd my-tdmcp-config
cp ../examples/Configuration_Examples/profiles.yml ./
cp ../examples/Configuration_Examples/custom_objects.yml mydomain_objects.yml

# Edit the files as needed
```sh
TD_USER=demo_user TD_PASSWORD=demo_password teradata-mcp-server --profile my_custom_profile
```

Claude Desktop server configuration snippet:
```json
    "sales_ux": {
      "command": "uvx",
      "args": [
        "--directory",
        "/absolute-path-to/my-tdmcp-config/examples/server-customisation",
        "teradata-mcp-server",
        "--profile", "sales",
        "--database_uri", "teradata://db_user:db_password@systemname.env.clearscape.teradata.com:1025"
      ]
    } 
```