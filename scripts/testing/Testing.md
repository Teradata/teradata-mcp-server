# MCP Server Test Runner

A testing system for the Teradata MCP Server that runs defined tests for tools discovered in the MCP server.


## Run the tests

1. **Start your MCP server** (in a separate terminal):
   ```bash
   uv run teradata-mcp-server
   ```

2. **Run the tests**:
   ```bash
   python run_mcp_tests.py "uv run teradata-mcp-server"
   ```

3. **View results** in the console and detailed JSON output file

## Overview

The test runner provides:
- **Dynamic Tool Discovery**: Automatically detects which tools are available on the server
- **Parametric Testing**: Runs multiple test cases per tool with different parameters
- **Smart Filtering**: Only executes tests for tools that exist in the current server configuration
- **Simple Pass/Fail Logic**: Infers test results based on response content
- **Comprehensive Reporting**: Generates detailed test reports with statistics

## Files

- `test_cases.json` - Test case definitions in JSON format
- `run_mcp_tests.py` - Main test runner script
- `test_results_*.json` - Generated test result files (timestamped)


## Test Case Format

The `test_cases.json` file defines test cases for each tool:

```json
{
  "test_cases": {
    "tool_name": [
      {
        "name": "test_case_name",
        "parameters": {
          "param1": "value1",
          "param2": "value2"
        }
      }
    ]
  }
}
```

### Example Test Cases

```json
{
  "test_cases": {
    "base_readQuery": [
      {
        "name": "simple_select",
        "parameters": {
          "sql": "SELECT 1 as test_column"
        }
      },
      {
        "name": "current_timestamp", 
        "parameters": {
          "sql": "SELECT CURRENT_TIMESTAMP"
        }
      }
    ],
    "sales_top_customers": [
      {
        "name": "top_10",
        "parameters": {
          "limit": 10
        }
      },
      {
        "name": "top_5",
        "parameters": {
          "limit": 5
        }
      }
    ]
  }
}
```

## Usage Examples

### Basic Usage
```bash
python run_mcp_tests.py "uv run teradata-mcp-server"
```

### Custom Test Cases File
```bash
python run_mcp_tests.py "uv run teradata-mcp-server" "my_test_cases.json"
```

### Testing Different Profiles
```bash
# Test with DBA profile
PROFILE=dba python run_mcp_tests.py "uv run teradata-mcp-server"

# Test with Feature Store enabled
python run_mcp_tests.py "uv run teradata-mcp-server --profile fs"
```

### Testing Docker Deployment
```bash
# Start Docker container first
docker compose up -d

# Run tests against containerized server  
python run_mcp_tests.py "docker exec -i teradata-mcp-server-1 teradata-mcp-server"
```

## Pass/Fail Logic

The test runner uses simple heuristics to determine test success:

- **PASS**: Tool returns content without error indicators
- **FAIL**: Tool returns content with error keywords (`error`, `failed`, `exception`) or no content
- **ERROR**: Exception thrown during tool execution

## Sample Output

```
✓ Loaded test cases for 5 tools
Connecting to MCP server: uv run teradata-mcp-server
✓ Connected to MCP server
✓ Discovered 23 available tools
✓ Found test cases for 4 tools
  Tools with tests: base_readQuery, base_tableList, dba_databaseSpace, sales_top_customers
  Tools without tests: base_columnDescription, base_tableDDL, ...

Running 6 test cases...

base_readQuery (2 tests):
  Running base_readQuery:simple_select... PASS (0.12s)
  Running base_readQuery:current_timestamp... PASS (0.08s)

sales_top_customers (2 tests):  
  Running sales_top_customers:top_10... PASS (0.45s)
  Running sales_top_customers:top_5... PASS (0.38s)

================================================================================
TEST REPORT
================================================================================
Total Tests: 6
Passed: 6
Failed: 0
Errors: 0
Success Rate: 100.0%

PERFORMANCE:
Total Time: 1.23s
Average Time: 0.21s per test

Detailed results saved to: test_results_20250811_143022.json
```

## Adding New Test Cases

1. **Edit `test_cases.json`** to add test cases for new tools
2. **Follow the JSON format** with tool names as keys
3. **Include realistic parameters** that the tool expects
4. **Test different scenarios** (valid inputs, edge cases)

Example of adding a new tool:
```json
{
  "test_cases": {
    "my_new_tool": [
      {
        "name": "basic_test",
        "parameters": {
          "required_param": "test_value"
        }
      },
      {
        "name": "edge_case_test", 
        "parameters": {
          "required_param": "",
          "optional_param": "edge_value"
        }
      }
    ]
  }
}
```

## Result Files

Test results are automatically saved to timestamped JSON files:

```json
{
  "timestamp": "2025-08-11T14:30:22.123456",
  "summary": {
    "total": 6,
    "passed": 5,
    "failed": 1,
    "errors": 0
  },
  "results": [
    {
      "tool": "base_readQuery",
      "test": "simple_select",
      "status": "PASS",
      "duration": 0.12,
      "response_length": 45,
      "error": null
    }
  ]
}
```

## Integration with CI/CD

The test runner returns appropriate exit codes:
- `0` - All tests passed
- `1` - Some tests failed or errors occurred

This makes it suitable for automated testing pipelines:

```bash
#!/bin/bash
# Start server in background
uv run teradata-mcp-server &
SERVER_PID=$!

# Wait for server to start
sleep 5

# Run tests
python run_mcp_tests.py "uv run teradata-mcp-server"
TEST_RESULT=$?

# Cleanup
kill $SERVER_PID

# Exit with test result
exit $TEST_RESULT
```

## Troubleshooting

### Common Issues

**"Failed to connect to MCP server"**
- Ensure the server command is correct
- Check that the server starts successfully
- Verify no port conflicts exist

**"No tests to run (no matching tools)"** 
- Check that `test_cases.json` contains tools that exist on your server
- Use tool discovery to see available tools: the script shows which tools have/don't have tests

**"Tool not found" errors**
- The tool may not be available in your current profile
- Check your server configuration and enabled modules
- Some tools require specific database connections or permissions

### Debugging

Add verbose output by modifying the script or checking the detailed JSON results file for more information about failures.