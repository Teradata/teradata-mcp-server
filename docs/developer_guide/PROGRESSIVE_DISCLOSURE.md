# Progressive Disclosure Implementation

## Overview

We enable progressive disclosure of MCP tools and other assets (to be implemented) to optimize the context window usage. 

This is particularly relevant considering the large number of tools that this server offers by default, and the pace at which new custom tools are created after deployment.

Instead of listing all tools in the `tools/list` response (which consumes significant context window space), tools are dynamically discovered and executed through a catalog system.

```mermaid
%%{init: {'theme':'neutral', 'themeVariables': { 'fontSize':'12px'}, 'flowchart':{'htmlLabels':true, 'curve':'basis', 'nodeSpacing': 30, 'rankSpacing': 30}}}%%
flowchart TD
    A[User Input] --> B[Current Context]
    B --> C[Start Reasoning]
    C --> D{Do I need more<br/>information?}
    D -->|No| G[Answer]
    D -->|Yes| E[Search for<br/>relevant tools]
    E --> F[Execute tool and<br/>add to context]
    F --> B
```    

## Usage

### Enabling Progressive Disclosure

**Via Command Line:**
```bash
teradata-mcp-server --progressive_disclosure
```

**Via Environment Variable:**
```bash
export PROGRESSIVE_DISCLOSURE=true
teradata-mcp-server
```

### Using Progressive Disclosure

#### 1. Search for Tools

The `search_tool` supports two modes based on the query:

**Exact Match** (query = exact tool name):
```python
# Get full documentation for a specific tool
search_tool("base_readQuery")

# Returns:
{
  "match_type": "exact",
  "tool": {
    "name": "base_readQuery",
    "category": "base",
    "description": "Execute a SQL query via SQLAlchemy, bind parameters...",
    "full_documentation": "Execute a SQL query via SQLAlchemy...\n\nArguments:\n  sql - SQL text...",
    "parameters": {
      "sql": {
        "type": "str",
        "required": false,
        "default": "None",
        "description": "SQL text, with optional bind-parameter placeholders"
      }
    }
  }
}
```

**Approximate Match** (query = keywords):
```python
# Search for table-related tools
search_tool("table list")

# Returns:
{
  "match_type": "approximate",
  "results_count": 2,
  "tools": [
    {
      "name": "base_tableList",
      "category": "base",
      "summary": "Lists all tables in a database.",
      "score": 120
    },
    {
      "name": "base_tableDDL",
      "category": "base",
      "summary": "Displays the DDL definition of a table via SQLAlchemy...",
      "score": 100
    }
  ]
}
```

**Key Differences:**
- **Exact match**: Full documentation + all parameters + complete docstring
- **Approximate match**: Short summary (first meaningful line) only

**Workflow:**
1. Use keywords to discover tools: `search_tool("table")`
2. Get full docs for specific tool: `search_tool("base_tableList")`
3. Execute the tool: `execute_tool("base_tableList", {"database_name": "demo"})`

#### 2. Execute a Tool

```python
# Execute a tool with arguments as a dictionary
execute_tool("base_tableList", {"database_name": "demo"})

# Returns: Query results (same format as static mode)
```

#### 3. Direct SQL Queries (Core Tool)

```python
# The base_readQuery tool is always available
base_readQuery({"sql": "SELECT * FROM dbc.tables SAMPLE 5"})
```

## Architecture

### Components

1. **ContextCatalog** ([src/teradata_mcp_server/tools/context_catalog.py](src/teradata_mcp_server/tools/context_catalog.py))
   - MCP-agnostic registry for tool metadata
   - Intelligent search with exact vs approximate matching
   - Argument validation
   - Category organization (base, dba, fs, etc.)

2. **Proxy MCP Tools** (in [src/teradata_mcp_server/app.py](src/teradata_mcp_server/app.py))
   - `search_tool`: Search with smart exact/approximate matching
   - `execute_tool`: Execute a tool by name with arguments
   - `base_readQuery`: Core SQL query tool (always available)

3. **Tool Functions** ([src/teradata_mcp_server/tools/*/](src/teradata_mcp_server/tools/))
   - Pure Python functions (handle_* pattern)
   - No MCP dependencies
   - Reusable across different frameworks

## Search Algorithm

### Exact Match Detection

Case-insensitive comparison with tool name:
- `"base_readQuery"` → Exact match
- `"BASE_READQUERY"` → Exact match
- `"base_readquery"` → Exact match

### Approximate Match Scoring

Weighted scoring system:
- **Exact name match**: +200 points
- **Partial name match**: +100 points
- **Category exact match**: +75 points
- **Category partial match**: +50 points
- **Keyword matches**: +10 points per keyword
- **Description contains query**: +20 points
- **Parameter name match**: +15 points per parameter

Results sorted by score (highest first) and limited by `limit` parameter.

### Short Summary Extraction

For approximate matches, extracts the first meaningful line from docstring:
- Skips empty lines
- Skips section headers (lines ending with `:`)
- Returns first substantial line of text

Example:
```python
"""Execute a SQL query via SQLAlchemy, bind parameters if provided.

Arguments:
  sql - SQL text
"""
# Summary: "Execute a SQL query via SQLAlchemy, bind parameters if provided."
```

## Tool Categories

Tools are automatically categorized by their prefix:

- `base_*`: Core database operations (tables, queries, DDL)
- `dba_*`: Database administration tools
- `fs_*`: Feature Store operations
- `qlty_*`: Data quality tools
- `sec_*`: Security and access management
- `tdvs_*`: Teradata Vector Store operations
- `plot_*`: Data visualization
- `rag_*`: RAG (Retrieval-Augmented Generation) tools
- `sql_opt_*`: SQL optimization tools
- `chat_*`: Chat completion tools
- `bar_*`: Backup and restore tools

## Comparison: Static vs Progressive Disclosure

### Static Mode (Default)

```python
# All tools are registered as individual MCP tools
settings = Settings(progressive_disclosure=False)
mcp, logger = create_mcp_app(settings)

# Client sees:
# - base_readQuery
# - base_tableList
# - base_tableDDL
# - base_columnDescription
# - ... (100+ tools)
```

### Progressive Disclosure Mode

```python
# Tools are registered in catalog, accessed via proxy
settings = Settings(progressive_disclosure=True)
mcp, logger = create_mcp_app(settings)

# Client sees:
# - search_tool (with exact/approximate matching)
# - execute_tool
# - base_readQuery (core tool)
#
# All other tools are in the catalog (100+ tools available)
```

## Testing

### Unit Tests

```bash
# Test catalog functionality
python3 test_progressive_disclosure.py

# Test search modes (exact vs approximate)
python3 test_search_modes.py
```

### Integration Tests

```bash
# Test server startup in both modes
~/.local/bin/uv run python test_server_startup.py
```

### Existing Tests

All existing tests continue to work:

```bash
export DATABASE_URI="teradata://user:pass@host:1025/database"
uv run python tests/run_mcp_tests.py "uv run teradata-mcp-server"
```

## Benefits

### For LLM Clients

- **Reduced context window usage**: 99% reduction in initial tokens
- **Two-tier discovery**: Quick summaries → detailed docs
- **Efficient exploration**: Keywords find relevant tools fast
- **Complete information**: Exact match provides full documentation

### For Server Operators

- **Scalability**: Support 1000+ tools without context bloat
- **Flexibility**: Easy to add/remove tools
- **Monitoring**: Can track which tools are searched/executed
- **Cost reduction**: Lower token usage → lower API costs

### For Developers

- **Clean separation**: MCP logic separate from tool logic
- **Reusability**: Tools work in any framework
- **Maintainability**: Single source of truth for tool metadata
- **Extensibility**: Easy to add new discovery methods

## Implementation Details

### No Code Duplication

Both modes use the same:
- Tool functions (`handle_*`)
- Database execution logic (`execute_db_tool`)
- Signature transformation (`make_tool_wrapper`)
- Connection management (`get_tdconn`)

The only difference is the registration mechanism:
- **Static**: `mcp.tool(name, description)(wrapped_func)`
- **Progressive**: `context_catalog.register_tool(func, category)`

### Separation of Concerns

- **MCP-specific code**: Only in `app.py` (FastMCP decorators, transport)
- **Core logic**: In `context_catalog.py` (no MCP dependencies)
- **Tool functions**: In `tools/*/` (protocol-agnostic)

This allows tools to be reused in:
- Different MCP implementations
- Direct Python scripts
- Other agent frameworks

## Backward Compatibility

- Default behavior unchanged (static mode)
- All existing tools continue to work
- No breaking changes to tool signatures
- Existing tests pass without modification

## Conclusion

Progressive disclosure with intelligent exact/approximate matching provides:

- **Dramatic context window savings** (99% reduction)
- **Smart discovery** (summaries vs full docs)
- **Zero code duplication** (same tools, different registration)
- **Clean architecture** (MCP-agnostic core)
- **Backward compatibility** (opt-in feature)

The two-tier search approach (exact match for details, approximate for exploration) optimizes the LLM experience for both discovery and execution workflows.
