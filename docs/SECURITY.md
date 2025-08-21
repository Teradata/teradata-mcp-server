# Audit and security


We enable several mechanisms to authenticate to the database:
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

| Key           | Description                                                           |
|---------------|-----------------------------------------------------------------------|
| APPLICATION   | Name of the calling application (e.g., `teradata-mcp-server`)         |
| PROFILE       | Profile or role associated with the user/session (if available)       |
| PROCESS_ID    | Identifier for the process making the request                         |
| TOOL_NAME     | Name of the tool or API endpoint invoked                              |
| REQUEST_ID    | Unique identifier for the request                                     |
| SESSION_ID    | Unique identifier for the session                                     |
| TENANT        | Tenant or customer identifier (if applicable)                         |
| CLIENT_IP     | IP address of the client making the request                           |
| USER_AGENT    | User agent string from the client                                     |
| AUTH_SCHEME   | Authentication scheme used (e.g., `Bearer`, `Basic`)                  |
| AUTH_HASH     | Hashed value representing the authentication credential or token       |

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


## Authentication to the database

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

</file>
