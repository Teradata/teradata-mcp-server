# Server Configuration

> **📍 Navigation:** [Documentation Home](../README.md) | [Server Guide](../README.md#-server-guide) | [Getting started](GETTING_STARTED.md) | [Architecture](ARCHITECTURE.md) | [Installation](INSTALLATION.md) | [<u>**Configuration**</u>](CONFIGURATION.md) | [Security](SECURITY.md) | [Customization](CUSTOMIZING.md) | [Client Guide](../client_guide/CLIENT_GUIDE.md)

> **🎯 Goal:** Configure your MCP server for optimal performance and security

## 🔧 Basic Configuration

### Configuration Priority

The MCP server uses the following configuration sources in priority order (highest to lowest):

1. **Command line arguments** (e.g., `--profile dataScientist`, `--config_dir /path/to/config`)
2. **Environment variables** (e.g., `export PROFILE=dataScientist`, `export CONFIG_DIR=/path/to/config`)
3. **Environment file** (i.e., `.env` file)
4. **Default values**


### Environment Variables

Configure the server using environment variables:

```bash
# Required: Database connection
export DATABASE_URI="teradata://username:password@host:1025/database"

# Optional: Server behavior  
export MCP_TRANSPORT="stdio"           # or "streamable-http"
export MCP_HOST="localhost"            # for HTTP transport
export MCP_PORT="8001"                 # for HTTP transport
export MCP_PING_INTERVAL="30"         # keep-alive ping interval (seconds) for streamable-http and sse transports
export PROFILE="all"                   # tool profile to load
export LOGGING_LEVEL="WARNING"         # DEBUG, INFO, WARNING, ERROR

# Optional: Database connection tuning
export LOGMECH="TD2"                   # TD2, LDAP, KRB5, JWT
export TD_POOL_SIZE="5"                # connection pool size
export TD_MAX_OVERFLOW="10"            # max overflow connections
export TD_POOL_TIMEOUT="30"            # connection timeout seconds

# Optional: Query result limits
export DEFAULT_ROW_LIMIT="1000"        # default max rows returned by base_readQuery
export MAX_ROW_LIMIT="50000"           # hard ceiling; callers cannot exceed this

# Optional: Authentication (see Security guide)
export AUTH_MODE="none"                # or "basic"  
export AUTH_CACHE_TTL="300"            # seconds
export AUTH_RATE_LIMIT_ATTEMPTS="5"
export AUTH_RATE_LIMIT_WINDOW="60"
```

### Configuration File (.env) - Optional

For convenience, you can create a `.env` file for persistent configuration:

```bash
# .env file (optional convenience)
DATABASE_URI=teradata://username:password@host:1025/database
PROFILE=dataScientist
LOGGING_LEVEL=INFO
MCP_TRANSPORT=streamable-http
MCP_PORT=8001
```

The server automatically loads `.env` files from the current directory. Command line arguments will override these values.

## Configuration files for customization and advanced tools

You can specify a custom directory for user configuration files using the `--config_dir` parameter or `CONFIG_DIR` environment variable:

```bash
# Using command line argument
teradata-mcp-server --config_dir /path/to/my/config-files
```

**Default:** If not specified, the current working directory is used, if no relevant config files are found the package defaults are applied.

The configuration directory can contain:
- Custom tool/prompt YAML definitions (any file with a `.yml` extension that is not in the list below - e.g., `my_tools.yml`)
- `profiles.yml` - Custom profiles
- `chat_config.yml` - Chat completion configuration overrides
- `rag_config.yml` - RAG configuration overrides
- `sql_opt_config.yml` - SQL optimizer configuration overrides

### Configuration Strategy

The server uses a **layered configuration approach** where configuration files are loaded in the following order:

1. **Built-in Defaults** - Hardcoded default values in the application code
2. **Packaged Config** - Configuration files in `src/teradata_mcp_server/config/` (developer mode, read-only)
3. **User Config** - Configuration files in your config directory (runtime overrides)

Later layers override earlier layers, and top-level keys are replaced entirely (no merge)


## Teradata Vector Store tools (`tdvs`)

The `tdvs` module provides tools to manage and use Teradata Vector Stores. It requires **Teradata Vantage 20.0+** and the `teradatagenai` Python library.

### Install the optional dependency

The `teradatagenai` library is not installed by default. Add it with the `[tdvs]` extra:

```bash
# With uv
uv tool install "teradata-mcp-server[tdvs]"

# With pip
pip install "teradata-mcp-server[tdvs]"
```

### Environment variables

In addition to `DATABASE_URI`, the `tdvs` module requires the following variables:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URI` | Yes | Standard Teradata connection string |
| `TD_BASE_URL` | Yes | Base URL of the Teradata Vector Store service |
| `TD_PAT` | No | Personal Access Token for authentication. Falls back to `DATABASE_URI` credentials if not set. |
| `TD_PEM` | No | Path to PEM certificate file. Used together with `TD_PAT`. |

Add them to your `.env` file:

```dotenv
DATABASE_URI=teradata://myuser:mypassword@my-host:1025/mydb
TD_BASE_URL=https://my-tdvs-host/api
TD_PAT=my-personal-access-token
TD_PEM=/path/to/my/cert.pem
```

### Claude Desktop configuration

Use `uvx` with the `--from` flag to pull the `[tdvs]` extra, and pass the variables in the `env` block.

> **Shell quoting note:** If running `uvx` manually in a terminal (zsh/bash), quote the package spec to prevent glob expansion: `uvx --from "teradata-mcp-server[tdvs]" teradata-mcp-server`. In the Claude Desktop JSON config below this is not needed — args are passed directly to the process without shell interpretation.

```json
{
  "mcpServers": {
    "teradata-mcp-server": {
      "command": "uvx",
      "args": [
        "--from", "teradata-mcp-server[tdvs]",
        "teradata-mcp-server"
      ],
      "env": {
        "DATABASE_URI": "teradata://myuser:mypassword@my-host:1025/mydb",
        "PROFILE": "all",
        "MCP_TRANSPORT": "stdio",
        "TD_BASE_URL": "https://my-tdvs-host/api",
        "TD_PAT": "my-personal-access-token",
        "TD_PEM": "/path/to/my/cert.pem"
      }
    }
  }
}
```

> **Note:** `TD_PAT` and `TD_PEM` are optional. If omitted, the server authenticates to the Vector Store using the username and password from `DATABASE_URI`.

---

## 🎯 Profiles

Profiles control which tools and resources are available:

### Built-in Profiles

| Profile | Description | Tools Included |
|---------|-------------|----------------|
| `all` | Everything (production ready) | All tools except test prompts |
| `tester` | Everything including tests | All tools + test prompts |
| `dba` | Database administration | dba_*, base_*, sec_* tools |
| `dataScientist` | Data science focus | base, rag, fs, qlty, sql_opt tools |
| `eda` | Exploratory data analysis | Read-only base tools, quality tools |
| `custom` | Custom tools only | Your custom YAML-defined tools |
| `sales` | Sales domain example | Custom sales tools and cubes |

### Using Profiles

```bash
# Command line
teradata-mcp-server --profile dataScientist

# Environment variable
export PROFILE="dataScientist"
teradata-mcp-server

# Multiple profiles (comma-separated)
export PROFILE="base,qlty,custom"
```

### Custom Profiles

Create custom profiles in `profiles.yml` in your config directory (see Configuration Directory section above):

```yaml
# profiles.yml (in your config directory)
myProfile:
  tool:
    - "base_*"           # All base tools
    - "custom_sales_*"   # Custom sales tools
    - "qlty_dataProfile" # Specific quality tool
  prompt:
    - "sales_*"          # All sales prompts
  resource:
    - "glossary"         # Include glossary
```

**Example usage with custom config directory:**
```bash
# Create your config directory
mkdir -p ~/my-teradata-config

# Create custom profiles
cat > ~/my-teradata-config/profiles.yml << 'EOF'
myProfile:
  tool:
    - "base_*"
    - "qlty_*"
  prompt:
    - "sql_*"
EOF

# Start server with custom config
teradata-mcp-server --config_dir ~/my-teradata-config --profile myProfile
```

Your custom `profiles.yml` will be merged with the built-in profiles, allowing you to:
- Override existing profiles
- Add new profiles
- Extend built-in profiles with additional tools

## 🔍 Progressive Disclosure

By default, all tools in the active profile are registered individually and listed by the client at startup. With many tools loaded this can consume a significant portion of the LLM context window.

**Progressive disclosure** reduces this by exposing only three proxy tools to the client — `search_tool`, and `execute_tool`— while keeping the full tool catalog available on demand. The LLM searches for tools by keyword, retrieves full documentation on the ones it needs, then executes them.

```bash
# Enable via flag
teradata-mcp-server --progressive_disclosure

# Or via environment variable
export PROGRESSIVE_DISCLOSURE=true
teradata-mcp-server
```

| Mode | Client sees | Context window |
|------|-------------|----------------|
| Static (default) | All tools listed at startup | Higher usage |
| Progressive disclosure | 3 proxy tools | ~99% reduction |

See the [developer guide](../developer_guide/PROGRESSIVE_DISCLOSURE.md) for details on the search algorithm and two-tier discovery workflow.

## 🚄 Transport Modes

### stdio (Default)

Best for: Desktop AI clients (Claude, VS Code)

```bash
teradata-mcp-server
# or
teradata-mcp-server --mcp_transport stdio
```

**Characteristics:**
- Uses stdin/stdout for communication
- Started and managed by AI client
- Most efficient for desktop use
- Default mode

### streamable-http

Best for: Multiple clients, multiple end-users with individual database access control, centralized deployment, container deployment.

```bash
teradata-mcp-server --mcp_transport streamable-http --mcp_port 8001
```

**Characteristics:**
- HTTP server on specified port
- Supports multiple concurrent clients with individual sessions
- Can be combined with user authentication to enforce individual data access policies
- Can be containerized

### Server-Sent Events (sse)

For specialized streaming applications:

```bash
teradata-mcp-server --mcp_transport sse --mcp_port 8001
```

### Keep-Alive (HTTP/SSE transports)

Load balancers and reverse proxies (nginx, AWS ALB) close idle connections after a fixed timeout. For long-running Teradata queries over `streamable-http` or `sse`, the server sends periodic ping messages to keep the connection alive.

```bash
export MCP_PING_INTERVAL="30"   # seconds between keep-alive pings (default: 30)
```

This has no effect on `stdio` transport.

## 🔒 Authentication Configuration

### No Authentication (Default)

```bash
export AUTH_MODE="none"
```

All requests use the server's database credentials.

### Basic Authentication

```bash
export AUTH_MODE="basic"
export AUTH_CACHE_TTL="300"                # Cache valid tokens for 5 minutes
export AUTH_RATE_LIMIT_ATTEMPTS="5"       # Max attempts per window
export AUTH_RATE_LIMIT_WINDOW="60"        # Rate limit window in seconds
```

Users must provide valid database credentials with each request.

See [Security Guide](SECURITY.md) for detailed authentication setup.

## 🏗 Database Connection Tuning

### Connection Pool Settings

```bash
export TD_POOL_SIZE="5"        # Base connections
export TD_MAX_OVERFLOW="10"    # Additional connections under load  
export TD_POOL_TIMEOUT="30"    # Seconds to wait for connection
```

### Query Result Limits

`base_readQuery` caps results to prevent LLM token overflow. Results beyond the limit are silently dropped and the response metadata includes `"truncated": true`.

```bash
export DEFAULT_ROW_LIMIT="1000"   # Default max rows per base_readQuery call
export MAX_ROW_LIMIT="50000"      # Hard ceiling; the row_limit parameter cannot exceed this
```

When a query is truncated, the LLM can:
- Pass a higher `row_limit` (up to `MAX_ROW_LIMIT`) to retrieve more rows in a single response.
- Pass `persist=true` to write the full result set to a volatile table and query it directly — this bypasses the row cap entirely and is recommended for large result sets.

### Authentication Methods

```bash
export LOGMECH="TD2"    # Teradata 2 (default)
export LOGMECH="LDAP"   # LDAP authentication  
export LOGMECH="KRB5"   # Kerberos
export LOGMECH="JWT"    # JSON Web Token
```

### Connection String Format

```bash
# Basic format
teradata://username:password@host:port/database

# With parameters
teradata://user:pass@host:1025/db?LOGMECH=TD2&charset=UTF8

# URL encoding for special characters
teradata://user:p%40ssw0rd@host:1025/database
```

## 🐳 Docker Configuration

### Environment Variables

```dockerfile
# Dockerfile or docker-compose.yml
environment:
  - DATABASE_URI=teradata://user:pass@host:1025/db
  - PROFILE=dataScientist
  - MCP_TRANSPORT=streamable-http
  - MCP_PORT=8001
  - LOGGING_LEVEL=INFO
```

### Volume Mounts

```yaml
# docker-compose.yml
services:
  teradata-mcp:
    build: .  # Build from source (no pre-built images available)
    volumes:
      - ./custom_objects.yml:/app/custom_objects.yml
      - ./profiles.yml:/app/profiles.yml
      - ./.env:/app/.env
```

## 🔍 Logging & Debugging

### Log Levels

```bash
export LOGGING_LEVEL="DEBUG"    # Verbose output
export LOGGING_LEVEL="INFO"     # General information
export LOGGING_LEVEL="WARNING"  # Warnings only (default)
export LOGGING_LEVEL="ERROR"    # Errors only
```

### Debug Mode

```bash
# Verbose logging
teradata-mcp-server --logging_level DEBUG

# Test specific profile
teradata-mcp-server --profile base --logging_level INFO
```

### Useful Debug Commands

```bash
# Test database connection
teradata-mcp-server --profile base --logging_level DEBUG

# List available tools
curl http://localhost:8001/mcp/list_tools

# Check server health
curl http://localhost:8001/mcp/ping
```

## 🆘 Troubleshooting

### Common Issues

**Server won't start**
```bash
# Check environment variables
env | grep -E "(DATABASE_URI|PROFILE|MCP_)"

# Test database connection
ping your-teradata-host
telnet your-teradata-host 1025
```

**Tools not loading**
```bash
# Check profile configuration
teradata-mcp-server --profile all --logging_level DEBUG

# Verify custom YAML files
cat custom_objects.yml
```

**Connection pool exhausted**
```bash
# Increase pool size
export TD_POOL_SIZE="10"
export TD_MAX_OVERFLOW="20"
```

**Performance issues**
```bash
# Monitor connections
export LOGGING_LEVEL="DEBUG"
# Check for connection leaks in logs
```

**Installing behind a proxy**

For UV installations
```bash
export INTERNAL_PROXY=
export UV_INDEX_INTERNAL_PROXY_USERNAME=
export UV_INDEX_INTERNAL_PROXY_PASSWORD=
export UV_INDEX=
```

for pip installations
```bash
pip install <package_name> --proxy ://[user:password@]proxy.server:port
```


### Testing Your Configuration

```bash
# Basic connectivity
teradata-mcp-server --help

# Database connection
export DATABASE_URI="your-connection-string"
teradata-mcp-server --profile base --logging_level INFO

# HTTP mode
teradata-mcp-server --mcp_transport streamable-http --mcp_port 8001 &
curl http://localhost:8001/mcp/ping
```

## ✨ What's Next?

**Configuration complete!** Your next steps:

- **🔒 Security**: [Set up authentication](SECURITY.md) for team use
- **🛠 Customize**: [Add custom tools](CUSTOMIZING.md) for your business
- **👥 Connect**: [Set up AI clients](../client_guide/CLIENT_GUIDE.md)
- **📊 Monitor**: [Production deployment tips](SECURITY.md#production-considerations)

---
*For advanced configuration options and enterprise features, see the [Security Guide](SECURITY.md) and [Customization Guide](CUSTOMIZING.md).*