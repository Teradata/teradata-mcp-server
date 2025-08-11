# Testing Scripts Directory

This directory contains various scripts for testing and validating the Teradata MCP Testing Framework.

## 🚀 Main Scripts

### `run_tests.py` 
**Primary test execution script** - Use this for running the testing framework.

- **Purpose**: Complete testing framework execution with real test discovery
- **Features**: Discovers all test prompts, executes realistic simulations, generates reports
- **Usage**: `python scripts/testing/run_tests.py`
- **Outputs**: Console report + JSON report in `scripts/test_results/`

## 🔧 Development & Validation Scripts

### `component_tests.py`
**Component validation** - Tests individual framework components in isolation.

- **Purpose**: Validate core framework components without server dependencies
- **Tests**: Result structures, configuration, basic functionality
- **Usage**: `python scripts/testing/component_tests.py`

### `demo_testing_framework.py`
**Framework demonstration** - Shows framework capabilities and structure.

- **Purpose**: Demonstrate framework features and architecture
- **Features**: Shows test discovery, component loading, usage instructions
- **Usage**: `python scripts/testing/demo_testing_framework.py`

### `framework_demo.py`
**Interactive framework demo** - Comprehensive framework demonstration.

- **Purpose**: Full framework walkthrough with actual test discovery
- **Features**: Real test prompt discovery, simulated execution, reporting
- **Usage**: `python scripts/testing/framework_demo.py`

## 🧪 Legacy & Experimental Scripts

### `execute_tests.py`
**Experimental test runner** - Alternative implementation approach.

- **Purpose**: Alternative test execution implementation
- **Status**: Experimental, may have import issues
- **Usage**: `python scripts/testing/execute_tests.py`

### `run_tests_legacy.py`
**Legacy test runner** - Original test runner attempt.

- **Purpose**: Early framework implementation
- **Status**: Legacy, kept for reference
- **Usage**: Not recommended for use

### `validate_testing_framework.py`
**Full framework validation** - Comprehensive validation including server components.

- **Purpose**: Complete framework validation with database connections
- **Status**: May fail due to database connection requirements
- **Usage**: `python scripts/testing/validate_testing_framework.py`

### `validate_testing_framework_simple.py`
**Simple validation** - Basic framework validation without database.

- **Purpose**: Core component validation without external dependencies
- **Status**: Simplified validation approach
- **Usage**: `python scripts/testing/validate_testing_framework_simple.py`

## 📋 Quick Start Guide

1. **Run the main testing framework**:
   ```bash
   python scripts/testing/run_tests.py
   ```

2. **Validate framework components**:
   ```bash
   python scripts/testing/component_tests.py
   ```

3. **See framework demonstration**:
   ```bash
   python scripts/testing/demo_testing_framework.py
   ```

## 📁 Directory Structure

```
scripts/testing/
├── README.md                              # This file
├── run_tests.py                           # Main test runner ⭐
├── component_tests.py                     # Component validation
├── demo_testing_framework.py             # Framework demo
├── framework_demo.py                     # Interactive demo
├── execute_tests.py                      # Experimental runner
├── run_tests_legacy.py                   # Legacy implementation
├── validate_testing_framework.py         # Full validation
└── validate_testing_framework_simple.py  # Simple validation
```

## 🎯 Recommended Usage

- **For regular testing**: Use `run_tests.py`
- **For development**: Use `component_tests.py` to validate changes
- **For demos**: Use `demo_testing_framework.py` to show capabilities
- **For troubleshooting**: Check `validate_testing_framework_simple.py`

## 📚 Related Files

- **Framework Source**: `src/teradata_mcp_server/testing/`
- **Documentation**: `docs/TESTING_FRAMEWORK.md`
- **Configuration**: `scripts/test_config.yml`
- **Reports Output**: `scripts/test_results/`