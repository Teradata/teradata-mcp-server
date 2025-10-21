# Teradata MCP Server on AWS EC2 — **Basic Deployment** 

> Goal: spin up the **Teradata MCP Server** on a small EC2 instance so you can connect it using **Claude Desktop** or your prefered desktop application over HTTP.  
> DO NOT USE AS IS FOR PRODUCTION DEPLOYMENT

---

## 1) EC2 sizing & OS

You can run the Teradata MCP server on a relatively small instance using a Linux OS.

| Size | vCPU | RAM | Why |
|---|---:|---:|---|
| **t3a.medium** *(recommended)* | 2 | 4 GiB | Great cost/perf for small teams (≈5–15 users). |
| t3a.large | 2 | 8 GiB | If you want to co-locate heavier front-end applications (eg. Flowwise, n8n, your chat bots...). |
| t4g.medium *(ARM)* | 2 | 4 GiB | Cheaper/faster if all deps are arm64; otherwise stick to x86 if unsure / planning to experiment. |

- **AMI**: Amazon Linux 2023 (or Ubuntu 22.04).  
- **Storage**: 30 GiB gp3 EBS.  (default)
- **Network**: (default)

---

## 2) Open the port & bind correctly

You will need to allow inbound traffic using ssh to configure your system and TCP for the end-users

- In the AWS Console, select your instance > Security > **Security Group > Edit inbound rules**:  
  - Inbound: TCP, type SSH, port **22** (default), 
  - Inbound: TCP, type Custom TCP, port **8001** (source = your end user IP list/range).  

---

## 3) Software Install

Install `uv` to install the MCP server

```bash
# On Amazon Linux
sudo dnf update -y
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Install the MCP server

```bash
uv tool install teradata-mcp-server
```

## 4) Configure the server

You can create a configuration file to store your server settings:

```bash
cat > .env <<'EOF'
# --- Required: DB connection ---
DATABASE_URI=teradata://<USER>:<PASS>@<HOST>:1025/<DB_OR_USER>

# --- Server (Streamable HTTP) ---
MCP_TRANSPORT=streamable-http
MCP_HOST=0.0.0.0
MCP_PORT=8001

EOF
```

Edit the database connection string as with the Teradata system and user credentials for the MCP server. 

## 5) Run the server

You may now run the server as a background process:

```bash
nohup teradata-mcp-server > mcp.log &
```
After a few seconds, validate that the server is started: `tail -50 mcp.log`


## 6) Test the server connectivity

You can test the connectivity to the server from your clients servers/workstations with curl: `curl -I http://<EC2_PUBLIC_IP>:8001/mcp`.

If your MCP service is reachable, you should see this type of output:

```
HTTP/1.1 307 Temporary Redirect
date: Tue, 14 Oct 2025 15:39:58 GMT
server: uvicorn
...
```

 If this returns a `Failed to connect to ...: Connection refused`, it is likely an issue in your network configuration.

## 7) Configure the clients

For Visual Studio Code, follow the usual [http setup instructions](../../docs/client_guide/Visual_Studio_Code.md#Add-the-http-server-in-VS-Code).

For Claude desktop, you can use mcp-remote connect to your server.

```json
{
  "mcpServers": {
    "teradata_mcp_remote_aws": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://<EC2_PUBLIC_IP>:8001/mcp/",
        "--allow-http"
      ]
    }
  }
}
```


## 8) Configure HTTPS with Caddy

If you are planning to expose the service over the public internet, you need to secure your MCP server communication with HTTPS.

In this example, we will use [Caddy](https://caddyserver.com/docs/automatic-https?utm_source=chatgpt.com) as a reverse proxy, alternatively, you may use [ngix](https://nginx.org/en/docs/http/configuring_https_servers.html).

 like and a free domain from **DuckDNS**. This guide reflects a working setup.

### Prerequisites: Domain ownership and DNS

When you enable HTTPS using Let’s Encrypt (which Caddy does automatically), the certificate authority needs to verify that you control the domain name in the URL.

You also need to setup your DNS to resolve to the IP of the instance deployed above. 


If you just want to want to quickly test the process, you may use a free dns service such as [https://www.duckDNS.org/](https://www.duckdns.org/). So you can create a new subdomain (e.g., `my-mcp-server.duckdns.org`) and point to your cloud instance's public IP address.

### 1. Allow HTTPS inbound traffic

Add a security rule to your EC2 security group to allow inbound traffic on port 443 (HTTPS).

In the AWS Console, select your instance > **Security>Security Group > Edit inbound rules > Add rule**:  
> Type=**HTTPS**; port **443** (default); source = **Anywhere-IPv4** (0.0.0.0/0).  


### 2. Install Caddy

The process below downloads and installs the static Caddy binary. You can also check on [the instal page](https://caddyserver.com/docs/install#install) if Caddy is distributed with your distribution's package manager.

```bash
curl -fsSL "https://github.com/caddyserver/caddy/releases/download/v2.6.4/caddy_2.6.4_linux_amd64_static" -o caddy
sudo mv caddy /usr/local/bin/caddy
sudo chmod +x /usr/local/bin/caddy
```

### 3. Setup Caddy user, directories, and configuration

Create a dedicated user and directories for Caddy:

```bash
sudo useradd --system --home /var/lib/caddy --shell /usr/sbin/nologin caddy
sudo mkdir -p /etc/caddy /var/lib/caddy /var/log/caddy
sudo chown -R caddy:caddy /etc/caddy /var/lib/caddy /var/log/caddy
```

Create the Caddyfile configuration file at `/etc/caddy/Caddyfile` with the following content:

```text
mcp.your-domain.org {
    encode gzip
    reverse_proxy 127.0.0.1:8001
}
```

Replace `mcp.your-domain.org` with your actual DNS domain (eg. `my-mcp-server.duckdns.org`).

### 4. Create and enable the Caddy systemd service

Create `/etc/systemd/system/caddy.service` with the following content:

```ini
[Unit]
Description=Caddy web server
After=network.target

[Service]
User=caddy
Group=caddy
ExecStart=/usr/local/bin/caddy run --environ --config /etc/caddy/Caddyfile
ExecReload=/usr/local/bin/caddy reload --config /etc/caddy/Caddyfile
Restart=on-failure
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

Reload systemd and start Caddy:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now caddy
```

### 5. Verify HTTPS and update your client configuration

**Confirm that `https://mcp.your-domain.org/mcp` loads successfully with a valid TLS certificate:**

just pasting the address in a browser should return a JSON RPC error.

**Claude Desktop config:**

You can simply create a new **custom connector** with the HTTPS URL: **Settings>Connectors>Add Custom Connector**, give it a name and your https URL, that's it! You may have to restart Claude Desktop for the change to take effect.



If you have enabled [basic authentication](../../docs/server_guide/SECURITY.md#basic-mode-details) and setup a database proxy user (eg. `https://mcp.your-domain.org/mcp/`), you may pass the database user credentials in the header.

For this head to the **Settings>Developer** section and update your `claude_desktop_config.json` configuration

```json
{
  "mcpServers": {
    "teradata_mcp_remote_aws": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://your-domain.com/mcp/",
        "--header",
        "Authorization: Basic ${AUTH_TOKEN}",
        "--allow-http"
      ],
      "env": {
        "AUTH_TOKEN": "<YOUR_DB_USER:PASSWORD_u64>" 
      }
    }
  }
}
```

### 6. Close port 8001 publicly

Once HTTPS is working, update your AWS security group to close port 8001 from public access to improve security.

---

### Troubleshooting tip

DNS changes can take some time to propagate. If HTTPS does not work immediately, wait a few minutes and retry. Also, Let's Encrypt (used by Caddy) may need a short time to issue certificates on first run. Check Caddy logs with:

```bash
sudo journalctl -u caddy -f
```
