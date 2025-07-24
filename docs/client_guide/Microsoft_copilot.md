## Using with Microsoft Copilot

Developing a Copilot Agent leveraging the Teradata MCP server uses [Microsoft Copilot Studio](https://copilotstudio.microsoft.com/).

---

### Step 1 – Create a New Agent

You can have Copilot help build the agent, or click **Skip to configure** to do it manually (recommended):

- **Name:** TD_MCP_Agent
- **Description:** _(optional)_
- **Instructions:** _(this is effectively the system prompt for the agent)_

  Based on current testing, instructions do **not** reliably reach the LLM. We recommend placing important guidance inside **tool descriptions**, especially if the agent orchestrates multiple tools or knowledge sources. Use this section to describe how the agent should decide what tool to invoke, not detailed usage instructions.

- Click **Create**

---

### Step 2 – Configure the Agent

After the agent is created:

- In the **Agent overview** panel:
  - Keep **Orchestration** enabled
  - Select the response model (e.g., GPT-4o or GPT-4.1 mini)
- In the **Knowledge** section:
  - **Turn off Web Search** (recommended for RAG setups)
  - Optionally, **toggle "Use general knowledge"** – we recommend keeping it ON
- Proceed to add the MCP server as a tool in the next step

---

### Step 3 – Connect MCP Server and Add Tool

- Go to the **Tools** tab
- Click **Add Tool**
- Select **Model Context Protocol**
- If the MCP server is already registered and available:
  - Select it
  - Turn the connection **ON**
  - Click **Add and configure**
  - Verify that tools appear in the Tools section

**Notes:**
- Microsoft currently enforces a **15-tool limit per agent**
- Use `configure_tools.yaml` to enable/disable specific tools for your use case
- Microsoft has announced plans to increase this limit to 60

If you need to create your own MCP connector, see the next section on **Creating a Custom MCP Connector**, then return to this step to add it.

---

### Step 4 – Test the Agent

- Ask: “What databases do I have?”
- First time only:
  - Click **Open Connection Manager** (a new tab opens)
  - Click **Connect** for your server
  - Click **Submit**
- Return to the Agent tab and retry the query

---

## Creating a Custom MCP Connector

### Step 1 – Set Up the Connector in Power Apps

- Go to **New Tool**
- Select **Custom Connector** (opens Power Apps)
- Click **New Custom Connector** > **Import an OpenAPI File**
- Name the connector and upload `copilot_swagger.yaml` from the repo
- Ensure the **host** field in the Swagger file contains a **public IP accessible by Copilot** (see next section)

Click **Continue** and review the configuration:

- **Schema:** `http` (or `https` if your MCP is served over TLS)
- **Host:** Public IP (e.g., from Azure VM)
- **Base URL:** `/` (Copilot appends `/mcp` automatically)
- **Security:** Add OAuth config if required
- Under **Definition**, open the Swagger Editor to confirm or modify the `host` field

Click **Create Connector**

After creating, go back to **Step 3 – Connect MCP Server and Add Tool** and add this connector to the agent.

---

### Step 5 – Publish Your Agent or Connector

You can publish your agent or MCP connector for others to use.  
Refer to Microsoft Copilot Studio's official documentation for publishing details.

---

## Exposing MCP Server Using Azure Port Forwarding

The `copilot_swagger.yaml` file is pre-configured, but you must manually update the `host` field with a public IP accessible by Copilot.

The working setup involves:

- Running the MCP server on a local machine (e.g., inside a VPN)
- Exposing it using a **reverse SSH tunnel** to a lightweight Ubuntu VM hosted on Azure
- This makes the MCP server reachable via the Azure VM’s **public IP**

---

### Preparing the Azure VM and SSH Key

To expose your MCP server, first deploy a lightweight Ubuntu VM and obtain a `.pem` key for SSH access.

#### Step 0 – Create a Lightweight Ubuntu VM on Azure

1. Go to [Azure Portal](https://portal.azure.com/)
2. Click **Create a resource** > **Compute** > **Ubuntu Server**
3. Use the following settings:
   - **Region:** Closest to your location or Copilot region
   - **Image:** Ubuntu Server 20.04 LTS (or later)
   - **Size:** B1s (sufficient for tunneling)
4. Under **Administrator account**:
   - **Authentication type:** SSH public key
   - **Username:** `tddemos` (or another preferred username)
   - **SSH public key source:** Generate new key pair
   - Azure will prompt you to download the `.pem` file  
     **Save it as `ais_key.pem`**
5. Click **Review + Create**, then **Create**

After deployment, note the **public IP address** from the VM Overview page.

---

### Step A – One-Time Setup on Local Machine

#### 1. Set `.pem` permissions

```bash
chmod 400 ais_key.pem
```

#### 2. Enable reverse tunnel support on the Azure VM

```bash
ssh -i ais_key.pem tddemos@<vm_public_ip>
```

Then edit the SSH config:

```bash
sudo vi /etc/ssh/sshd_config
```

Uncomment or add these lines:

```
AllowTcpForwarding yes  
GatewayPorts yes
```

Apply changes:

```bash
sudo systemctl restart ssh
exit
```

---

### Step B – Run MCP on the Local Machine

Ensure your MCP service is running and bound to your VPN-assigned IP (visible in GlobalProtect).

#### To confirm the MCP port binding:

##### For Windows users (PowerShell):

```powershell
netstat -ano | findstr :8001
```

Expected output:

```
TCP    <your_vpn_ip>:8001     0.0.0.0:0     LISTENING
```

##### For macOS/Linux users (Terminal):

```bash
lsof -i :8001
```

or

```bash
netstat -an | grep 8001
```

If MCP is bound to `127.0.0.1`, update your `.env`:

```
MCP_HOST=<your_vpn_ip>  
MCP_PORT=8001
```

Then restart the MCP server so it binds to the correct interface.

---

### Step C – Start the Reverse Tunnel (every session)

From your local machine:

```bash
ssh -i ais_key.pem -R 8001:<your_vpn_ip>:8001 tddemos@<vm_public_ip>
```

- Replace `<your_vpn_ip>` with your machine's VPN-assigned IP
- Replace `<vm_public_ip>` with the Azure VM’s public IP
- Keep this terminal session **open** to maintain the tunnel

---

### Step D – Update the Swagger File

In your `copilot_swagger.yaml`:

- Set the `host` field to the Azure VM’s public IP (e.g., `20.33.77.25`)

```yaml
host: <vm_public_ip>
```

Save the file and re-import it when creating the custom connector.

---

Once the tunnel is active and the Swagger file is updated, your MCP server will be accessible to Copilot via:

```
http://<vm_public_ip>:8001
```

This completes the setup for exposing MCP to Copilot using reverse SSH and Azure.

---
