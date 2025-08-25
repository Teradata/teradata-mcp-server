# Audit and security

All database tool calls are traced using [Teradata DBQL](https://docs.teradata.com/r/Enterprise_IntelliFlex_VMware/Database-Administration/Tracking-Query-Behavior-with-Database-Query-Logging-Operational-DBAs) and the MCP server implements query banding by default.

We enable several mechanisms to manage database access (and RBAC policies):
- End user via proxy user (recommended for general use):The MCP server uses a [Permanent proxy user](https://docs.teradata.com/r/Enterprise_IntelliFlex_VMware/SQL-Data-Control-Language/Statement-Syntax/GRANT-CONNECT-THROUGH/CONNECT-THROUGH-Usage-Notes/GRANT-CONNECT-THROUGH-Trusted-Sessions-and-User-Types/Permanent-Proxy-Users) to assume the privileges of the client user using their own database user. Requires user identification.
- Application user (best for application-specific deployments): a single database user is dedicated to the MCP Server instance.
- End user direct authentication: The end user passes their database credentials (eg. JWT token) via the client.

We enable several mechanisms to authenticate to the server:
- No authentication (AUTH_MODE=none)
- Basic authentication (AUTH_MODE=basic)
- OAuth 2.1
  - JWT without verification AUTH_MODE=oauth_no_verify)
  - JWT with IDP verification (AUTH_MODE=oauth_verify)
  - Full OAuth with introspection (AUTH_MODE=oauth_full)

## Tracing tool calls

By default, all tool calls are identified in the Teradata database with [QueryBand](https://docs.teradata.com/r/Enterprise_IntelliFlex_VMware/Database-Administration/Managing-Database-Resources-Operational-DBAs/Managing-Sessions-and-Transactions-with-Query-Banding/Finding-the-Origin-of-a-Query-Using-Query-Bands).

Example of output in `dbc.qrylog.QueryBand`:

`=T> APPLICATION=teradata-mcp-server;PROCESS_ID=myserver:58488;TOOL_NAME=base_databaseList;REQUEST_ID=06c782e231484316b4caa500194d539c;SESSION_ID=06c782e231484316b4caa500194d539c;USER_AGENT=node;AUTH_SCHEME=Bearer;AUTH_HASH=b7ca7936a723;`

The following parameters are included in the query band for each tool call:

| Key         | Description                                                           | Source                                                                                      |
|-------------|-----------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| APPLICATION | Name of the calling application (e.g., `teradata-mcp-server`)         | FastMCP server name (`mcp.name`)                                                            |
| PROFILE     | Profile or role associated with the server instance (if available)       | Selected profile for the server process                                                                |
| PROCESS_ID  | Identifier for the process making the request                         | Hostname + process ID                                                                       |
| TOOL_NAME   | Name of the tool or API endpoint invoked                              | Current tool name                                                                           |
| REQUEST_ID  | Unique identifier for the request                                     | FastMCP request context ID (or UUID fallback)                                               |
| SESSION_ID  | FastMCP session id (or request_id fallback)                           | FastMCP session id (or request_id fallback)                                                 |
| TENANT      | Tenant or customer identifier (if applicable)                         | Header (`x-td-tenant` / `x-tenant`)                                                         |
| CLIENT_IP   | IP address of the client making the request                           | Header (`x-forwarded-for`), if provided                                                     |
| USER_AGENT  | User agent string from the client                                     | Header (`user-agent`)                                                                       |
| AUTH_SCHEME | Authentication scheme used (e.g., `Bearer`, `Basic`)                  | Header (`authorization` scheme)                                                             |
| AUTH_HASH   | Hashed value representing the authentication credential or token       | SHA-256 hash of the authorization token                                                     |

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
| dba_resusageSummary        | DEMO_USER  | 23       | 0:00:00.001304     |
| dba_systemSpace            | DEMO_USER  | 10       | 0:00:00.000000     |
| base_readQuery             | DEMO_USER  | 9        | 0:00:00.001111     |
| base_tablePreview          | DEMO_USER  | 8        | 0:00:00.001250     |
| base_tableList             | DEMO_USER  | 7        | 0:00:00.000000     |


## Database Access

### Proxy user

This requires you to create a proxy user for the MCP Server in advance, and associate existing databases users so the MCP Server user can assume their identity.

Here is how you can do it:

Create a proxy user for the MCP Server
```SQL
CREATE USER mcp_svc AS 
    PASSWORD = mcp_svc
    ,PERM = 10e9  -- Adjust as needed
    ,SPOOL = 10e9  -- Adjust as needed
    ,ACCOUNT = 'service_account';
```

If you use a system admin user to manage users and roles make sure that it has CTCONTROL rights on the proxy user
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

Now you can use this the proxy user in as the MCP Server database connection, eg.

```sh
export DATABASE_URI="teradata://mcp_svc:mcp_svc@yourteradatasystem.teradata.com:1025"
uv run teradata-mcp-server --mcp_transport streamable-http --mcp_port 8001
```

**FOR DEMO PURPOSE**
In your client, indicate the end user name to assume in the http header.

For example, with Clause Desktop  `claude_desktop_config.json`, to assume the `demo_user` user.

```json
{
  "mcpServers": {
   "teradata_mcp_remote": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:8001/mcp/", "--header", "AssumeUser: ${DB_USER}"],
      "env": { "DB_USER": "demo_user" }
    }
  }
}

### End user direct authentication
Example: using Claude Desktop with [mcp-remote](https://www.npmjs.com/package/mcp-remote) to authentcate using a Baerer token:

Add the server configuration in `claude_desktop_config.json`

```json
{
  "mcpServers": {
   "teradata_mcp_remote": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:8001/mcp/", "--header", "Authorization: Bearer ${AUTH_TOKEN}"],
      "env": { "AUTH_TOKEN": "thisismytoken" }
    }
  }
}
```

## Reporting a Vulnerability

The teradata-mcp-server community take security seriously.

We apprciate your efforts to responsibly disclose your findings, and will make every effort to acknowledge your contribution.

To report a security issue, please use the GitHub Security Advisory ["Report a Vulnerability"](https://github.com/Teradata/teradata-mcp-server/security/advisories)
