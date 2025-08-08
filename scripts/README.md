# Scripts Directory

This directory contains utility scripts for the Teradata MCP Server project.

## 📁 Directory Structure

```
scripts/
├── client_examples/   # Client example implementations
│   ├── ADK_Client_Examples/       # Google ADK client examples
│   ├── Claude_Desktop_Config_Files/  # Claude desktop configurations
│   ├── Copilot_Agent/             # Microsoft Copilot examples
│   ├── MCP_Client_Example/        # MCP protocol client examples
│   └── MCP_VoiceClient/           # Voice-based client
├── testing/           # Testing framework scripts
│   ├── README.md      # Testing scripts documentation
│   ├── run_tests.py   # Main test runner ⭐
│   └── [other files]  # Development and validation scripts
└── test_results/      # Generated test reports
```

## 🚀 Quick Start

### Run Tests
```bash
# From project root - use the launcher
python scripts/run_tests.py

# Or directly from scripts directory
python scripts/testing/run_tests.py
```

### Explore Testing Options
```bash
# See testing scripts documentation
cat scripts/testing/README.md

# List all available testing scripts
ls scripts/testing/
```

## 📋 Available Script Categories

- **🧪 Testing Scripts**: `testing/` - Complete testing framework and utilities
- **🔗 Client Examples**: `client_examples/` - Various MCP client implementations and configurations
- **📊 Test Results**: `test_results/` - Generated test reports and outputs
- **🔧 Future Extensions**: Additional script categories can be added here

## 📚 Related Documentation

- **Testing Framework**: `docs/TESTING_FRAMEWORK.md`
- **Developer Guide**: `docs/developer_guide/DEVELOPER_GUIDE.md`
- **Project README**: `README.md`