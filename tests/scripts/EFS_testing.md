

# EFS Test Script — Teradata Enterprise Feature Store

## Purpose
This script (`efs_mcp_test.py`) demonstrates and tests the Teradata MCP Server's functionality for the **Teradata Enterprise Feature Store** (EFS). 

It runs through the following EFS functions:
1. `fs_isFeatureStorePresent`
2. `fs_setFeatureStoreConfig`
3. `fs_getDataDomains`
4. `fs_getAvailableDatasets`
5. `fs_getAvailableEntities`
6. `fs_getFeatures`
7. `fs_createDataset`

## Actions
- **setup** – Create a demo feature store schema and load example features.  
- **test** – Call the EFS MCP tools above in sequence to verify functionality.  
- **cleanup** – Drop the demo feature store objects.


## Requirements
- Python 3.11+
- Access to a Teradata system
- MCP server exposing `fs_*` tools at `http://127.0.0.1:8001/mcp`
- Python packages: `tdfs4ds`, `teradataml`, `langchain_mcp_adapters`

## Setup
Create and activate a virtual environment, then install the required packages:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Usage

Make sure that you have the Teradata MCP server with EFS tools running on `127.0.0.1:8001/mcp` eg.

```bash
uv run teradata-mcp-server --profile dataScientist --mcp_transport streamable-http --mcp_port 8001
```

Use the test script

```bash
# Setup demo feature store in your schema
python test/EFS/efs_mcp_test.py --action setup --database_uri "teradata://user:pass@host:1025/schema"

# Run the tests
python test/EFS/efs_mcp_test.py --action test

# Clean up: drop the feature store
python test/EFS/efs_mcp_test.py --action cleanup --database_uri "teradata://user:pass@host:1025/schema"
```

## Notes
- Defaults: `database_name = demo_user`, `data_domain = demo_dba`.
- Dataset created in test: `test_dataset`.
- `feature_selection` must be a string (e.g. `"col1,col2"`), not a list.