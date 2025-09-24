# MCP Performance Benchmark Tool

A performance testing tool for MCP (Model Context Protocol) servers.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Your MCP Server

Ensure your MCP server is running. For example:
```bash
# Your server should be running at http://localhost:8001/mcp/
```

### 3. Run Performance Test

```bash
python run_perf_test.py configs/perf_test.json
```

## Configuration

### Basic Configuration

Create a JSON configuration file with server details and test streams:

```json
{
  "server": {
    "host": "localhost",
    "port": 8001
  },
  "streams": [
    {
      "stream_id": "stream_01",
      "test_config": "configs/real_tools_test.json",
      "duration": 30,
      "loop": true
    }
  ]
}
```

### Test Cases Configuration

Define which tools/methods to test in a separate JSON file:

```json
{
  "test_cases": {
    "tool_name": [
      {
        "name": "test_name",
        "parameters": {
          "param1": "value1"
        }
      }
    ]
  }
}
```

## Available Test Configurations

- `configs/perf_test.json` - 3 concurrent streams, 30 seconds each
- `configs/minimal_test.json` - Single stream, 5 seconds (quick test)
- `configs/load_test.json` - Heavy load test with multiple streams
- `configs/real_tools_test.json` - Tests with actual MCP tools

## Example Commands

### Quick Test (5 seconds)
```bash
python run_perf_test.py configs/minimal_test.json
```

### Standard Performance Test (30 seconds)
```bash
python run_perf_test.py configs/perf_test.json
```

### Custom Server
```bash
# Edit config to point to your server:
# "host": "your-server.com", "port": 8080
python run_perf_test.py your_config.json
```

## Output

The tool provides:
- Real-time progress during testing
- Per-stream metrics (requests, success rate, response time)
- Overall performance summary
- Throughput in requests per second

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
```

## Architecture

- `run_perf_test.py` - Main test runner
- `mcp_streamable_client.py` - MCP client implementation
- `configs/` - Test configuration files

## Creating Custom Tests

1. Create a test cases file with your tools:
```json
{
  "test_cases": {
    "your_tool": [
      {
        "name": "your_test",
        "parameters": {}
      }
    ]
  }
}
```

2. Create a main config pointing to your test:
```json
{
  "server": {
    "host": "localhost",
    "port": 8001
  },
  "streams": [
    {
      "stream_id": "test",
      "test_config": "path/to/your/test.json",
      "duration": 10,
      "loop": true
    }
  ]
}
```

3. Run the test:
```bash
python run_perf_test.py your_config.json
```

## Notes

- The tool properly handles MCP session initialization
- Supports concurrent test streams
- Automatically discovers available tools on the server
- Measures response time and throughput
- Provides 100% success rate tracking