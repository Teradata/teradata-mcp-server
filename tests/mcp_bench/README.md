# MCP Performance Benchmark Tool

A performance testing tool for MCP (Model Context Protocol) servers supporting multiple concurrent streams of test cases with authentication support and detailed performance reporting.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Your MCP Server

Ensure your MCP server is running in streamable http and accessible. For example:
```bash
uv run python -m teradata_mcp_server.server --mcp_transport streamable-http --mcp_port 8001 --auth_mode none
# Your server should be running at http://localhost:8001/mcp/
```

For authenticated testing:
```bash
uv run python -m teradata_mcp_server.server --mcp_transport streamable-http --mcp_port 8001 --auth_mode Basic
```

### 3. Run Performance Test

**Simple Test (no auth):**
```bash
python run_perf_test.py configs/scenario_simple.json
```

**Authenticated Test:**
```bash
export AUTH_TOKEN="ZGVtb191c2VyOmRlbW9fdXNlcg=="
python run_perf_test.py configs/scenario_simple_auth.json
```

## Configuration

We separately define configuration files for *test cases* and *scenarios*. 

Test cases files define the list of MCP tool calls that will be issued, and scenarios the streams that will execute the cases.
A single case file may contain multiple tool calls, they will be executed sequentially in the order they are defined.
A scenario file may contain multiple stream definitions, they will be executed concurrently. Streams may be configured to loop over the test cases definitions and end after a specific duration.

### Basic Configuration

We provide multiple case and scenario files:
- `cases_mixed.json` A small sample of mixed "base" tool calls.
- `cases_tactical.json` A series of tactical queries using the `base_readQuery` tool.
- `cases_error.json` Erroneous tool calls (using wrong/missing parameters or tool names).
- `scenario_simple`: Single stream quick test (5 seconds, no loop).
- `scenario_concurrence`: Three concurrent streams running the three test cases files above in loop for 30 seconds.
- `scenario_load`: 50 concurrent streams running the cases above in loop for 5 minutes.
- `scenario_simple_auth`: Basic authentication testing with a single stream.
- `scenario_env_example`: Example configuration showing environment variable usage.

### Creating your own scenarios

You may create new cases and scenario JSON files to configure your own test scenarios:

**Cases Example**

```json
{
  "test_cases": {
    "base_databaseList": [
      {
        "name": "database_list_test",
        "parameters": {}
      }
    ],
    "base_readQuery": [
      {
        "name": "simple_query_test",
        "parameters": {
          "sql": "select top 10 * from dbc.tablesv"
        }
      },
      {
        "name": "tactical_query_test",
        "parameters": {
          "sql": "sel * from dbc.dbcinfo where infokey='VERSION'"
        }
      }

    ]
  }
}
```

**Scenario Example (no authentication)**
```json
{
  "server": {
    "host": "localhost",
    "port": 8001
  },
  "streams": [
    {
      "stream_id": "stream_01",
      "test_config": "tests/mcp_bench/configs/cases_mixed.json",
      "duration": 30,
      "loop": true
    },
    {
      "stream_id": "stream_02",
      "test_config": "tests/mcp_bench/configs/cases_error.json",
      "duration": 30,
      "loop": true
    }
  ]
}
```

**Scenario Example (with stream-level authentication)**
```json
{
  "server": {
    "host": "localhost",
    "port": 8001
  },
  "streams": [
    {
      "stream_id": "stream_01",
      "test_config": "tests/mcp_bench/configs/cases_mixed.json",
      "duration": 30,
      "loop": true,
      "auth": {
        "Authorization": "Basic $AUTH_TOKEN"
      }
    },
    {
      "stream_id": "stream_02",
      "test_config": "tests/mcp_bench/configs/cases_error.json",
      "duration": 30,
      "loop": true,
      "auth": {
        "Authorization": "Basic $AUTH_TOKEN_USER2"
      }
    }
  ]
}
```

## Authentication Support

The MCP benchmark client supports Basic Authentication for testing servers that require authentication.

### Environment Variables

The configuration system supports environment variable expansion for secure token management:

```bash
export AUTH_TOKEN="ZGVtb191c2VyOmRlbW9fdXNlcg=="
```

Configuration files can reference environment variables using:
- `$VARIABLE_NAME` syntax
- `${VARIABLE_NAME}` syntax

### Authentication Configuration

Authentication is configured at the **stream level** (recommended for testing different users):

```json
{
  "server": {
    "host": "localhost",
    "port": 8001
  },
  "streams": [
    {
      "stream_id": "test_01",
      "test_config": "tests/mcp_bench/configs/cases_mixed.json",
      "duration": 5,
      "loop": false,
      "auth": {
        "Authorization": "Basic $AUTH_TOKEN"
      }
    }
  ]
}
```

### Generating Auth Tokens

Use the included auth helper utility to generate Basic Auth tokens:

```bash
# Generate a token
python tests/mcp_bench/auth_helper.py encode demo_user demo_user

# Output:
# Basic Auth Token: ZGVtb191c2VyOmRlbW9fdXNlcg==
# Authorization Header: Authorization: Basic ZGVtb191c2VyOmRlbW9fdXNlcg==

# Decode a token (for verification)
python tests/mcp_bench/auth_helper.py decode ZGVtb191c2VyOmRlbW9fdXNlcg==

# Output:
# Username: demo_user
# Password: demo_user
```


## Example Commands

### Quick Test (5 seconds, no auth)
```bash
python tests/mcp_bench/run_perf_test.py tests/mcp_bench/configs/scenario_simple.json
```

### Authenticated Test
```bash
export AUTH_TOKEN="ZGVtb191c2VyOmRlbW9fdXNlcg=="
python tests/mcp_bench/run_perf_test.py tests/mcp_bench/configs/scenario_simple_auth.json
```

### Load Test with Authentication (50 streams, 5 minutes)
```bash
export AUTH_TOKEN="ZGVtb191c2VyOmRlbW9fdXNlcg=="
python tests/mcp_bench/run_perf_test.py tests/mcp_bench/configs/scenario_load.json
```

### Verbose Output

This enables you to see the request/response details:

```bash
python tests/mcp_bench/run_perf_test.py tests/mcp_bench/configs/scenario_simple.json --verbose
```


## Output

The tool provides:
- Real-time progress during testing
- Per-stream metrics (requests, success rate, response time)
- Overall performance summary
- Throughput in requests per second
- **Detailed JSON reports** saved to `var/mcp-bench/reports/`

### Verbose Mode
With `--verbose` flag, you'll see:
- Each request's method and parameters
- Response content previews
- Success/failure status with timing
- Detailed error messages

### Sample Output
```
============================================================
RESULTS
============================================================

Stream stream_01:
  Requests: 1719
  Success Rate: 100.0%
  Avg Response: 6.33ms
  Throughput: 57.27 req/s

OVERALL:
  Total Requests: 5155
  Successful: 5155
  Failed: 0
  Success Rate: 100.0%
============================================================

📊 Detailed report saved to: var/mcp-bench/reports/perf_report_20250924_174226.json
```

### Multi-User Testing

You can test concurrent streams with different users by setting multiple environment variables:

```bash
export AUTH_TOKEN="ZGVtb191c2VyOmRlbW9fdXNlcg=="          # demo_user:demo_user
export AUTH_TOKEN_USER2="YWRtaW46YWRtaW4="                # admin:admin
export AUTH_TOKEN_USER3="Z3Vlc3Q6Z3Vlc3Q="                # guest:guest
```

Then configure different streams to use different tokens:

```json
{
  "streams": [
    {
      "stream_id": "user1_stream",
      "auth": { "Authorization": "Basic $AUTH_TOKEN" }
    },
    {
      "stream_id": "user2_stream",
      "auth": { "Authorization": "Basic $AUTH_TOKEN_USER2" }
    },
    {
      "stream_id": "user3_stream",
      "auth": { "Authorization": "Basic $AUTH_TOKEN_USER3" }
    }
  ]
}
```

## Claude Desktop Integration

This authentication format matches Claude Desktop MCP configurations:

```json
{
  "mcpServers": {
    "teradata-mcp-server": {
      "command": "mcp-remote",
      "args": [
        "http://localhost:8001/mcp/",
        "--header",
        "Authorization: Basic ${AUTH_TOKEN}"
      ],
      "env": {
        "AUTH_TOKEN": "ZGVtb191c2VyOmRlbW9fdXNlcg=="
      }
    }
  }
}
```

## Security Notes

- Basic Auth tokens are Base64 encoded, not encrypted - use HTTPS in production
- Store auth tokens securely and avoid committing them to version control
- Use environment variables for sensitive authentication data
- The demo token `ZGVtb191c2VyOmRlbW9fdXNlcg==` encodes `demo_user:demo_user`

## Architecture

- `run_perf_test.py` - Main test runner with environment variable expansion
- `mcp_streamable_client.py` - MCP client implementation with auth support
- `auth_helper.py` - Authentication token encoding/decoding utility
- `configs/` - Test configuration files
  - `scenario_*.json` - Stream configurations
  - `cases_*.json` - Test case definitions