# Quickstart — Docker Compose (MCP + Caddy HTTPS)
 
This guide shows how to run the **Teradata MCP server** behind **Caddy** with automatic **HTTPS (Let’s Encrypt)** using **Docker Compose**. It keeps port **8001** private and exposes only **80/443**.
 
---
 
## 0) Prerequisites
 
- Docker + Docker Compose plugin installed.
- An EC2 instance or host with public IPv4.
- A DNS record pointing to your host (e.g. `teradata-mcp.duckdns.org → <public IP>`).  
  *(you can use a free dynamic DNS service such as DuckDNS for testing...)*
- Security Group / firewall allows inbound **TCP 80** and **TCP 443** (keep **22** for SSH).
 
---
 
## 1) Folder layout
 
Copy the [docker](examples/server-deployment/docker) directory outside this code directory and move into it this is the structure:

```
examples/server-deployment/docker/
├─ docker-compose.yml
├─ .env
├─ Dockerfile
├─ deploy/
│  └─ caddy/
│     └─ Caddyfile
└─ site/
   ├─ favicon.ico        # optional
   ├─ favicon.png        # optional
   └─ index.html         # optional landing page
```

Eg. 
```bash
#If you haven't, clone this repo
git clone https://github.com/<your-org>/teradata-mcp-server.git

cp -R teradata-mcp-server/examples/server-deployment/docker teradata-mcp-service
cp teradata-mcp-server/Dockerfile teradata-mcp-service
cd teradata-mcp-service
```


---
 
## 2) `.env` — runtime configuration
 
Copy the `env` file to `.env` and edit it to update your database connection string for `DATABASE_URI` and domain name for `DOMAIN`:

```bash
cp env .env
```

```dotenv
# --- MCP server (FastMCP) ---
DATABASE_URI=teradata://USER:PASS@HOST:1025/DEFAULT_DB_SCHEMA   # <-- Update here 
MCP_TRANSPORT=streamable-http
MCP_HOST=0.0.0.0
MCP_PORT=8001
 
# --- Caddy / HTTPS ---
# Set this to the DNS name that points at your server
DOMAIN=teradata-mcp.duckdns.org                                 # <-- Update here 
```
 
> Keep secrets out of command history by using `.env`. For all supported vars, see **docs/server_guide/CONFIGURATION.md**.
 
---
 
## 3) (Optional) landing page
 
You can update or add files under `examples/server-deployment/docker/site/` to customize the landing page. 
The current setup indicates that the server is running and points the viewer to the client tool setup documentation.

---
 
## 4) Start the stack
 
From your directory:
 
```bash
docker compose up -d --remove-orphans
docker compose ps
```
 
First-time HTTPS may take ~30–90 seconds. Watch Caddy:
 
```bash
docker compose logs -f caddy
```
 
---
 
## 5) Verify
 
```bash
# Expect 200/401/405 from the app (not HTML)
curl -i https://${DOMAIN}/mcp/
 
# Inside the network (debug): curl from caddy to mcp
docker compose exec caddy sh -lc 'wget -qO- http://mcp:8001/mcp/ | head'
```
 
If you added a landing page: visit `https://${DOMAIN}/`.
 
---
 
## 6) Use with Claude Desktop
 
With HTTPS you **do not** need `--allow-http`:
 
```json
{
  "mcpServers": {
    "teradata_mcp_remote_https": {
      "command": "npx",
      "args": ["mcp-remote", "https://YOUR_DOMAIN/mcp/"]
    }
  }
}
```
 
Add headers if you enforce auth at the app or proxy (e.g., `--header "Authorization: Basic ${AUTH_TOKEN}"`).
 
---
 
## 7) Operations
 
```bash
# Update/recreate
docker compose pull && docker compose up -d --remove-orphans --build
 
# Logs
docker compose logs -f mcp
docker compose logs -f caddy
 
# Stop
docker compose down
```
 
---
 
## 10) Troubleshooting
 
- **TLS errors right after deploy** → DNS propagation or first ACME run; retry in a minute and check `docker compose logs -f caddy`.
- **80/443 blocked** → open in Security Group / firewall; confirm public IPv4 resolves for `${DOMAIN}`.
 
---
 
**That’s it.** You now have a HTTPS-protected MCP server via Docker Compose with Caddy.

-----
