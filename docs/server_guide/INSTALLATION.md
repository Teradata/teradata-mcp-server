# Installation Guide

> **📍 Navigation:** [Documentation Home](../README.md) | [Server Guide](../README.md#-server-guide) | [Quick Start](QUICK_START.md) | **Installation** | [Configuration](CONFIGURATION.md)

> **🎯 Goal:** Choose and implement the best deployment method for your needs

## 🤔 Which Installation Method?

| Method | Best For | Pros | Cons | Setup Time |
|--------|----------|------|------|------------|
| **uv tool** | Development, Desktop use | Fast, isolated, easy updates | Requires uv | 2 min |
| **Docker** | Production, REST API | Containerized, scalable | Requires Docker knowledge | 5 min |  
| **pip + venv** | Traditional Python shops | Familiar workflow | Manual env management | 3 min |
| **Source** | Contributors, Custom builds | Latest features | Requires dev setup | 10 min |

## 🚀 Method 1: uv Tool (Recommended)

**Best for:** Most users, development, desktop integration

### Why uv?
- Installs into isolated environment (no system pollution)
- Extremely fast downloads and installs
- Easy upgrades: `uv tool upgrade teradata-mcp-server`

### Install uv
```bash
# macOS
brew install uv

# Windows  
winget install astral-sh.uv

# Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install MCP Server
```bash
# Basic installation
uv tool install teradata-mcp-server

# With enterprise features (Feature Store, Vector Store)
uv tool install "teradata-mcp-server[fs,evs]"
```

### Usage
```bash
# Run directly
teradata-mcp-server --help

# Or via uvx (no install needed)
uvx teradata-mcp-server --help
```

### Updates
```bash
uv tool upgrade teradata-mcp-server
```

## 🐳 Method 2: Docker (Production)

**Best for:** Production deployments, REST API usage, team deployments

### Quick Start
```bash
docker run -d \\
  --name teradata-mcp \\
  -p 8001:8001 \\
  -e DATABASE_URI="teradata://user:pass@host:1025/db" \\
  -e MCP_TRANSPORT="streamable-http" \\
  ghcr.io/teradata/teradata-mcp-server:latest
```

### With Docker Compose
```yaml
# docker-compose.yml
services:
  teradata-mcp:
    image: ghcr.io/teradata/teradata-mcp-server:latest
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URI=teradata://user:pass@host:1025/db
      - MCP_TRANSPORT=streamable-http
      - PROFILE=dataScientist
    restart: unless-stopped
```

Run with: `docker-compose up -d`

### Custom Configuration
```bash
# Mount custom config
docker run -d \\
  -p 8001:8001 \\
  -v ./custom_objects.yml:/app/custom_objects.yml \\
  -e DATABASE_URI="teradata://user:pass@host:1025/db" \\
  ghcr.io/teradata/teradata-mcp-server:latest
```

## 🐍 Method 3: pip + venv (Traditional)

**Best for:** Python developers, existing Python workflows

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
- Python 3.9+
- uv (recommended) or pip
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

### Development Mode
```bash
# Run tests
uv run pytest

# Format code
uv run ruff format

# Type checking
uv run mypy src/
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
- Verify DATABASE_URI format: `teradata://user:pass@host:1025/database`
- Test network connectivity: `ping your-host`
- Check firewall settings (port 1025)

## ✨ What's Next?

**Installation complete!** Choose your next step:

- **🚀 Quick Test**: [5-Minute Quick Start](QUICK_START.md)
- **⚙️ Configuration**: [Server Configuration](CONFIGURATION.md)  
- **🔒 Security**: [Authentication Setup](SECURITY.md)
- **👥 Client Setup**: [Connect AI Clients](../client_guide/CLIENT_GUIDE.md)
- **🛠 Custom Tools**: [Add Business Logic](CUSTOMIZING.md)

---
*Need help? Check our [troubleshooting guide](CONFIGURATION.md#troubleshooting) or [video tutorials](../VIDEO_LIBRARY.md).*