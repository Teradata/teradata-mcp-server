# Graph Dependency Analysis Tools

**Version:** 2.0  
**Last Updated:** 2026-03-31  
**Purpose:** Teradata object dependency analysis via ODEX framework

This module provides tools for analysing object dependencies in Teradata using graph traversal through the ODEX (Object Dependency Exchange) framework.

## Quick Start

```python
# Step 1 — Find root objects (seed points for analysis)
roots = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="%WBC%,%StGeo%",
    object_types="Table"
)

# Step 2 — Compute BFS hop distances and group into migration waves
waves = handle_graph_bfsLevelsPy(
    conn=connection,
    root_node_list="DEV02_WBC_RPT_T.mortgage_portfolio_summary,"
                   "DEV01_StGeo_RPT_T.monthly_portfolio_risk_summary",
    include_containers="DEV01_StGeo%,DEV02_WBC%,POWERBI%,TABLEAU%"
)

# Objects grouped by nearest_root = migration wave grouping
# Objects ordered by downstream_level = deployment sequence within each wave
```

---

## Tools

This module provides five complementary tools for dependency analysis:

| # | Tool | Type | Purpose |
|---|------|------|---------|
| 1 | [`graph_findRootObjects`](#graph_findrootobjects) | SQL | Discover objects with no upstream dependencies — migration seed points |
| 2 | [`graph_bfsLevels`](#graph_bfslevels) | Python BFS | Wave planning, blast-radius sizing, deployment sequencing |
| 3 | [`graph_queryDependenciesAgent`](#graph_querydependenciesagent) | SP | Full lineage tracing, impact path analysis, edge detail |
| 4 | [`graph_detectCycles`](#graph_detectcycles) | SP | Circular reference detection, DAG validation |
| 5 | [`graph_connectedComponents`](#graph_connectedcomponents) | SP | Graph partitioning, isolated sub-graph identification |

**Typical workflow:** `findRootObjects` → `bfsLevels` → `queryDependenciesAgent` → `detectCycles`

---

## Package Structure

```
teradata_mcp_server/tools/
├── graph_tools.py                     # Registration hub (imports + GRAPH_TOOLS list only)
├── graph/
│   ├── __init__.py
│   ├── _graph_utils.py                # Shared BFS helpers (internal)
│   ├── graph_findRootObjects.py       # Tool: SQL-based root object discovery
│   ├── graph_bfsLevelsPy.py          # Tool: Python BFS (no SP dependency)
│   ├── graph_queryDependenciesAgent.py # Tool: SP-based lineage analysis
│   ├── graph_detectCycles.py          # Tool: SP-based cycle detection
│   └── graph_connectedComponents.py   # Tool: SP-based WCC analysis
└── utils.py                           # Shared MCP utilities
```

`graph_tools.py` is intentionally thin — it contains no logic, only imports and the `GRAPH_TOOLS` registration list. See the comments in that file for the rationale.

---

## Tool Reference

### `graph_findRootObjects`

Find objects with no upstream dependencies in specified containers.

#### Description

Root objects are foundational data sources that nothing else feeds into. They are the natural starting points for downstream impact analysis and migration wave planning — use `graph_bfsLevels` after this tool to compute hop distances from the identified roots.

#### Use Cases

| Use Case | Description | Configuration |
|----------|-------------|---------------|
| **Migration seed discovery** | Find root tables to anchor migration waves | `container_pattern="%WBC%,%StGeo%"` |
| **Source table discovery** | Find base tables in data pipelines | `object_types="Table"` |
| **Foundation objects** | Identify independent foundational objects | `exclude_objects="PRD_%,%.temp_%"` |
| **Migration planning** | Prioritise by downstream impact count | `return_format="detailed"` |
| **Quick count** | Fast assessment of root object count | `return_format="summary"` |

#### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `container_pattern` | string | — | ✅ | Database/schema pattern(s). Supports `%` wildcards and CSV.<br>Examples: `%WBC%`, `%WBC%,%StGeo%`, `DEV01_%` |
| `exclude_objects` | string | `''` | ❌ | SQL LIKE patterns to exclude. Matches `DatabaseName.ObjectName`.<br>Examples: `PRD_%`, `%.temp_%,%.bak_%` |
| `edge_repository` | string | `DEV_01_ODEX_STD_0_V.ODEXRepository` | ❌ | ODEX repository view to query |
| `object_types` | string | `''` | ❌ | Filter by object type: `Table`, `View`, `Procedure`, `Macro`.<br>CSV supported: `Table,View`. Empty = all types. |
| `return_format` | string | `detailed` | ❌ | `detailed` (full list with metadata) or `summary` (statistics only) |

#### Example Calls

```python
# Find all root objects in WBC and StGeo databases
result = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="%WBC%,%StGeo%"
)
for obj in result['results']['summary']['top_impact_objects']:
    print(f"  {obj['name']} → {obj['downstream_count']} dependents")

# Find only root tables excluding personal schemas
result = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="DEV01_%,DEV02_%",
    object_types="Table",
    exclude_objects="DFJ%,C_D02%,PRD_%"
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
        "DatabaseName": "DEV01_StGeo_RPT_T",
        "ObjectName": "monthly_portfolio_risk_summary",
        "FullyQualifiedName": "DEV01_StGeo_RPT_T.monthly_portfolio_risk_summary",
        "ObjectType": "Table",
        "DownstreamDependentCount": 8
      }
    ],
    "summary": {
      "total_root_objects": 32,
      "object_type_counts": {"Table": 32},
      "database_counts": {"DEV02_WBC_RPT_T": 3, "DEV01_StGeo_RPT_T": 5},
      "top_impact_objects": [...]
    }
  }
}
```

---

### `graph_bfsLevels`

Compute BFS shortest-path hop distances from one or more root nodes.

**Implementation:** Pure Python — no stored procedure required. One SQL round-trip fetches the edge set; all BFS computation runs in the MCP server process.

#### Description

Returns one row per reachable node with signed hop distances and a wave grouping. Purpose-built for migration wave planning, deployment sequencing, and blast-radius sizing.

**This is the right tool for:** sequencing, wave grouping, blast-radius counts, cycle depth analysis.  
**This is not the right tool for:** lineage tracing, impact path detail, edge-level analysis — use `graph_queryDependenciesAgent` for those.

#### Direction Convention

ODEX edge semantics: `Src` "referenced by" `Tgt` → Src is the dependency (upstream); Tgt is the dependent (downstream).

| Direction | Traversal | Meaning |
|-----------|-----------|---------|
| Upstream BFS | Reverse adjacency (Tgt → Src) | Discovers what a node depends on |
| Downstream BFS | Forward adjacency (Src → Tgt) | Discovers what depends on a node |

Root objects with in-degree zero correctly show `upstream_level=None` for all non-root nodes — they have no upstream sources. This is the correct behaviour, confirmed by the Option B direction fix applied during development.

#### Use Cases

| Use Case | Description | Configuration |
|----------|-------------|---------------|
| **Migration wave planning** | Group objects by nearest root | All roots in `root_node_list` |
| **Deployment sequencing** | Order by `downstream_level` ascending | `max_depth_up=0, max_depth_down=10` |
| **Blast-radius sizing** | Count objects within N hops | `max_depth_down=N` |
| **Cycle member depth** | Find `direction='BOTH'` nodes | Both directions enabled |
| **Scoped analysis** | Limit to project containers | `include_containers="DEV01_%,TABLEAU%"` |

#### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `root_node_list` | string | — | ✅ | CSV of exact FQ root node names. **No wildcards.** Use `graph_findRootObjects` to discover names. |
| `max_depth_up` | integer | `10` | ❌ | Maximum upstream hops. `0` = skip upstream entirely. |
| `max_depth_down` | integer | `10` | ❌ | Maximum downstream hops. `0` = skip downstream entirely. |
| `exclude_objects` | string | `''` | ❌ | CSV of FQ LIKE patterns to exclude. Matched against both Src and Tgt. Applied in Python. |
| `include_containers` | string | `''` | ❌ | CSV of container LIKE patterns. Both endpoints must match. Applied in SQL for efficiency. |
| `edge_repository` | string | `DEV_01_ODEX_STD_0_V.ODEXRepository` | ❌ | ODEX repository view containing edges. |

#### Example Calls

```python
# Multi-root migration wave planning
waves = handle_graph_bfsLevelsPy(
    conn=connection,
    root_node_list=(
        "DEV02_WBC_RPT_T.mortgage_portfolio_summary,"
        "DEV01_StGeo_RPT_T.monthly_portfolio_risk_summary,"
        "DFJ_DATA.dfj_reltnshps"
    ),
    include_containers="DEV01_StGeo%,DEV02_WBC%,DFJ%,POWERBI%,TABLEAU%"
)
# nearest_root → wave grouping
# downstream_level → deployment order within each wave

# Downstream consumers only (deployment sequencing)
result = handle_graph_bfsLevelsPy(
    conn=connection,
    root_node_list="DEV02_WBC_STD_T.Borrower",
    max_depth_up=0,
    max_depth_down=10
)

# With exclusions
result = handle_graph_bfsLevelsPy(
    conn=connection,
    root_node_list="DEV01_StGeo_RPT_T.mortgage_products_summary",
    exclude_objects="DFJ%,C_D02%,%.temp_%",
    include_containers="DEV01_StGeo%,TABLEAU%"
)
```

#### Return Format

```json
{
  "results": {
    "nodes": [
      {
        "node":             "DEV02_WBC_RPT_T.mortgage_portfolio_summary",
        "container_name":   "DEV02_WBC_RPT_T",
        "object_name":      "mortgage_portfolio_summary",
        "object_kind":      "Table",
        "upstream_level":   null,
        "downstream_level": 0,
        "nearest_root":     "DEV02_WBC_RPT_T.mortgage_portfolio_summary",
        "direction":        "ROOT",
        "is_root":          "Y"
      },
      {
        "node":             "DEV02_WBC_RPT_V.mortgage_portfolio_summary",
        "container_name":   "DEV02_WBC_RPT_V",
        "object_name":      "mortgage_portfolio_summary",
        "object_kind":      "View",
        "upstream_level":   null,
        "downstream_level": 1,
        "nearest_root":     "DEV02_WBC_RPT_T.mortgage_portfolio_summary",
        "direction":        "D",
        "is_root":          "N"
      }
    ],
    "cycle_candidates": [],
    "summary": {
      "total_nodes":            68,
      "root_nodes":             10,
      "upstream_only":          0,
      "downstream_only":        58,
      "both_directions":        0,
      "cycle_candidates":       0,
      "max_upstream_depth":     0,
      "max_downstream_depth":   5,
      "nodes_per_nearest_root": {
        "DEV02_WBC_RPT_T.mortgage_portfolio_summary": 9
      },
      "object_kind_counts": {"Table": 12, "View": 22, "Procedure": 16}
    }
  },
  "metadata": {
    "implementation": "python_bfs",
    "graph_stats": {
      "unique_nodes_in_graph": 120,
      "raw_edges_fetched": 95,
      "edges_excluded": 3,
      "edges_traversed": 92
    }
  }
}
```

#### `direction` Values

| Value | Meaning | `upstream_level` | `downstream_level` |
|-------|---------|-----------------|-------------------|
| `ROOT` | One of the input root nodes | `0` | `0` |
| `U` | Reachable upstream only | Negative integer | `None` |
| `D` | Reachable downstream only | `None` | Positive integer |
| `BOTH` | Reachable both ways — possible cycle member | Negative integer | Positive integer |

`BOTH` nodes where `abs(upstream_level) ≠ downstream_level` are cycle candidates — the asymmetry indicates a back-edge. Equal absolute levels indicate a shared dependency.

---

### `graph_queryDependenciesAgent`

Comprehensive bidirectional dependency analysis with full edge detail.

#### Description

Traverses upstream (what the object depends on) and downstream (what depends on the object) relationships using the `QueryDependenciesAgentBatch` stored procedure. Returns nodes and edges representing the complete dependency graph.

**Use this for:** lineage tracing, impact path detail, visualisation data, edge-level relationship analysis.  
**Not for:** deployment sequencing or wave grouping — use `graph_bfsLevels` for those.

#### Use Cases

| Use Case | Description | Configuration |
|----------|-------------|---------------|
| **Impact analysis** | What breaks if I change/drop this object? | `max_depth_up=0, max_depth_down=5` |
| **Data lineage** | Where does this data come from? | `max_depth_up=10, max_depth_down=0` |
| **Pre-deployment validation** | Check impacts before deployment | `max_depth_up=3, max_depth_down=5` |
| **Visualisation** | Feed D3.js or Cytoscape graph | `return_format="detailed"` |
| **Quick impact check** | Fast assessment for approvals | `return_format="summary"` |

#### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `object_name` | string | — | ✅ | FQ object name(s). Supports `%` wildcards and CSV.<br>Examples: `DB.Table`, `%WBC%.%`, `%WBC%.%,%StGeo%.%` |
| `max_depth_up` | integer | `3` | ❌ | Upstream traversal depth (0–10). |
| `max_depth_down` | integer | `3` | ❌ | Downstream traversal depth (0–10). |
| `exclude_objects` | string | `''` | ❌ | Server-side SQL LIKE patterns for exclusion. |
| `include_containers` | string | `''` | ❌ | Container whitelist (empty = all). |
| `edge_repository` | string | `DEV_01_ODEX_STD_0_V.ODEXRepository` | ❌ | ODEX repository view. |
| `return_format` | string | `detailed` | ❌ | `detailed`, `summary`, or `edges_only`. |

#### Exclusion Patterns

The `exclude_objects` parameter uses server-side SQL LIKE filtering against `DatabaseName.ObjectName` — significantly more efficient than client-side filtering.

```python
# Common patterns
exclude_objects="PRD_%,PROD_%"              # Production safety
exclude_objects="PRD_%,TST_%,UAT_%,STG_%"  # Dev-only focus
exclude_objects="DFJ%,C_D02%,SANDBOX_%"    # Personal/sandbox exclusion
exclude_objects="%.temp_%,%.bak_%"          # Temporary and backup objects
```

#### Example Calls

```python
# Downstream impact analysis
result = handle_graph_queryDependenciesAgent(
    conn=connection,
    object_name="DEV01_StGeo_STD_T.mortgage_account",
    max_depth_up=0,
    max_depth_down=5,
    exclude_objects="PRD_%,OLD_%"
)
impact = result['results']['summary']['downstream_nodes']
print(f"Modifying this table affects {impact} downstream objects")

# Data lineage tracing
result = handle_graph_queryDependenciesAgent(
    conn=connection,
    object_name="DEV01_StGeo_RPT_V.mortgage_risk_analysis",
    max_depth_up=10,
    max_depth_down=0
)

# Wildcard — all WBC and StGeo objects
result = handle_graph_queryDependenciesAgent(
    conn=connection,
    object_name="%WBC%.%,%StGeo%.%",
    max_depth_up=3,
    max_depth_down=3,
    exclude_objects="DFJ%,PRD_%"
)
```

---

### `graph_detectCycles`

Detect circular references in the ODEX lineage graph.

#### Description

Identifies all directed cycles using WCC partitioning and a single-pass `WITH RECURSIVE` CTE. Returns each cycle as an ordered node list with a human-readable path string. Use this to validate graph integrity (DAG property) before migration or deployment.

#### Use Cases

- Validate graph integrity before deployment sequencing
- Find "stub-then-replace" code patterns
- Identify objects causing topological sort failures
- Pre-deployment cycle checks

#### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `container_pattern` | string | — | ✅ | CSV LIKE patterns for container scope. |
| `excl_patterns` | string | `''` | ❌ | CSV LIKE patterns to exclude. |
| `object_dependency_table` | string | `DEV_01_ODEX_STD_0_V.ODEXRepository` | ❌ | ODEX repository view. |
| `strategy` | string | `AUTO` | ❌ | `AUTO` (default, WCC-partitioned CTE), `CTE` (small graphs), `DFS` (debugging). |
| `max_edges_for_cte` | integer | `0` | ❌ | Strategy selection hint. `0` = let SP decide. |

#### Example Calls

```python
# Check for cycles across WBC and StGeo
result = handle_graph_detectCycles(
    conn=connection,
    container_pattern="%WBC%,%StGeo%",
    excl_patterns="DFJ%,C_D02%"
)

cycle_count = result['results']['summary_stats'][0]['Cycle_Count']
print(f"Cycles found: {cycle_count}")

if cycle_count > 0:
    for cycle in result['results']['cycle_summaries']:
        print(f"  Cycle: {cycle['Cycle_Path']}")
```

#### Return Format

```json
{
  "results": {
    "cycle_details":   [...],  // One row per node per cycle
    "cycle_summaries": [...],  // One row per cycle with path string
    "summary_stats":   [...]   // Single row: Cycle_Count, Edge_Count, Strategy_Used
  }
}
```

---

### `graph_connectedComponents`

Identify all Weakly Connected Components (WCC) in the ODEX graph.

#### Description

Partitions the graph into isolated sub-graphs (components) where every node can reach every other node when edge direction is ignored. Use this to understand graph structure, scope impact analysis to a single component, or pre-filter before cycle detection.

#### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `container_pattern` | string | — | ✅ | CSV LIKE patterns for container scope. |
| `excl_patterns` | string | `''` | ❌ | CSV LIKE patterns to exclude. |
| `object_dependency_table` | string | `DEV_01_ODEX_STD_0_V.ODEXRepository` | ❌ | ODEX repository view. |

#### Example Calls

```python
# Partition the StGeo graph into components
result = handle_graph_connectedComponents(
    conn=connection,
    container_pattern="%StGeo%",
    excl_patterns="PRD_%"
)

stats = result['results']['summary_stats'][0]
print(f"Components: {stats['Component_Count']}")
print(f"Nodes: {stats['Node_Count']}, Edges: {stats['Edge_Count']}")
```

---

## Integration Patterns

### Workflow: Migration Wave Planning

```python
# Step 1 — Find root objects (seed points)
roots = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="%WBC%,%StGeo%,%DFJ%",
    object_types="Table",
    exclude_objects="PRD_%,C_D02%"
)

# Step 2 — Take top 10 by downstream count
top_roots = roots['results']['summary']['top_impact_objects'][:10]
root_fq_list = ",".join(obj['name'] for obj in top_roots)

# Step 3 — BFS to compute wave groupings and deployment sequence
waves = handle_graph_bfsLevelsPy(
    conn=connection,
    root_node_list=root_fq_list,
    max_depth_up=0,      # Root objects have no upstream
    max_depth_down=10,
    include_containers="%WBC%,%StGeo%,%DFJ%,POWERBI%,TABLEAU%",
    exclude_objects="PRD_%,C_D02%"
)

# Group by nearest_root → one migration wave per root
# Sort by downstream_level → deployment order within each wave
nodes = waves['results']['nodes']
for node in sorted(nodes, key=lambda n: (n['nearest_root'], n['downstream_level'] or 0)):
    print(f"  Wave: {node['nearest_root']} | Level: {node['downstream_level']} | {node['node']}")
```

### Workflow: Pre-deployment Validation

```python
# Check for cycles before running topological sort
cycles = handle_graph_detectCycles(
    conn=connection,
    container_pattern="%WBC%,%StGeo%"
)

if cycles['results']['summary_stats'][0]['Cycle_Count'] > 0:
    raise ValueError(f"Cannot deploy — circular references detected")

# Safe to proceed with wave planning
waves = handle_graph_bfsLevelsPy(
    conn=connection,
    root_node_list="DEV02_WBC_STD_T.Borrower,DEV02_WBC_STD_T.Collateral"
)
```

### Workflow: Change Impact Assessment

```python
# Assess blast radius before raising a change ticket
result = handle_graph_queryDependenciesAgent(
    conn=connection,
    object_name="DEV01_StGeo_STD_T.mortgage_account",
    max_depth_up=0,
    max_depth_down=5,
    return_format="summary"
)

impact_count = result['results']['statistics']['downstream_nodes']

if impact_count > 20:
    create_change_ticket(severity="HIGH", testing_required=True)
elif impact_count > 5:
    create_change_ticket(severity="MEDIUM", testing_required=True)
else:
    create_change_ticket(severity="LOW", testing_required=False)
```

---

## Performance Guide

### Query Time Expectations

| Tool | Typical Time | Notes |
|------|--------------|-------|
| `graph_findRootObjects` | 2–5s | Single SQL query with NOT EXISTS |
| `graph_bfsLevels` | 1–10s | One edge fetch + in-memory BFS |
| `graph_queryDependenciesAgent` depth 1–3 | 2–10s | SP-based, standard analysis |
| `graph_queryDependenciesAgent` depth 5 | 10–20s | Deep analysis |
| `graph_queryDependenciesAgent` depth 10 | 30–60s+ | Complete lineage |
| `graph_detectCycles` | 5–30s | Depends on graph size and component count |
| `graph_connectedComponents` | 5–20s | WCC propagation across all edges |

### `graph_bfsLevels` Performance Note

The Python BFS fetches all matching edges in one round-trip. Performance is dominated by the edge fetch volume and network transfer, not BFS computation. For typical ODEX graphs (thousands to low tens of thousands of edges), the Python implementation is faster than the retired SP due to zero volatile table overhead.

If `include_containers` is supplied, the SQL WHERE clause filters both endpoints before transfer — always use this parameter when the scope is known.

### Optimisation Strategies

1. **Use `include_containers` for `graph_bfsLevels`** — pushed into SQL, dramatically reduces edge fetch volume
2. **Use `exclude_objects` aggressively** — server-side for `graph_queryDependenciesAgent` (SP handles it); Python-side for `graph_bfsLevels`
3. **Start with `max_depth=3`** for `graph_queryDependenciesAgent` — incrementally increase only if needed
4. **Run `graph_detectCycles` first** before wave planning to confirm clean DAG
5. **Use `return_format="summary"`** for quick checks and change approvals

---

## Dependencies

### Required Teradata Objects

| Object | Used By | Required |
|--------|---------|----------|
| `DEV_01_ODEX_STD_0_V.ODEXRepository` | All tools (SELECT only) | ✅ |
| `DEV_01_ODEX_RPT_0_P.QueryDependenciesAgentBatch` | `graph_queryDependenciesAgent` | ✅ |
| `DEV_01_ODEX_RPT_0_P.graph_detectCycles` | `graph_detectCycles` | ✅ |
| `DEV_01_ODEX_RPT_0_P.graph_connectedComponents` | `graph_connectedComponents` | ✅ |
| `DEV_01_ODEX_RPT_0_P.graph_bfsLevels` | **Retired** — replaced by Python BFS | ❌ |

### Python Packages

- `teradatasql` (included in base MCP server)
- `fnmatch` (standard library — used by `graph_bfsLevels`)
- `collections` (standard library — used by `graph_bfsLevels`)
- `logging` (standard library)

### Permissions Required

| Permission | Required For |
|-----------|-------------|
| `SELECT` on `ODEXRepository` | All tools |
| `EXECUTE` on `QueryDependenciesAgentBatch` | `graph_queryDependenciesAgent` |
| `EXECUTE` on `graph_detectCycles` | `graph_detectCycles` |
| `EXECUTE` on `graph_connectedComponents` | `graph_connectedComponents` |
| `CREATE VOLATILE TABLE` | `graph_queryDependenciesAgent` (SP requirement) |
| `REPLACE PROCEDURE` on any graph SP | **Not required** — Python BFS needs no SP updates |

---

## Installation

### File Structure

```
teradata_mcp_server/tools/
├── graph_tools.py                     # Registration hub
├── graph/
│   ├── __init__.py
│   ├── _graph_utils.py
│   ├── graph_findRootObjects.py
│   ├── graph_bfsLevelsPy.py
│   ├── graph_queryDependenciesAgent.py
│   ├── graph_detectCycles.py
│   └── graph_connectedComponents.py
└── prompts/
    └── graph_bfsLevels.yml            # YAML prompt descriptor (this release)
```

### Configuration

Add to your `profiles.yml`:

```yaml
graph:
  allmodule: True
  tool:
    graph_findRootObjects: True
    graph_bfsLevels: True
    graph_queryDependenciesAgent: True
    graph_detectCycles: True
    graph_connectedComponents: True
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| **Query timeout** | Depth too high or large graph | Reduce `max_depth` or add `exclude_objects` / `include_containers` |
| **Empty BFS results** | Root node FQ name incorrect | Verify exact name via `graph_findRootObjects` — no wildcards in `root_node_list` |
| **`upstream_level` always None** | Correct behaviour for root objects | Root objects with in-degree zero have no upstream sources — this is expected |
| **Large edge fetch for BFS** | No `include_containers` specified | Always supply `include_containers` when scope is known |
| **SP procedure errors** | SP not deployed or privileges missing | Check `EXECUTE` permissions on the relevant SP |
| **Stale results** | ODEX repository not refreshed | Check `MAX(LastUpdated)` on `ODEXRepository`; request refresh if > 1 week |

### Debug Steps

```python
# 1. Verify object exists and find exact FQ name
result = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="DEV01_StGeo_RPT_T"
)
# Check result for the exact FullyQualifiedName

# 2. Test BFS with minimal scope
result = handle_graph_bfsLevelsPy(
    conn=connection,
    root_node_list="DEV01_StGeo_RPT_T.monthly_portfolio_risk_summary",
    max_depth_down=2
)

# 3. Check repository currency
base_readQuery(sql="""
    SELECT MAX(LastUpdated) AS LastRefresh
    FROM DEV_01_ODEX_STD_0_V.ODEXRepository
""")

# 4. Check cycle-free before wave planning
result = handle_graph_detectCycles(
    conn=connection,
    container_pattern="%StGeo%"
)
print(result['results']['summary_stats'][0]['Summary_Message'])
```

---

## Best Practices

1. **Always run `graph_detectCycles` before migration planning** — a cycle will cause topological sort to hang silently.

2. **Use `graph_findRootObjects` to seed `graph_bfsLevels`** — never guess root node names; they must be exact FQ names with no wildcards.

3. **Always supply `include_containers` for `graph_bfsLevels`** — without it, every edge in the repository is fetched. One additional LIKE pattern costs almost nothing; fetching a million irrelevant edges costs significantly.

4. **Deploy in `downstream_level` ascending order within each wave** — depth 0 (root) first, then +1, +2, and so on. Never deploy a consumer before its dependency.

5. **Check `cycle_candidates` in BFS results** — `direction='BOTH'` nodes with unequal absolute levels indicate back-edges. Investigate before treating them as simple dependents.

6. **Filter aggressively with `exclude_objects`** — document and version-control your team's standard exclusion patterns.

7. **Validate ODEX repository currency before critical decisions** — request refresh if more than one week old.

---

## Future Enhancements

| Tool | Status | Notes |
|------|--------|-------|
| `graph_findRootObjects` | ✅ Implemented (v1.1) | |
| `graph_bfsLevels` | ✅ Implemented (v2.0) | SP replaced by Python BFS |
| `graph_queryDependenciesAgent` | ✅ Implemented (v1.0) | |
| `graph_detectCycles` | ✅ Implemented (v1.2) | |
| `graph_connectedComponents` | ✅ Implemented (v1.3) | |
| `graph_findOrphanedObjects` | 🔲 Planned | Objects with no upstream or downstream |
| `graph_calculateMetrics` | 🔲 Planned | Centrality, clustering coefficient |
| `graph_suggestRefactoring` | 🔲 Planned | Structure-based refactoring opportunities |

---

## Version History

- **2.0** (2026-03-31): Major refactor — modular package structure, SP replaced by Python BFS
  - Split monolithic `graph_tools.py` into one file per tool under `graph/` sub-package
  - `graph_tools.py` reduced to a thin registration hub (imports + `GRAPH_TOOLS` list only)
  - `graph_bfsLevels` SP (`DEV_01_ODEX_RPT_0_P.graph_bfsLevels`) replaced by pure-Python BFS implementation (`handle_graph_bfsLevelsPy`) — no stored procedure required, one SQL round-trip, standard queue-based BFS
  - BFS traversal direction fix applied (Option B): upstream BFS now correctly uses reverse adjacency (Tgt→Src); downstream uses forward (Src→Tgt). Root objects with in-degree zero now correctly show `upstream_level=None` for all non-root nodes
  - Shared BFS helpers (`bfs_safe_int`, `create_bfs_summary`, `extract_cycle_candidates`) extracted to `graph/_graph_utils.py`
  - Added `GRAPH_FIND_ROOT_OBJECTS_TOOL` and `GRAPH_QUERY_DEPENDENCIES_TOOL` descriptor constants (were previously missing)
  - Added `YAML` prompt descriptor for `graph_bfsLevels` (`graph_bfsLevels.yml`)
  - README updated to reflect all five tools, new package structure, and Python BFS

- **1.3** (2026-01-15): Added `graph_connectedComponents` tool
  - Weakly Connected Component analysis via `graph_buildWCC` SP

- **1.2** (2025-12-01): Added `graph_detectCycles` tool
  - WCC-partitioned single-pass CTE cycle detection

- **1.1** (2025-03-05): Added `graph_findRootObjects` tool
  - Find objects with no upstream dependencies
  - CSV pattern support, object type filtering, two return formats

- **1.0** (2025-03-04): Initial release
  - `graph_queryDependenciesAgent` — bidirectional dependency analysis
  - Server-side filtering, three return formats, comprehensive documentation
