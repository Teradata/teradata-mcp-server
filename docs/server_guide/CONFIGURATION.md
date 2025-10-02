# Server Configuration

> **📍 Navigation:** [Documentation Home](../README.md) | [Server Guide](../README.md#-server-guide) | [Getting started](GETTING_STARTED.md) | [Architecture](ARCHITECTURE.md) | [Installation](INSTALLATION.md) | [<u>**Configuration**</u>](CONFIGURATION.md) | [Security](SECURITY.md) | [Customization](CUSTOMIZING.md) | [Client Guide](../client_guide/CLIENT_GUIDE.md)

> **🎯 Goal:** Configure your MCP server for optimal performance and security

## 🔧 Basic Configuration

### Configuration Priority

The MCP server uses the following configuration sources in priority order (highest to lowest):

1. **Command line arguments** (e.g., `--profile dataScientist`)
2. **Environment variables** (e.g., `export PROFILE=dataScientist`)
3. **Configuration files** (e.g., `.env` file)
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
export PROFILE="all"                   # tool profile to load
export LOGGING_LEVEL="WARNING"         # DEBUG, INFO, WARNING, ERROR

# Optional: Database connection tuning
export LOGMECH="TD2"                   # TD2, LDAP, KRB5, JWT
export TD_POOL_SIZE="5"                # connection pool size
export TD_MAX_OVERFLOW="10"            # max overflow connections
export TD_POOL_TIMEOUT="30"            # connection timeout seconds

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

Create custom profiles in `profiles.yml` (must be in the current directory where the application is started):

```yaml
# profiles.yml
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