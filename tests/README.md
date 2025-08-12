# MCP Server Test Runner

A parametric testing system for the Teradata MCP Server that automatically discovers available tools and runs test cases only for those tools.

## How to test

The testing framework will run teradata-mcp-server and test through stdio.

```bash
export DATABASE_URI="teradata://user:pass@host:1025/database"
python tests/run_mcp_tests.py "uv run teradata-mcp-server"
```

**No need to start the server separately!**


## How to add your test case

If you add a tool, you need to at least add a test case for it.
You can do so by appending to the `core_test_cases.json` file with your test cases using the following format:

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

**Important** Test in `core_cases.json` cannot be dependent of custom data. Use systems tables and users. If you want to define test cases on your own business data or an optional module, you can do so in a separate file, see *Custom and add-on Test Cases File* section below.

## Overview

The test runner provides:
- **Dynamic Tool Discovery**: Automatically detects which tools are available on the server
- **Parametric Testing**: Runs multiple test cases per tool with different parameters
- **Smart Filtering**: Only executes tests for tools that exist in the current server configuration
- **Simple Pass/Fail Logic**: Infers test results based on response content
- **Comprehensive Reporting**: Generates detailed test reports with statistics

## Files

- `tests/cases/*_cases.json` - Test case definitions in JSON format
- `tests/run_mcp_tests.py` - Main test runner script
- `var/test-reports/test_report_*.json` - Generated test result files (timestamped)


## Test Case Format

The `core_test_cases.json` file defines test cases for each tool:

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

**Using UV (recommended for production):**
```bash
python tests/run_mcp_tests.py "uv run teradata-mcp-server"
```

**Using Python directly (for development):**
```bash
# After installing in development mode (pip install -e .)
python tests/run_mcp_tests.py "python -m teradata_mcp_server"

# Or run the server file directly with PYTHONPATH
PYTHONPATH=src python tests/run_mcp_tests.py "python src/teradata_mcp_server/server.py"
```

**Using Python with PYTHONPATH (for development from source):**
```bash
PYTHONPATH=src python tests/run_mcp_tests.py "python -m teradata_mcp_server"
```

### Custom and add-on Test Cases File

You can add your own test cases into separate files, or invoke additional test modules.

Currently available modules:
- `core_test_cases.json` foundational test cases, default and mandatory cases for system integration testing.
- `evs_test_cases.json` for Teradata Enterprise Vector Store testing.
- `fs_test_cases.json` for Teradata Enterprise Feature Store testing.

To specific modules, specify the module name in second position. eg.:
```bash
python tests/run_mcp_tests.py "uv run teradata-mcp-server" "tests/cases/fs_test_cases.json"
```

### Verbose Output
```bash
python tests/run_mcp_tests.py "uv run teradata-mcp-server" --verbose
```

### Testing Different Profiles
```bash
# Test with DBA profile (UV)
PROFILE=dba python tests/run_mcp_tests.py "uv run teradata-mcp-server"

# Test with DBA profile (Python)
PROFILE=dba python tests/run_mcp_tests.py "python -m teradata_mcp_server"

# Test with Feature Store enabled
python tests/run_mcp_tests.py "uv run teradata-mcp-server --profile fs"
python tests/run_mcp_tests.py "python -m teradata_mcp_server --profile fs"
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
Errors: 0
Success Rate: 100.0%

PERFORMANCE:
Total Time: 1.23s
Average Time: 0.21s per test

Detailed results saved to: test_results_20250811_143022.json
```

## Adding New Test Cases

1. **Edit `core_test_cases.json`** to add test cases for new tools
2. **Follow the JSON format** with tool names as keys
3. **Include parameters** that the tool expects
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

You can add pre/post scripts (eg. to load the environment with specific datasets and clean it up afterwards) by adding a `scripts` section to your test definitions.

```
  "scripts": {
    "pre_test": {
      "command": "python tests/scripts/efs_setup.py --action setup",
      "description": "Setup Feature Store test environment"
    },
    "post_test": {
      "command": "python tests/scripts/efs_setup.py --action cleanupSQL", 
      "description": "Display SQL commands to cleanup Feature Store test environment"
    }
  },
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

### Debugging

Add verbose output by modifying the script or checking the detailed JSON results file for more information about failures.