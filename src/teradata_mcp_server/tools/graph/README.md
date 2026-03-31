# Graph Dependency Analysis Tools

**Version:** 1.0  
**Last Updated:** 2025-03-04  
**Purpose:** Teradata object dependency analysis via ODEX framework

This module provides tools for analysing object dependencies in Teradata using graph traversal through the ODEX (Object Dependency Exchange) framework.

## Quick Start

```python
from teradata_mcp_server.tools.graph import graph_queryDependenciesAgent

# Basic impact analysis
result = graph_queryDependenciesAgent(
    conn=connection,
    object_name="DEV01_StGeo_STD_T.mortgage_account",
    max_depth_down=5,
    exclude_objects="PRD_%,OLD_%"  # Exclude production and old databases
)

print(f"Total affected objects: {result['summary']['downstream_nodes']}")
```

## Tools

This module provides two complementary tools for dependency analysis:

1. **`graph_queryDependenciesAgent`** - Comprehensive bidirectional dependency analysis
2. **`graph_findRootObjects`** - Identify starting points for downstream impact analysis

---

### `graph_findRootObjects`

Find root objects (objects with no upstream dependencies) to identify ideal starting points for downstream impact analysis.

#### Description

Identifies objects that have **no upstream dependencies** in the ODEX repository. These "root objects" represent foundational data sources that nothing else depends upon, making them perfect starting points for:
- Downstream impact analysis
- Data pipeline understanding
- Migration planning
- Dependency mapping

#### Use Cases

| Use Case | Description | Configuration |
|----------|-------------|---------------|
| **Find Starting Points** | Identify where to begin impact analysis | `container_pattern="%WBC%,%StGeo%"` |
| **Source Table Discovery** | Find base tables in data pipelines | `object_types="T"` |
| **Foundation Objects** | Identify independent foundational objects | `exclude_objects="PRD_%,%.temp_%"` |
| **Migration Planning** | Prioritise objects by downstream impact | `return_format="detailed"` |
| **Quick Count** | Fast assessment of root object count | `return_format="summary"` |

#### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `container_pattern` | string | - | ✅ | Database/schema pattern(s) (supports % wildcards and CSV)<br>Examples: `%WBC%`, `%WBC%,%StGeo%`, `DEV01_%` |
| `exclude_objects` | string | `''` | ❌ | **SERVER-SIDE filtering** - Comma-separated FQ patterns<br>Examples: `PRD_%`, `%.temp_%,%.bak_%` |
| `edge_repository` | string | `DEV_01_ODEX_STD_0_V.ODEXRepository` | ❌ | ODEX repository to query |
| `object_types` | string | `''` | ❌ | Filter by object type: `T` (tables), `V` (views), `P` (procedures)<br>Examples: `T`, `T,V` |
| `return_format` | string | `detailed` | ❌ | Output format: `detailed` (full list) or `summary` (statistics only) |

#### Example Queries

**Natural Language (Triggers)**

```
"Which objects in WBC and StGeo databases should I start analysing?"
"Find root objects in DEV01 databases"
"What are the starting points for impact analysis?"
"Show me base tables with no dependencies"
```

**Python Code Examples**

```python
# Find all root objects in WBC and StGeo databases
result = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="%WBC%,%StGeo%"
)

print(f"Found {len(result['results']['root_objects'])} root objects")
for obj in result['results']['summary']['top_impact_objects']:
    print(f"  {obj['name']} → {obj['downstream_count']} dependents")

# Find only root tables (no views/procedures)
result = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="DEV01_%",
    object_types="T",
    exclude_objects="PRD_%,%.temp_%"
)

# Quick summary
result = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="%StGeo%",
    return_format="summary"
)
print(result['results']['summary_text'])
```

#### Return Format

**Detailed** (default):
```json
{
  "results": {
    "root_objects": [
      {
        "DatabaseName": "DEV01_StGeo_STD_T",
        "ObjectName": "mortgage_account",
        "FullyQualifiedName": "DEV01_StGeo_STD_T.mortgage_account",
        "ObjectType": "T",
        "DownstreamDependentCount": 15
      }
    ],
    "summary": {
      "total_root_objects": 42,
      "object_type_counts": {"T": 35, "V": 7},
      "top_impact_objects": [...]
    }
  }
}
```

**Summary**:
```json
{
  "results": {
    "summary_text": "ROOT OBJECTS ANALYSIS SUMMARY\n...",
    "statistics": {...},
    "root_object_names": [...]
  }
}
```

---

### `graph_queryDependenciesAgent`

The primary tool for comprehensive dependency analysis using recursive graph traversal.

#### Description

Analyse object dependencies by traversing upstream (what the object depends on) and downstream (what depends on the object) relationships using the `QueryDependenciesAgent` stored procedure from the ODEX framework.

Returns nodes (unique objects) and edges (relationships) representing the complete dependency graph.

#### Use Cases

| Use Case | Description | Configuration |
|----------|-------------|---------------|
| **Impact Analysis** | What breaks if I change/drop this object? | `max_depth_up=0, max_depth_down=5` |
| **Data Lineage** | Where does this data come from? | `max_depth_up=10, max_depth_down=0` |
| **Pre-deployment Validation** | Check impacts before deployment | `max_depth_up=3, max_depth_down=5` |
| **Documentation** | Understanding object relationships | `return_format="detailed"` |
| **Quick Impact Check** | Fast assessment for approvals | `return_format="summary"` |

#### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `object_name` | string | - | ✅ | Fully qualified object name (supports % wildcards)<br>Examples: `DEV01_StGeo_STD_T.mortgage_account`, `DBC.TablesV`, `%.mortgage_%` |
| `max_depth_up` | integer | 3 | ❌ | Upstream traversal depth (0-10)<br>0=none, 1=direct only, 3=standard, 10=complete |
| `max_depth_down` | integer | 3 | ❌ | Downstream traversal depth (0-10)<br>0=none, 1=direct only, 3=standard, 10=complete |
| `exclude_objects` | string | `''` | ❌ | **SERVER-SIDE filtering** - Comma-separated FQ patterns<br>See [Exclusion Patterns](#exclusion-patterns) below |
| `include_containers` | string | `''` | ❌ | Whitelist of schemas/databases (empty = all)<br>Example: `DEV01_%,DEV02_%` |
| `edge_repository` | string | `DEV_01_ODEX_STD_0_V.ODEXRepository` | ❌ | ODEX repository to query |
| `return_format` | string | `detailed` | ❌ | Output format: `detailed`, `summary`, or `edges_only` |

#### Exclusion Patterns

The `exclude_objects` parameter supports **server-side filtering** using SQL LIKE patterns matching against fully qualified names (`DatabaseName.ObjectName`).

**🔥 Critical Discovery:** This is significantly more efficient than client-side filtering and can reduce result sets by 20-50%.

##### Database-Level Exclusions (Most Common)

Exclude entire database families by matching the database prefix:

```python
# Single database family
exclude_objects="PRD_%"              # All objects in databases starting with PRD_

# Multiple database families
exclude_objects="PRD_%,TST_%,UAT_%"  # Production, test, and UAT

# Specific database
exclude_objects="PROD_DB.%"          # All objects in PROD_DB only
```

##### Object-Level Exclusions

Exclude objects by name pattern across all databases:

```python
# Temporary objects
exclude_objects="%.temp_%"           # All objects with 'temp_' prefix

# Backup objects
exclude_objects="%.bak_%,%.backup_%"  # Backup and archive objects

# System objects
exclude_objects="%._sys_%,%.#%"      # System and temporary objects
```

##### Common Patterns

```python
# Production safety (most common)
PRODUCTION_SAFE = "PRD_%,PROD_%"

# Multi-environment focus (dev only)
DEV_ONLY = "PRD_%,TST_%,UAT_%,STG_%,SBX_%"

# Deprecated/legacy cleanup
NO_LEGACY = "OLD_%,ARCHIVE_%,DEPRECATED_%,LEGACY_%"

# Exclude personal/sandbox schemas
NO_PERSONAL = "DFJ%,C_D02%,SANDBOX_%"

# Regulatory compliance (exclude sensitive)
NO_SENSITIVE = "COMPLIANCE_%,REG_%,AUDIT_%,PII_%"
```

##### Real-World Example

```python
# Scenario: Analyse DBC.TablesV but exclude production, 
# test schemas, and deprecated databases

result = graph_queryDependenciesAgent(
    object_name="DBC.TablesV",
    max_depth_down=10,
    exclude_objects="PRD_%,DFJ%,C_D02%,TST_%,OLD_%"
)

# Result: Reduced from 71 edges to 52 edges
# Performance improvement: 27% reduction in result size
```

#### Return Formats

##### `detailed` (Default)

Complete information for visualisation and analysis:

```json
{
  "results": {
    "nodes": [...],              // All unique objects
    "upstream_edges": [...],     // Dependencies this object relies on
    "downstream_edges": [...],   // Objects that depend on this
    "summary": {                 // Aggregate statistics
      "total_nodes": 25,
      "upstream_nodes": 8,
      "downstream_nodes": 17
    }
  },
  "metadata": {...}              // Execution details
}
```

**Best for:** Visualisation (D3.js, Cytoscape), debugging, comprehensive analysis

##### `summary`

High-level statistics only:

```json
{
  "results": {
    "summary_text": "...",       // Formatted text report
    "statistics": {...},          // Aggregate counts
    "upstream_objects": [...],    // List of FQ names (upstream)
    "downstream_objects": [...]   // List of FQ names (downstream)
  }
}
```

**Best for:** Quick impact checks, executive reporting, change approvals

##### `edges_only`

Raw edge data without node details:

```json
{
  "results": {
    "upstream_edges": [...],     // Raw upstream relationships
    "downstream_edges": [...]    // Raw downstream relationships
  }
}
```

**Best for:** Graph construction, minimising data transfer, Neo4j import

#### Example Queries

##### Natural Language (Triggers)

```
"Show me dependencies for DEV02_WBC_STD_P.SP_POPULATE_WITH_COUNTS"
"What breaks if I drop vw_borrower_risk_assessment?"
"Find upstream dependencies for MyTable, 5 levels deep"
"Impact analysis for Schema.MyView excluding test objects"
```

##### Python Code Examples

**1. Basic Downstream Impact Analysis**

```python
# Find what breaks if I modify this table
result = graph_queryDependenciesAgent(
    conn=connection,
    object_name="DEV01_StGeo_STD_T.mortgage_account",
    max_depth_up=0,      # No upstream
    max_depth_down=5,    # 5 levels downstream
    exclude_objects="PRD_%,OLD_%"  # Safety filters
)

impact = result['results']['summary']['downstream_nodes']
print(f"Modifying this table affects {impact} downstream objects")
```

**2. Data Lineage Tracing**

```python
# Trace where report data comes from
result = graph_queryDependenciesAgent(
    conn=connection,
    object_name="DEV01_StGeo_RPT_V.mortgage_risk_analysis",
    max_depth_up=10,     # Complete upstream trace
    max_depth_down=0     # No downstream needed
)

sources = result['results']['upstream_objects']
print(f"Report sources: {sources}")
```

**3. Complete Bidirectional Analysis**

```python
# Full ecosystem understanding
result = graph_queryDependenciesAgent(
    conn=connection,
    object_name="DEV02_WBC_STD_T.Mortgage",
    max_depth_up=5,
    max_depth_down=5,
    exclude_objects="PRD_%,DFJ%,C_D02%"
)
```

**4. Quick Summary Check**

```python
# Fast impact check for change approval
result = graph_queryDependenciesAgent(
    conn=connection,
    object_name="DEV_01_ODEX_STD_0_P.CheckSQLValidity",
    max_depth_down=3,
    return_format="summary"  # Text summary only
)

print(result['results']['summary_text'])
```

**5. Project-Scoped Analysis**

```python
# Focus on specific project databases only
result = graph_queryDependenciesAgent(
    conn=connection,
    object_name="DEV01_StGeo_STD_T.mortgage_account",
    max_depth_down=10,
    include_containers="DEV01_StGeo_%,DEV02_WBC_%",
    exclude_objects="%.temp_%,%.bak_%"
)
```

## Performance Guide

### Query Time Expectations

| Depth | Typical Time | Notes |
|-------|--------------|-------|
| 1-3 | 2-10 seconds | Standard analysis |
| 5 | 10-20 seconds | Deep analysis |
| 10 | 30-60+ seconds | Complete lineage |

### Result Size Expectations

| Depth | Typical Nodes | Typical Edges |
|-------|--------------|---------------|
| 1 | 10-50 | 15-75 |
| 3 | 50-200 | 75-400 |
| 10 | 500-1000+ | 1000-2000+ |

### Optimisation Strategies

1. **Use `exclude_objects` aggressively**
   - Server-side filtering is 10-100x faster than client-side
   - Can reduce results by 20-50%
   - Example: `exclude_objects="PRD_%,OLD_%,%.temp_%"`

2. **Start with lower depths**
   - Test with `max_depth=1` first to estimate size
   - Incrementally increase as needed
   - Use `max_depth=3` as standard default

3. **Leverage `include_containers`**
   - Whitelist specific databases to limit scope
   - Reduces search space significantly
   - Example: `include_containers="PROJECT_%"`

4. **Choose appropriate `return_format`**
   - Use `summary` for quick checks (smallest transfer)
   - Use `edges_only` when nodes can be derived client-side
   - Use `detailed` only when needed

5. **Cache frequently accessed results**
   - Store dependency graphs for common objects
   - Refresh periodically (daily/weekly)
   - Reduces database load

### Performance Targets

| Metric | Target | Action if Exceeded |
|--------|--------|-------------------|
| Query Time | < 10s | Reduce depth or add exclusions |
| Result Nodes | < 500 | Add `exclude_objects` patterns |
| Result Edges | < 1000 | Reduce `max_depth` or scope with `include_containers` |

## Dependencies

### Required Teradata Objects

- **Stored Procedure**: `DEV_01_ODEX_RPT_0_P.QueryDependenciesAgent`
- **Edge Repository**: `DEV_01_ODEX_STD_0_V.ODEXRepository` (default)
  - Should have indexes on `Src_Container_Name` and `Tgt_Container_Name`
  - Requires regular updates for accuracy

### Python Packages

- `teradatasql` (included in base MCP server)
- Standard library: `logging`

### Permissions Required

- `SELECT` on edge repository table
- `CREATE VOLATILE TABLE` permission (for procedure execution)
- `EXECUTE` permission on `DEV_01_ODEX_RPT_0_P.QueryDependenciesAgent`

## Installation

### File Structure

```
src/teradata_mcp_server/tools/graph/
├── __init__.py
├── graph_tools.py           # Main implementation
└── README.md                # This file
```

### Configuration

Add to your `profiles.yml`:

```yaml
graph:
  allmodule: True
  tool:
    graph_queryDependenciesAgent: True
```

## Best Practices

1. **Always Start Conservative**
   - Begin with `max_depth=1` or `max_depth=3`
   - Incrementally increase only if needed
   - Test query complexity before production use

2. **Filter Aggressively**
   - Use `exclude_objects` liberally
   - Document standard exclusion patterns for team
   - Example team standard: `"PRD_%,OLD_%,%.temp_%"`

3. **Validate Repository Currency**
   - Check ODEX repository update timestamp before critical decisions
   - Request refresh if stale (> 1 week old)

4. **Cache Results**
   - Store frequently accessed dependency graphs
   - Implement cache invalidation strategy
   - Refresh on schema changes

5. **Choose Right Format**
   - `detailed` → Visualisation, documentation
   - `summary` → Quick checks, approvals
   - `edges_only` → Graph databases, network analysis

6. **Document Exclusions**
   - Maintain team-wide exclusion pattern library
   - Version control exclusion configurations
   - Review and update quarterly

## Integration Patterns

### Workflow: Root Objects → Downstream Impact Analysis

```python
# Step 1: Find root objects (starting points)
root_result = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="%WBC%,%StGeo%",
    object_types="T",  # Tables only
    exclude_objects="PRD_%,%.temp_%"
)

# Step 2: Prioritise by downstream impact
high_impact_roots = [
    obj for obj in root_result['results']['root_objects']
    if obj['DownstreamDependentCount'] > 10
]

# Step 3: Analyse downstream impact for each high-impact root
for root_obj in high_impact_roots:
    print(f"\n=== Analysing: {root_obj['FullyQualifiedName']} ===")
    print(f"Downstream dependents: {root_obj['DownstreamDependentCount']}")
    
    impact_result = handle_graph_queryDependenciesAgent(
        conn=connection,
        object_name=root_obj['FullyQualifiedName'],
        max_depth_up=0,      # No upstream (it's a root!)
        max_depth_down=5,    # Deep downstream analysis
        exclude_objects="PRD_%"
    )
    
    print(f"Total impact: {impact_result['results']['summary']['downstream_nodes']} objects")
    print(f"Max depth reached: {impact_result['results']['summary']['max_depth_downstream']}")
```

### With D3.js/Cytoscape Visualisation

```python
result = graph_queryDependenciesAgent(
    conn=connection,
    object_name="DEV01_StGeo_STD_T.mortgage_account",
    max_depth_up=5,
    max_depth_down=5,
    return_format="detailed"
)

nodes = result['results']['nodes']
edges = result['results']['upstream_edges'] + result['results']['downstream_edges']

# Feed to D3.js force-directed graph
create_visualisation(nodes, edges)
```

### With Change Management Systems

```python
# Assess blast radius
result = graph_queryDependenciesAgent(
    conn=connection,
    object_name="DEV01_StGeo_STD_T.mortgage_account",
    max_depth_up=0,
    max_depth_down=5,
    return_format="summary"
)

impact_count = result['results']['statistics']['downstream_nodes']

# Auto-classify change severity
if impact_count > 20:
    create_change_ticket(severity="HIGH", testing_required=True)
elif impact_count > 5:
    create_change_ticket(severity="MEDIUM", testing_required=True)
else:
    create_change_ticket(severity="LOW", testing_required=False)
```

### With Data Lineage Documentation

```python
# Trace upstream to source systems
result = graph_queryDependenciesAgent(
    conn=connection,
    object_name="DEV01_StGeo_RPT_V.mortgage_risk_analysis",
    max_depth_up=10,
    max_depth_down=0
)

# Generate lineage documentation
generate_lineage_doc(
    report_name="mortgage_risk_analysis",
    source_tables=extract_tables(result, direction='upstream'),
    transformation_layers=extract_views(result)
)
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| **Query Timeout** | Depth too high or large graph | Reduce `max_depth` or add `exclude_objects` |
| **Empty Results** | Object doesn't exist or all filtered | Verify object name, check exclusions |
| **Incomplete Results** | Stale ODEX repository | Request repository refresh |
| **Performance Degradation** | Missing indexes on repository | Add indexes on `Src_Container_Name`, `Tgt_Container_Name` |

### Debug Steps

1. **Verify object exists**
   ```python
   base_tableList(database_name="DEV01_StGeo_STD_T")
   ```

2. **Test with minimal query**
   ```python
   result = graph_queryDependenciesAgent(
       object_name="...",
       max_depth_down=1,
       return_format="summary"
   )
   ```

3. **Check repository status**
   ```python
   base_readQuery(sql="""
       SELECT MAX(LastUpdated) as LastRefresh
       FROM DEV_01_ODEX_STD_0_V.ODEXRepository
   """)
   ```

## Future Enhancements

Planned tools for this module:

- ~~`graph_findRootObjects`~~ - ✅ **IMPLEMENTED** (v1.1) - Find root objects with no upstream dependencies
- `graph_detectCircularDependencies` - Find circular reference loops
- `graph_findOrphanedObjects` - Find objects with no dependencies (neither upstream nor downstream)
- `graph_calculateMetrics` - Graph metrics (centrality, clustering coefficient)
- `graph_suggestRefactoring` - Identify refactoring opportunities based on graph structure

## Support

### Documentation

- [graph_queryDependenciesAgent Complete Documentation](./graph_queryDependenciesAgent_complete_documentation.md)
- [graph_findRootObjects Complete Documentation](./graph_findRootObjects_complete_documentation.md)
- [Fully Commented Source Code](./graph_tools.py)

### Contact

For issues or questions:
- Check ODEX repository status first
- Review exclusion patterns
- Consult team documentation for standard configurations
- Contact database administration team for repository updates

---

**Version History**

- **1.1** (2025-03-05): Added `graph_findRootObjects` tool
  - Find objects with no upstream dependencies (root objects)
  - Identify starting points for downstream impact analysis
  - CSV pattern support for multiple container searches
  - Server-side filtering via `exclude_objects` parameter
  - Object type filtering (tables, views, procedures, macros)
  - Two return formats: detailed (full list) and summary (statistics)
  - Automatically sorts by downstream dependent count
  - Comprehensive documentation and examples

- **1.0** (2025-03-04): Initial release with `graph_queryDependenciesAgent` tool
  - Server-side filtering via `exclude_objects` parameter
  - Three return formats: detailed, summary, edges_only
  - Comprehensive documentation and examples
