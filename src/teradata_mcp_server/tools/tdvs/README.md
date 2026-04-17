# Teradata VectorStore tools

Leverage Teradata Vector Store capabilities to manage and use vector stores in Teradata.

## Dependencies

### Teradata software

Teradata Vector Store requires **Teradata Vantage 20.0** or later (the vector data type was introduced in this release).

### Python package

The `tdvs` module depends on the `teradatagenai` library, which is an optional dependency. Install it using the `[tdvs]` extra:

```bash
# With uv
uv tool install "teradata-mcp-server[tdvs]"

# With pip
pip install "teradata-mcp-server[tdvs]"
```

### Configuration

The `tdvs` module requires the following environment variables (or `.env` file entries):

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URI` | Yes | Teradata connection string — `teradata://user:pass@host:1025/database` |
| `TD_BASE_URL` | Yes | Base URL of the Teradata Vector Store service (e.g. `https://your-tdvs-host/api`) |
| `TD_PAT` | No | Personal Access Token for Vector Store authentication. If omitted, `DATABASE_URI` credentials are used. |
| `TD_PEM` | No | Path to PEM certificate file. Used together with `TD_PAT` for certificate-based auth. |

**Authentication behaviour:**
- If both `TD_PAT` and `TD_PEM` are set → PAT + certificate authentication
- Otherwise → username and password are extracted from `DATABASE_URI`

**Example `.env` file:**

```dotenv
DATABASE_URI=teradata://myuser:mypassword@my-host:1025/mydb
TD_BASE_URL=https://my-tdvs-host/api
TD_PAT=my-personal-access-token
TD_PEM=/path/to/my/cert.pem
```

## Tools

- `tdvs_get_health` - Check the health of the Teradata Vector Store service
- `tdvs_list` - List all vector stores
- `tdvs_get_details` - Get details of a specific vector store
- `tdvs_destroy` - Delete a vector store
- `tdvs_grant_user_permission` - Grant a user permission to use a vector store
- `tdvs_revoke_user_permission` - Revoke a user's permission to use a vector store
- `tdvs_similarity_search` - Perform similarity search against a vector store
- `tdvs_create` - Create a new vector store
- `tdvs_update` - Update / add data in a vector store
- `tdvs_ask` - Find contextual information related to a query

[Return to Main README](../../../../README.md)
