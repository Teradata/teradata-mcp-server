# Audit and Security

All database tool calls are traced using [Teradata DBQL](https://docs.teradata.com/r/Enterprise_IntelliFlex_VMware/Database-Administration/Tracking-Query-Behavior-with-Database-Query-Logging-Operational-DBAs), and the MCP server implements query banding by default.

We enable several mechanisms to manage database access (and RBAC policies):
- Service Account (recommended for general use): The MCP server uses a [Permanent proxy user](https://docs.teradata.com/r/Enterprise_IntelliFlex_VMware/SQL-Data-Control-Language/Statement-Syntax/GRANT-CONNECT-THROUGH/CONNECT-THROUGH-Usage-Notes/GRANT-CONNECT-THROUGH-Trusted-Sessions-and-User-Types/Permanent-Proxy-Users) to assume the privileges of the client user using their own database user. Requires user identification.
- Application user (best for application-specific deployments): a single database user is dedicated to the MCP Server instance. :warning: If no authentication is enabled, any user reaching the server inherits application user privileges.

We enable several mechanisms to authenticate to the server:
- No authentication (AUTH_MODE=none)
- Basic (AUTH_MODE=basic): accepts either `Authorization: Basic base64(user:secret)` **or** `Authorization: Bearer <jwt>`; the server validates either a password-based DB login (LDAP/KRB5) or a JWT DB login (LOGMECH=JWT) and then proxies as the validated user.
- OAuth (verify) (AUTH_MODE=oauth): verifies an OIDC JWT via JWKS (offline) and proxies as the mapped user.
- OAuth (introspect) (AUTH_MODE=oauth_introspect): verifies JWT via JWKS **and** calls the IdP's token introspection endpoint to ensure the token is active before proxying.

## Tracing Tool Calls

By default, all tool calls are identified in the Teradata database with [QueryBand](https://docs.teradata.com/r/Enterprise_IntelliFlex_VMware/Database-Administration/Managing-Database-Resources-Operational-DBAs/Managing-Sessions-and-Transactions-with-Query-Banding/Finding-the-Origin-of-a-Query-Using-Query-Bands).

Example of output in `dbc.qrylog.QueryBand`:

`=T> APPLICATION=teradata-mcp-server;PROCESS_ID=myserver:58488;TOOL_NAME=base_databaseList;REQUEST_ID=06c782e231484316b4caa500194d539c;SESSION_ID=06c782e231484316b4caa500194d539c;USER_AGENT=node;AUTH_SCHEME=Bearer;AUTH_HASH=b7ca7936a723;`

The following parameters are included in the query band for each tool call:

| Key         | Description                                                                                     | Source                                                                                      |
|-------------|-------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| APPLICATION | Name of the calling application (e.g., `teradata-mcp-server`)                                   | FastMCP server name (`mcp.name`)                                                            |
| PROFILE     | Profile or role associated with the server instance (if available)                             | Selected profile for the server process                                                     |
| PROCESS_ID  | Identifier for the process making the request                                                 | Hostname + process ID                                                                       |
| TOOL_NAME   | Name of the tool or API endpoint invoked                                                      | Current tool name                                                                           |
| REQUEST_ID  | Unique identifier for the request                                                             | FastMCP request context ID (or UUID fallback)                                              |
| SESSION_ID  | FastMCP session ID (or request_id fallback)                                                  | FastMCP session ID (or request_id fallback)                                                |
| TENANT      | Tenant or customer identifier (if applicable)                                                 | Header (`x-td-tenant` / `x-tenant`)                                                        |
| CLIENT_IP   | IP address of the client making the request                                                   | Header (`x-forwarded-for`), if provided                                                    |
| USER_AGENT  | User agent string from the client                                                             | Header (`user-agent`)                                                                       |
| AUTH_SCHEME | Authentication scheme used (e.g., `Basic`, `Bearer` in AUTH_MODE=basic; `Bearer` in AUTH_MODE=oauth and AUTH_MODE=oauth_introspect). | Header (`authorization` scheme)                                                            |
| AUTH_HASH   | Hashed value representing the authentication credential or token                              | SHA-256 hash of the authorization token                                                    |

Admins may optionally enable an additional QueryBand key such as `AUTH_VALIDATION=verify|introspect` to differentiate between OAuth verification and introspection modes in DBQL.

Usage example:

```sql
select  getQueryBandValue(QueryBand, 0, 'TOOL_NAME'), username, count(1) request_cnt, avg(elapsedTime) elapsedTime_avg
from dbc.qrylog
where getQueryBandValue(QueryBand, 0, 'APPLICATION')= 'teradata-mcp-server'
and StartTime (date)=current_date
group by 1,2 order by 3 desc
```

| Tool Name                  | User       | Requests | Avg Elapsed Time   |
|----------------------------|------------|----------|--------------------|
| dba_resusageSummary         | DEMO_USER  | 23       | 0:00:00.001304     |
| dba_systemSpace             | DEMO_USER  | 10       | 0:00:00.000000     |
| base_readQuery              | DEMO_USER  | 9        | 0:00:00.001111     |
| base_tablePreview           | DEMO_USER  | 8        | 0:00:00.001250     |
| base_tableList              | DEMO_USER  | 7        | 0:00:00.000000     |

## Database Access

### Service Account

This requires you to create a proxy user for the MCP Server in advance, and associate existing database users so the MCP Server user can assume their identity.

Here is how you can do it:

Create a proxy user for the MCP Server
```SQL
CREATE USER mcp_svc AS 
    PASSWORD = mcp_svc
    ,PERM = 10e9  -- Adjust as needed
    ,SPOOL = 10e9  -- Adjust as needed
    ,ACCOUNT = 'service_account';
```

If you use a system admin user to manage users and roles, make sure that it has CTCONTROL rights on the proxy user
```SQL
GRANT CTCONTROL ON mcp_svc TO sysdba WITH GRANT OPTION;
```

Proxy sessions use the user’s default role. You can specify roles using the `WITH ROLE` option. 
For more details, see [GRANT CONNECT THROUGH documentation](https://docs.teradata.com/r/Enterprise_IntelliFlex_VMware/SQL-Data-Control-Language/Statement-Syntax/GRANT-CONNECT-THROUGH).

```SQL
GRANT CONNECT THROUGH mcp_svc
  TO PERMANENT demo_user WITHOUT ROLE;
  --, PERMANENT alice   WITHOUT ROLE --Additional users here
```

This server **always** executes via the service account (proxy user). End-user credentials or tokens are only used to authenticate the caller; queries are executed via the service account with `PROXYUSER=<user>` in the **transaction** query band.

:warning: **DEV ONLY** — The `X-Assume-User` header is honored **only** when `AUTH_MODE=none`. In all other modes, identity comes from Basic/Bearer/OAuth and must be validated.

Now you can use this proxy user as the MCP Server database connection, e.g.:

```sh
export DATABASE_URI="teradata://mcp_svc:mcp_svc@yourteradatasystem.teradata.com:1025"
uv run teradata-mcp-server --mcp_transport streamable-http --mcp_port 8001
```

### Application User

This is the default mode for the MCP server: the server instantiates a connection pool to the database as specified in the DATABASE_URI string. This deployment method has the lowest database overhead and is optimal for high-throughput / low-latency applications.

:white_check_mark: Ideal for application-specific instantiation with demanding SLAs.  
- Consider co-locating the server deployment with the application (as well as stdio-based communication)  
- If exposed over a network interface (e.g., streamable HTTP, SSE), implement sufficient network filtering and overlaying authentication mechanisms.

:warning: If no authentication is enabled, any user accessing the MCP Server instance may have access with the privileges of the application user.

Example: server execution co-located  with Claude Desktop and communication over stdio (defined in `claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "teradata": {
      "command": "uv",
      "args": [
        "--directory",
        "<PATH_TO_DIRECTORY>/teradata-mcp-server",
        "run",
        "teradata-mcp-server"
      ],
      "env": {
        "DATABASE_URI": "teradata://<USERNAME>:<PASSWORD>@<HOST_URL>:1025/<USERNAME>",
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
```

Example starting the server over Streamable HTTP, with a dedicated database user:

```sh
export DATABASE_URI="teradata://mcp_applicationuser:mcp_applicationuser_password@yourteradatasystem.teradata.com:1025"
uv run teradata-mcp-server --mcp_transport streamable-http --mcp_port 8001
```

## Authentication

Overview of Authentication Patterns

:warning: **NOT IMPLEMENTED** 

We support multiple authentication mechanisms, ranging from simple static credentials to full OAuth2 flows.
The following patterns are available, and selectable via an AUTH_MODE server setting.

 - No Authentication (AUTH_MODE=none): No credentials required – open access.
 - Basic Authentication (AUTH_MODE=basic): Uses HTTP Basic Auth with a username and password or Bearer token. The server validates the credentials from the database at the session initiation.
 - OAuth (verify) (AUTH_MODE=oauth): Uses Bearer token with OIDC JWT verification via JWKS and user mapping.
 - OAuth (introspect) (AUTH_MODE=oauth_introspect): Uses Bearer token with OIDC JWT verification via JWKS, plus token introspection call to IdP to confirm token active status.

Basic authentication provides a simple way to manage server and data access with minimal setup, leveraging your existing database authentication mechanisms. This can include classic password-based logins as well as OAuth-based JWT database authentication, even though the MCP server itself does not directly interact with the OAuth flow (the client and database perform that validation).

Oauth modes enable you to integrate the MCP server directly with your enterprise SSO/OAuth2 systems  actively verify user access rights. 
For example, if using Keycloak or another OpenID Connect provider, a user could obtain an access token (via login outside the MCP server) and present it to the MCP server; the server will check the token’s signature and metadata. 

### Basic mode details

In `AUTH_MODE=basic`, the server accepts either `Basic` or `Bearer` headers.

- If `Basic`, it decodes `user:secret`. By default, it attempts password-based validation (LDAP/KRB5). If configured to use JWT-in-password, it performs a Teradata JWT DB login using `secret` as the JWT.
- If `Bearer`, it treats the token as a JWT for Teradata JWT DB validation.
- On successful validation, the server sets `PROXYUSER=<principal>` and executes via the service account.

Claude Desktop example for Basic user:pass:

```json
{
  "mcpServers": {
    "teradata_basic": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:8001/mcp/", "--header", "Authorization: Basic ${BASIC_AUTH}"],
      "env": { "BASIC_AUTH": "dXNlcjpwYXNzd29yZA==" }
    }
  }
}
```

Claude Desktop example for Basic with JWT in password (or Bearer):

```json
{
  "mcpServers": {
    "teradata_jwt": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:8001/mcp/", "--header", "Authorization: Bearer ${JWT_TOKEN}"],
      "env": { "JWT_TOKEN": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." }
    }
  }
}
```

### OAuth mode details

`AUTH_MODE=oauth` expects `Authorization: Bearer <JWT>` from a trusted IdP (e.g., Keycloak), verifies via JWKS (`iss`, `aud`, `exp`, `nbf`), maps a claim to the Teradata username, then proxies with `PROXYUSER`.

Example environment variables:

```sh
export OIDC_ISS="https://keycloak.example.com/auth/realms/myrealm"
export OIDC_AUD="my-client-id"
export OIDC_JWKS_URL="https://keycloak.example.com/auth/realms/myrealm/protocol/openid-connect/certs"
export USERMAP_STRATEGY="claim:preferred_username"
```

### OAuth introspection mode details

When `AUTH_MODE=oauth_introspect`, the server first performs JWKS verification (fast, cryptographic), then performs an HTTP POST to the IdP's **token introspection** endpoint to confirm `active=true`.

Pros and cons of the two OAuth modes:

- **Verify mode** (`oauth`): Low-latency and resilient to IdP outages since verification is done offline using JWKS. Suitable for most scenarios with JWT access tokens.
- **Introspection mode** (`oauth_introspect`): Adds immediate token revocation support and opaque token compatibility by querying the IdP's introspection endpoint, but introduces additional latency and dependency on IdP availability.

Configuration variables required for introspection mode:

```sh
export OIDC_INTROSPECT_URL="https://keycloak.example.com/realms/corp/protocol/openid-connect/token/introspect"
export OIDC_CLIENT_ID="teradata-mcp"
export OIDC_CLIENT_SECRET="<secret>"
# Optional timeouts
export OIDC_INTROSPECT_TIMEOUT_MS=2000
```

Notes:

- If tokens are opaque (non-JWT), JWKS verification is skipped and introspection is relied upon exclusively.
- It is recommended to use short access-token TTLs (5–10 min) even when using introspection to limit exposure.

## Reporting a Vulnerability

The teradata-mcp-server community takes security seriously.

We appreciate your efforts to responsibly disclose your findings and will make every effort to acknowledge your contribution.

To report a security issue, please use the GitHub Security Advisory ["Report a Vulnerability"](https://github.com/Teradata/teradata-mcp-server/security/advisories)

## Deployment hardening

Place the MCP server behind NGINX for TLS termination and rate limiting; the app listens on an internal HTTP port only.
