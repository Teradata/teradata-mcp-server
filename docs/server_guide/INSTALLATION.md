# Installation & Deployment Guide

> **📍 Navigation:** [Documentation Home](../README.md) | [Server Guide](../README.md#-server-guide) | [Getting started](GETTING_STARTED.md) | [Architecture](ARCHITECTURE.md) | [<u>**Installation**</u>](INSTALLATION.md) | [Configuration](CONFIGURATION.md) | [Security](SECURITY.md) | [Customization](CUSTOMIZING.md) | [Client Guide](../client_guide/CLIENT_GUIDE.md)

> **🎯 Goal:** Choose and implement the best deployment method for your needs

This guide covers everything you need to deploy the Teradata MCP Server, from local development to production environments:

- **Installation Methods** - Different ways to install the server (CLI, Docker, pip, source)
- **Production Deployment** - Remote deployment strategies for serving multiple clients
- **Service Management** - Running as system services with automatic restart and monitoring

## 🤔 Which Installation Method?

| Method | Best For | Pros | Cons | Setup Time |
|--------|----------|------|------|------------|
| **CLI Install** | System-wide command | Available everywhere, isolated | Requires uv/pipx | 2 min |
| **Docker** | Production, REST API | Containerized, scalable | Requires Docker knowledge | 5 min |  
| **pip + venv** | Traditional Python shops | Familiar workflow | Manual env management | 3 min |
| **Source** | Contributors, Custom builds | Latest features | Requires dev setup | 10 min |

## 🚀 Method 1: CLI Installation (Recommended)

**Best for:** System-wide command-line tool, available from anywhere

We recommend `uv` or `pipx` to install teradata-mcp-server as a CLI tool. They provide isolated environments and ensure the `teradata-mcp-server` command is available system-wide without interfering with system Python.

### Option A: Using uv
```bash
# Install uv first
# macOS: brew install uv
# Windows: winget install astral-sh.uv  
# Linux: curl -LsSf https://astral.sh/uv/install.sh | sh

# Install teradata-mcp-server
uv tool install "teradata-mcp-server"

# With optional Enterprise Feature Store and Vector Store
uv tool install "teradata-mcp-server[fs,evs]"
```

If the tool's path isn't resolved add it to your shell using `uv tool update-shell` and restart the terminal.

### Option B: Using pipx 
```bash
# Install pipx first (if not available)
python -m pip install --user pipx
python -m pipx ensurepath

# Install teradata-mcp-server
pipx install "teradata-mcp-server"

# With optional Enterprise Feature Store and Vector Store
pipx install "teradata-mcp-server[fs,evs]"
```

### Usage
```bash
# Available system-wide
teradata-mcp-server --help
teradata-mcp-server --version
```

### Updates
```bash
# With uv
uv tool upgrade teradata-mcp-server

# With pipx  
pipx upgrade teradata-mcp-server
```

## 🐳 Method 2: Docker (Build from Source)

**Best for:** Production deployments, scale out, IaC

You can use Docker to run the MCP server in streamable-http mode.

Docker requires building from the source repository since we currently don't publish pre-built images.

### Prerequisites
- Docker and Docker Compose installed
- Git

### Clone and configure
```bash
# Clone the repository
git clone https://github.com/Teradata/teradata-mcp-server.git
cd teradata-mcp-server
```

**Optional configurations:**
- Place `custom_objects.yml` in the project root to add custom tools
- Modify `docker-compose.yml` for permanent environment changes (you can use environment variables at runtime)

### Run
The server expects at least the Teradata URI string via the `DATABASE_URI` environment variable. You may:
- update the `docker-compose.yaml` file or 
- setup the environment variable with your system's connection details:

```sh
export DATABASE_URI=teradata://username:password@host:1025/databaseschema
docker compose up
```

### Examples

```bash
# Set your database connection
export DATABASE_URI="teradata://username:password@host:1025/database"

# Build with optional modules (Feature Store, Vector Store)
ENABLE_FS_MODULE=true ENABLE_TDVS_MODULE=true docker compose build
docker compose up

# Run with specific profile
PROFILE=dba docker compose up

# Combine options
ENABLE_FS_MODULE=true ENABLE_TDVS_MODULE=true PROFILE=dataScientist docker compose build
PROFILE=dataScientist docker compose up

# Run in background (production)
docker compose up -d
```

The server will be available on port 8001 (or the value of the `PORT` environment variable).

### REST Interface Option

For integration with any tool that supports REST APIs, you can run the server with a REST interface using the "rest" profile:

```sh
# Set your API key for authentication
export MCPO_API_KEY=top-secret
export DATABASE_URI="teradata://username:password@host:1025/database"

# Run with REST interface
docker compose --profile rest up
```

This exposes your Teradata tools as OpenAPI-compatible REST endpoints at http://localhost:8002. View the documentation and test endpoints at http://localhost:8002/docs.

You are now ready to connect your client. For details on how to set up client tools, refer to [Working with Clients](../client_guide/CLIENT_GUIDE.md)

## 🐍 Method 3: pip + venv (Traditional)

**Best for:** Existing Python projects

### Prerequisites
- Python 3.12+

### Create Virtual Environment
```bash
python -m venv .venv

# Activate (Linux/macOS)
source .venv/bin/activate

# Activate (Windows)
.venv\\Scripts\\activate
```

### Install
```bash
pip install --upgrade pip
pip install teradata-mcp-server

# With enterprise features
pip install "teradata-mcp-server[fs,evs]"
```

### Usage
```bash
# Make sure venv is activated
source .venv/bin/activate
teradata-mcp-server --help
```

## 🔨 Method 4: Build from Source (Contributors)

**Best for:** Contributors, custom modifications, latest features

### Prerequisites
- Python 3.12+
- uv (recommended)
- Git

### Clone and Install
```bash
git clone https://github.com/Teradata/teradata-mcp-server.git
cd teradata-mcp-server

# With uv (recommended)
uv sync
uv run teradata-mcp-server --help

# Or with pip
pip install -e ".[dev]"
teradata-mcp-server --help
```

## ✅ Verify Installation

Test your installation:

```bash
# Check version
teradata-mcp-server --version

# Test database connection (set DATABASE_URI first)
export DATABASE_URI="teradata://user:pass@host:1025/db"
teradata-mcp-server --profile all
```

You should see output like:
```
Created tool: base_listTables
Created tool: base_readQuery
...
```

## 🔄 Updates & Maintenance

### uv tool
```bash
uv tool upgrade teradata-mcp-server
```

### Docker
```bash
docker pull ghcr.io/teradata/teradata-mcp-server:latest
docker-compose down && docker-compose up -d
```

### pip
```bash
pip install --upgrade teradata-mcp-server
```

## 🆘 Troubleshooting

### Common Issues

**"Command not found" after uv install**
```bash
# Add uv tools to PATH (usually automatic)
export PATH="$HOME/.local/bin:$PATH"
```

**Docker permission denied**
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
# Then log out/in
```

**Import errors with pip**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate
which python  # Should show .venv path
```

**Database connection fails**
- Verify DATABASE_URI environment variable is available, or use `--database_uri` argument, and URI well formatted: `teradata://user:pass@host:1025/database` 
- Check firewall settings (port 1025)

---

## 🚀 Production Deployment

For production deployments that serve multiple clients, you have two main options:

1. **Docker deployment** - Containerized setup with automatic restarts (includes REST option)
2. **System service** - Background service using either:
   - **Direct execution** - `teradata-mcp-server` (after pip/uv install, recommended)
   - **uv-managed execution** - `uv run teradata-mcp-server` (with dependency management)

For remote access, use the `streamable-http` transport protocol which communicates over HTTP.

**Before you deploy**, define your security strategy and review the [security patterns we provide](SECURITY.md).

### 🐳 Docker Production Setup

If the server is using docker compose and you wish to have it automatically start on system reboot, add the following entry to the docker-compose.yaml file to either or both service entries (`teradata-mcp-server:`, `teradata-rest-server:`):

```yaml
services:
  teradata-mcp-server:
    build: .
    image: teradata-mcp-server:latest
    restart: always
```

### ⚙️ System Service Setup

Configure the MCP server to run as a systemd service for automatic startup and management:

1. **Create a service file** in `/etc/systemd/system/` named `<your service name>.service`, e.g. `teradata_mcp.service`

2. **Copy the following configuration** - modify for your environment:
```ini
[Unit]
Description=Teradata MCP Server
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=1
User=your-username
Environment=DATABASE_URI=teradata://username:password@host:1025/database
Environment=MCP_TRANSPORT=streamable-http
Environment=MCP_HOST=127.0.0.1
Environment=MCP_PORT=8001
ExecStart=/usr/local/bin/teradata-mcp-server --profile all

[Install]
WantedBy=multi-user.target
```

3. **Start and enable the service**:
```bash
# Start the service
sudo systemctl start <your service name>.service

# Check status
sudo systemctl status <your service name>.service

# Enable start on system boot
sudo systemctl enable <your service name>.service
```

4. **Optional: Add cron restart** for additional stability:
```bash
# Edit crontab
sudo crontab -e

# Add hourly restart (adjust as needed)
0 * * * * /bin/systemctl restart <your service name>.service
```

## ✨ What's Next?

**Installation complete!** Choose your next step:

- **🚀 Quick Test**: [5-Minute Quick Start](QUICK_START.md)
- **⚙️ Configuration**: [Server Configuration](CONFIGURATION.md)  
- **🔒 Security**: [Authentication Setup](SECURITY.md)
- **👥 Client Setup**: [Connect AI Clients](../client_guide/CLIENT_GUIDE.md)
- **🛠 Custom Tools**: [Add Business Logic](CUSTOMIZING.md)

---
*Need help? Check our [troubleshooting guide](CONFIGURATION.md#troubleshooting) or [video tutorials](VIDEO_LIBRARY.md).*