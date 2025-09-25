# MCP Performance Benchmark Tool

A performance testing tool for MCP (Model Context Protocol) servers running multiple concurrent streams of test cases and reporting the errors and performance.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Your MCP Server

Ensure your MCP server is running in streamable http and accesible. For example:
```bash
teradata-mcp-server --mcp_transport streamable-http --mcp_port 8001
# Your server should be running at http://localhost:8001/mcp/
```

### 3. Run Performance Test

```bash
python run_perf_test.py configs/scenario_simple.json
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
- `scenario_simple`: Three concurrent streams running the three test cases files above in loop for 30 seconds.
- `scenario_ load`: 50 concurrent streams running the cases above in loop for 5 minutes.

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

**Cases Example**
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

## Example Commands

### Quick Test (5 seconds)
```bash
python tests/mcp_bench/run_perf_test.py tests/mcp_bench/configs/scenario_simple.json
```

### Standard Performance Test (30 seconds)
```bash
python tests/mcp_bench/run_perf_test.py tests/mcp_bench/configs/scenario_load.json
```

### Verbose Output

This enables you to see the request/response details

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

## Architecture

- `run_perf_test.py` - Main test runner
- `mcp_streamable_client.py` - MCP client implementation
- `configs/` - Test configuration files