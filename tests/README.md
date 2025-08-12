# MCP Server Test Runner

A parametric testing system for the Teradata MCP Server that automatically discovers available tools and runs test cases only for those tools.

## How to test

The testing framework will run teradata-mcp-server and test through stdio.

```bash
export DATABASE_URI="teradata://user:pass@host:1025/database"
python run_mcp_tests.py "uv run teradata-mcp-server"
```

**No need to start the server separately!**


## How to add your test case

If you add a tool, you need to at least add a test case for it.
You can do so by appending to the `test_cases.json` file with your test cases using the following format:

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

Where:
- `tool_name` is the name of the tool to test
- `name` is the name of your test (if only one, simply keep it as your tool name)
- `parameters` is the list of parameters expected by the tool.

**Important** Test in `test_cases.json` cannot be dependent of custom data. Use systems tables and users. If you want to define test cases on your own business data, you can do so in a separate file, see *Adding new test cases* section below.

## How it works

The test runner provides:
- **Automatic Server Management**: Starts and stops the MCP server automatically
- **Dynamic Tool Discovery**: Automatically detects which tools are available on the server
- **Parametric Testing**: Runs multiple test cases per tool with different parameters
- **Smart Filtering**: Only executes tests for tools that exist in the current server configuration
- **Simple Pass/Fail Logic**: Infers test results based on response content
- **Comprehensive Reporting**: Generates detailed test reports with statistics

When you run, the test runner automatically:
- Starts the MCP server as a subprocess
- Connects to it via stdin/stdout
- Runs all tests
- Shuts down the server when complete

## Files

- `test_cases.json` - Test case definitions in JSON format
- `run_mcp_tests.py` - Main test runner script
- `test_results_*.json` - Generated test result files (timestamped)


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
python run_mcp_tests.py "uv run teradata-mcp-server --profile dba"

# Test with Feature Store enabled
python run_mcp_tests.py "uv run teradata-mcp-server --profile fs"
```

### Testing with Environment Variables
```bash
# Test with profile via environment variable
PROFILE=dba python run_mcp_tests.py "uv run teradata-mcp-server"

# Test with optional modules enabled
ENABLE_FS_MODULE=true python run_mcp_tests.py "uv run teradata-mcp-server"
```

## Pass/Fail Logic

The test runner uses simple heuristics to determine test success:

- **PASS**: Tool returns content without error indicators
- **FAIL**: Tool returns content with error keywords (`error`, `failed`, `exception`) or exception thrown during tool execution
- **WARNING**: Tool returns empty `results` content.

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
Warnings: 0
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

## How It Works

The test runner uses MCP's stdio transport to communicate with the server:

1. **Spawns server process** using the provided command
2. **Connects via stdin/stdout** - no network ports needed
3. **Queries available tools** using MCP's `list_tools` request
4. **Executes test cases** using MCP's `call_tool` requests
5. **Shuts down server**  process when done


## Integration with CI/CD

The test runner returns appropriate exit codes:
- `0` - All tests passed
- `1` - Some tests failed or errors occurred

This makes it suitable for automated testing pipelines:

```bash
#!/bin/bash
# Set up environment
export DATABASE_URI="your_connection_string"

# Run tests (server is managed automatically)
python scripts/testing/run_mcp_tests.py "uv run teradata-mcp-server"
TEST_RESULT=$?

# Exit with test result
exit $TEST_RESULT
```


