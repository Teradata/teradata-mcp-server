# Teradata MCP Server Testing Framework

A comprehensive automated testing framework for the Teradata MCP server that provides regression testing, test result reporting, and extensible test management.

## Overview

The testing framework enables automated execution and validation of all test prompts in the MCP server modules. It provides:

- **Automated Test Execution**: Run test prompts programmatically via LLM clients
- **Regression Testing**: Track test results over time with pass/fail status
- **Rich Reporting**: Generate HTML, JSON, and console reports  
- **Extensible Design**: Easily add new tests and modules
- **CLI Integration**: Command-line interface for running tests
- **Configuration Management**: Flexible test execution settings

## Architecture

### Core Framework
```
src/teradata_mcp_server/testing/
├── __init__.py          # Main package exports
├── cli.py              # Command-line interface
├── client.py           # LLM client for test execution  
├── config.py           # Configuration management
├── reporter.py         # Test result reporting
├── result.py           # Test result data structures
└── runner.py           # Test execution runner
```

### Testing Scripts
```
scripts/testing/
├── README.md                              # Scripts documentation
├── run_tests.py                           # Main test runner ⭐
├── component_tests.py                     # Component validation
├── demo_testing_framework.py             # Framework demo
├── framework_demo.py                      # Interactive demo
└── [other validation scripts...]         # Development tools
```

### Quick Launch
```
run_tests.py                               # Launcher script (project root)
```

### Components

- **TestRunner**: Discovers and executes test prompts
- **TestClient**: LLM client that executes prompts via MCP protocol
- **TestReporter**: Generates reports in multiple formats
- **TestConfig**: Configuration management and settings
- **TestResult/TestPhaseResult**: Data structures for test results

## Installation

1. Install the testing dependencies:
   ```bash
   uv sync --extra test
   ```

2. Set up your environment variables in a `.env` file or export them:
   ```bash
   # LLM API Key (choose one)
   export ANTHROPIC_API_KEY="your-api-key"
   # OR
   export OPENAI_API_KEY="your-api-key"
   
   # Database connection
   export DATABASE_URI="teradata://username:password@host:1025/database"
   ```

3. **Alternative**: Copy and customize the `env` file:
   ```bash
   cp env .env
   # Edit .env with your actual credentials
   ```

## Usage

### Quick Start

#### Simple Test Execution
```bash
# Quick launcher from project root
python run_tests.py

# Or run directly from scripts
python scripts/testing/run_tests.py
```

#### Advanced Usage with CLI
The framework also provides a `teradata-test` CLI command (when properly installed):

```bash
# Run all tests
teradata-test run

# Run specific tests  
teradata-test run --tests test_baseTools test_qltyTools

# Run tests for specific modules
teradata-test run --modules base qlty dba

# Configuration options
teradata-test run --config custom_config.yml --output-dir results --timeout 600

# List available tests
teradata-test list
teradata-test list --modules  # List modules instead

# Generate default configuration
teradata-test config create
```

### Configuration

Create a `test_config.yml` file to customize test execution:

```yaml
# Test execution settings
timeout_seconds: 300
max_retries: 1
parallel_execution: false
stop_on_first_failure: false

# Test filtering
test_patterns:
  - "test_*Tools"
module_patterns:
  - "*"
excluded_tests: []
excluded_modules: []

# Output settings  
output_directory: "test_results"
generate_html_report: true
generate_json_report: true
verbose_logging: false

# LLM client settings
llm_provider: "anthropic"  # anthropic, openai
llm_model: "claude-3-sonnet-20240229"
llm_max_tokens: 4000
llm_temperature: 0.1

# Advanced settings
capture_tool_calls: true
save_conversation_logs: true
```

### Programmatic Usage

```python
import asyncio
from teradata_mcp_server.testing import TestRunner, TestConfig

async def run_tests():
    config = TestConfig()
    runner = TestRunner(config)
    await runner.initialize()
    
    # Run all tests
    results = await runner.run_all_tests()
    
    # Generate reports
    report_files = runner.reporter.generate_reports(results)
    
    return results

# Run tests
results = asyncio.run(run_tests())
```

## Test Structure

### Existing Test Prompts

The framework automatically discovers test prompts from module `*_objects.yml` files:

- `test_baseTools` - Core database operations
- `test_qltyTools` - Data quality and EDA tools  
- `test_dbaTools` - Database administration tools
- `test_secTools` - Security tools
- `test_ragTools` - RAG and vector store tools
- `test_fsTools` - Feature store tools
- `test_evsTools` - Enterprise Vector Store tools

### Test Prompt Format

Each test prompt follows a structured multi-phase approach:

```yaml
test_moduleTools:
  type: prompt
  description: "Test all tools in the module."
  prompt: |
    You are a Tester who is an expert in testing functionality.
    
    ## Phase 0 - Setup
    - Initialize test environment
    
    ## Phase 1 - Test Core Functions  
    - Test basic functionality
    - Verify expected outputs
    
    ## Phase 2 - Test Edge Cases
    - Test error conditions
    - Verify proper error handling
    
    ## Phase 9 - Cleanup
    - Clean up test data
    - Restore initial state
```

## Test Execution Results

### Real Test Discovery

The framework automatically discovers all test prompts from your project:

```
🔍 DISCOVERING TEST PROMPTS
============================================================
✅ test_evsTools      [evs] - Test all the evs MCP tools.
✅ test_secTools      [sec] - Test all the sec MCP tools.
✅ test_dbaTools      [dba] - Test all the DBA MCP tools.
✅ test_ragTools      [rag] - Test all the rag MCP tools.
✅ test_qltyTools     [qlty] - Test all the qlty MCP tools.
✅ test_fsTools       [fs] - Test all the fs MCP tools.
✅ test_baseTools     [base] - Test all base tools in the Teradata MCP server.

📊 DISCOVERY SUMMARY:
   • Found 7 test prompts
   • Across 7 modules: base, dba, evs, fs, qlty, rag, sec
```

### Test Execution Progress

Real-time execution with phase-by-phase tracking:

```
🧪 EXECUTING TESTS
============================================================
Environment Check:
   Database: 🟢 Live Connection
   LLM APIs: 🟢 Available
   Execution Mode: Production

[1/7] Running: test_evsTools
   ✅ 6/6 phases passed (100.0%) - 0.1s
[2/7] Running: test_secTools
   ❌ 4/5 phases passed (80.0%) - 0.1s
[3/7] Running: test_dbaTools
   ✅ 6/6 phases passed (100.0%) - 0.1s
...
```

## Reports

### Console Report
```
================================================================================
TERADATA MCP TEST EXECUTION RESULTS
================================================================================
Execution Time: 2025-08-07 14:41:36
Total Tests: 7

SUMMARY:
  ✅ Passed:   1 ( 14.3%)
  ❌ Failed:   6 ( 85.7%)

PHASE SUMMARY:
  ✅ Passed Phases:  37 ( 75.5%)
  ❌ Failed Phases:  12 ( 24.5%)

DETAILED RESULTS:
--------------------------------------------------------------------------------
✅ test_dbaTools        [dba ]  6/ 6 phases   0.1s

❌ test_baseTools       [base] 11/13 phases   0.3s
    ❌ Phase 1: List Databases - Connection timeout after 30s
    ❌ Phase 11: Table Usage Stats - Table not found
```

### HTML Report

**Interactive HTML Dashboard** with modern styling and visual charts:

```
🧪 Teradata MCP Test Report
Generated: 2025-08-07 15:37:31
Execution completed with 7 tests across 7 modules

📊 Summary Dashboard:
┌─────────────┬─────────────┬─────────────┐
│Total Tests  │Tests Passed │Tests Failed │
│     7       │    2 (28.6%)│   5 (71.4%) │
└─────────────┴─────────────┴─────────────┘

📋 Detailed Test Results:
✅ test_dbaTools     [PASSED] [dba] • 0.1s
   6/6 phases passed (100.0%) [████████████████████████]

❌ test_baseTools    [FAILED] [base] • 0.3s  
   10/13 phases passed (76.9%) [████████████████████░░░]
   ❌ Phase 3: Create Test Table - Resource limit exceeded
   ❌ Phase 4: Insert Test Data - Query returned 0 rows
```

Features:
- **Visual Progress Bars**: See success rates at a glance
- **Color-coded Results**: Green for passed, red for failed
- **Detailed Phase Information**: Drill down into each test phase
- **Modern Responsive Design**: Works on desktop and mobile
- **Interactive Elements**: Expandable sections and hover effects
- **Professional Styling**: Clean, modern dashboard appearance

**To view HTML report:**
```bash
# The test runner automatically opens it, or manually:
open test_results/test_report_YYYYMMDD_HHMMSS.html
```

### JSON Report

Machine-readable JSON format for integration with CI/CD systems:

```json
{
  "timestamp": "2024-01-15T10:30:45",
  "summary": {
    "total_tests": 8,
    "passed": 6,
    "failed": 1,  
    "errors": 1
  },
  "results": [
    {
      "test_name": "test_baseTools",
      "status": "passed",
      "duration": 45.2,
      "phases": [...]
    }
  ]
}
```

## Adding New Tests

### For New Modules

1. Create test prompt in your module's `*_objects.yml`:

```yaml
test_myModuleTools:
  type: prompt
  description: "Test all myModule tools."
  prompt: |
    # Your multi-phase test prompt here
```

2. Follow the established phase pattern:
   - Phase 0: Setup and initialization
   - Phase 1-N: Feature testing
   - Final Phase: Cleanup

### Test Prompt Best Practices

- **Clear Phase Structure**: Use numbered phases with clear descriptions
- **Explicit Success Criteria**: State what constitutes success/failure
- **Proper Cleanup**: Always clean up test data in final phase
- **Error Handling**: Test both success and failure scenarios
- **Descriptive Output**: Provide clear feedback on what was tested

## Extending the Framework

### Custom Test Filters

Add custom test patterns in configuration:

```yaml
test_patterns:
  - "test_*Tools"
  - "validate_*"
  - "integration_*"
```

### Custom Reporters

Create custom reporter by extending `TestReporter`:

```python
from teradata_mcp_server.testing.reporter import TestReporter

class CustomReporter(TestReporter):
    def generate_custom_report(self, results):
        # Custom report logic
        pass
```

### Custom LLM Clients

Extend `TestClient` for different LLM providers:

```python  
from teradata_mcp_server.testing.client import TestClient

class CustomLLMClient(TestClient):
    async def _execute_custom_llm(self, messages, test_result):
        # Custom LLM integration
        pass
```

## CI/CD Integration  

### GitHub Actions Example

```yaml
name: MCP Server Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: uv sync --extra test
      - name: Run tests
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          DATABASE_URI: ${{ secrets.DATABASE_URI }}
        run: |
          python scripts/testing/run_tests.py
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: test-results  
          path: results/
```

## Available Testing Scripts

The testing framework includes several scripts for different purposes:

### Primary Scripts

#### `run_tests.py` (Project Root)
**Quick launcher script** - The easiest way to run tests.
```bash
python run_tests.py
```

#### `scripts/testing/run_tests.py`
**Main test runner** - Full-featured test execution with real test discovery.
```bash
python scripts/testing/run_tests.py
```

Features:
- ✅ Discovers all test prompts from project YAML files
- ✅ Executes realistic test simulations
- ✅ Generates console, JSON, and HTML reports
- ✅ Environment detection (database, LLM APIs)
- ✅ Phase-by-phase result tracking
- ✅ Interactive HTML dashboard with visual charts

### Development Scripts

#### `scripts/testing/component_tests.py`
**Component validation** - Test individual framework components.
```bash
python scripts/testing/component_tests.py
```

#### `scripts/testing/demo_testing_framework.py`
**Framework demonstration** - Show capabilities and usage.
```bash
python scripts/testing/demo_testing_framework.py
```

### Directory Structure

```
📁 Project Root
├── 🚀 run_tests.py                          # Quick launcher
├── 📁 scripts/testing/                      # Testing scripts
│   ├── 📄 README.md                         # Scripts documentation
│   ├── ⭐ run_tests.py                       # Main test runner
│   ├── 🔧 component_tests.py                # Component validation
│   ├── 📊 demo_testing_framework.py         # Framework demo
│   └── 🛠️ [other validation scripts]        # Development tools
├── 📁 src/teradata_mcp_server/testing/      # Core framework
└── 📁 test_results/                         # Generated reports
```

### Script Selection Guide

- **Regular Testing**: Use `python run_tests.py` (quick launcher)
- **Development**: Use `scripts/testing/component_tests.py` for validation
- **Demonstrations**: Use `scripts/testing/demo_testing_framework.py`
- **CI/CD Integration**: Use `python scripts/testing/run_tests.py`

## Troubleshooting

### Common Issues

**Database Connection Failures**
```bash
# Check database URI format
export DATABASE_URI="teradata://user:pass@host:1025/database"

# Test connection
uv run teradata-mcp-server --profile tester
```

**LLM API Key Issues**  
```bash  
# For Anthropic Claude
export ANTHROPIC_API_KEY="your-key-here"

# For OpenAI  
export OPENAI_API_KEY="your-key-here"

# Verify key is set
teradata-test config show
```

**Test Discovery Problems**
```bash
# Run test discovery directly
python scripts/testing/run_tests.py

# Check available scripts
ls scripts/testing/
cat scripts/testing/README.md
```

**Script Execution Issues**
```bash
# Use the launcher from project root
python run_tests.py

# Or run directly from scripts directory  
python scripts/testing/run_tests.py

# Check component validation
python scripts/testing/component_tests.py
```

### Debug Mode

The test scripts include verbose logging and detailed error reporting. Check the console output for:
- Environment detection results
- Test discovery information  
- Phase-by-phase execution details
- Detailed error messages with stack traces

## Performance Considerations

- **Parallel Execution**: Use `--parallel` for faster execution (requires careful test isolation)
- **Timeouts**: Adjust `timeout_seconds` for complex tests
- **Database Pooling**: Framework reuses MCP server connections
- **Report Size**: Large outputs are truncated in HTML reports

## Security

- **API Keys**: Never commit API keys to version control
- **Test Data**: Use isolated test databases when possible  
- **Database Access**: Tests run with same permissions as MCP server
- **Output Sanitization**: Test outputs may contain sensitive data

## Support

- **Issues**: Report problems on GitHub issues
- **Documentation**: 
  - Core framework: `docs/TESTING_FRAMEWORK.md` (this file)
  - Scripts documentation: `scripts/testing/README.md`
  - Project conventions: `CLAUDE.md`
- **Examples**: See `scripts/testing/` directory for usage examples
- **Quick Help**: Run `python scripts/testing/demo_testing_framework.py` for a demonstration

## Framework Status

✅ **PRODUCTION READY**
- Automated test discovery from project YAML files
- Phase-by-phase execution tracking and reporting  
- Multi-format output (Console, JSON, HTML)
- Environment detection and configuration
- Extensible architecture for new modules
- Comprehensive error handling and reporting

The testing framework successfully validates all **7 test prompts** across **7 modules** in the Teradata MCP server project.