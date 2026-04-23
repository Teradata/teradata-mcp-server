# Graph Dependency Analysis Tools

**Version:** 3.0  
**Last Updated:** 2026-04-10  
**Purpose:** Directed dependency graph analysis for Teradata object lineage

This package provides seven complementary tools for analysing object dependencies
in Teradata. All tools are stored-procedure-free — the only Teradata privilege
required is `SELECT` on an edge repository conforming to the
[Graph Edge Contract](#graph-edge-contract).

---

## Quick Start

```python
# Step 0 — Generate an edge repository (once, if you don't have one)
#           For AI-Native Data Products, skip this — use lineage_graph directly:
#             edge_repository="{ProductName}_Semantic.lineage_graph"
ddl = handle_graph_edgeContractDDL(
    conn=connection,
    target_database="MY_PROJECT_Semantic",
    object_name="EdgeRepository",
    output_type="TABLE"
)

# Step 1 — Find root objects (seed points for analysis)
roots = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="%MY_PROJECT%",
    object_types="Table",
    edge_repository="MY_PROJECT_Semantic.EdgeRepository"
)

# Step 2 — Compute BFS hop distances and group into migration waves
waves = handle_graph_bfsLevels(
    conn=connection,
    root_node_list="MY_DB_STD_T.source_table_a,MY_DB_STD_T.source_table_b",
    include_containers="MY_DB%",
    edge_repository="MY_PROJECT_Semantic.EdgeRepository"
)

# Objects grouped by nearest_root  = migration wave grouping
# Objects ordered by downstream_level = deployment sequence within each wave

# Step 3 — Trace lineage and impact paths for a specific object
lineage = handle_graph_traceLineage(
    conn=connection,
    object_name="MY_DB_STD_T.source_table_a",
    max_depth_down=5,
    edge_repository="MY_PROJECT_Semantic.EdgeRepository"
)
```

---

## Tools

Seven complementary tools covering the full graph analysis workflow:

| Step | Tool | Implementation | Purpose |
|------|------|---------------|---------|
| 0 | [`graph_edgeContractDDL`](#graph_edgecontractddl) | Template | Generate edge repository DDL — start here |
| 1 | [`graph_findRootObjects`](#graph_findrootobjects) | SQL | Discover objects with no upstream dependencies |
| 2 | [`graph_bfsLevels`](#graph_bfslevels) | Python BFS | Wave planning, deployment sequencing, blast-radius sizing |
| 3 | [`graph_traceLineage`](#graph_tracelineage) | Python + recursive CTE | Full lineage tracing, impact path analysis, edge detail |
| 4 | [`graph_detectCycles`](#graph_detectcycles) | Python DFS | Circular reference detection, DAG validation |
| 5 | [`graph_connectedComponents`](#graph_connectedcomponents) | Python Union-Find | Graph partitioning, isolated sub-graph identification |
| 6 | [`graph_analyseDatabase`](#graph_analysedatabase) | Composite | All four analyses in one call, one shared edge fetch |

**Typical workflow:** `edgeContractDDL` → `findRootObjects` → `bfsLevels` → `traceLineage` → `detectCycles`

**When to use `graph_analyseDatabase`:** if you need three or more of the individual analyses, use this instead — it fetches the edge set once and shares it across all four analyses in a single MCP response.

---

## Graph Edge Contract

All tools require an **edge repository** — a Teradata table or view conforming to the Graph Edge Contract. The contract defines six required columns and two optional enrichment columns:

### Required Columns

| Column | Type | Description |
|--------|------|-------------|
| `Src_Container_Name` | `VARCHAR(128) NOT NULL` | Source (upstream) container — Teradata database name, ETL workflow folder, dbt project, etc. |
| `Src_Object_Name` | `VARCHAR(128) NOT NULL` | Source object name |
| `Src_Kind` | `VARCHAR(30) NOT NULL` | Source object type (e.g. `Table`, `View`, `Job`) |
| `Tgt_Container_Name` | `VARCHAR(128) NOT NULL` | Target (downstream) container |
| `Tgt_Object_Name` | `VARCHAR(128) NOT NULL` | Target object name |
| `Tgt_Kind` | `VARCHAR(30) NOT NULL` | Target object type |

### Optional Enrichment Columns

| Column | Type | Description |
|--------|------|-------------|
| `Edge_Relationship` | `VARCHAR(50)` | Nature of the edge: `DIRECT`, `ETL_INPUT`, `ETL_OUTPUT`, `JOIN`, `TRANSFORM` |
| `Transformation_Type` | `VARCHAR(50)` | Process category: `ETL`, `FEATURE_ENG`, `AGGREGATION`, `EMBEDDING_GEN` |

Optional columns are ignored by graph analysis tools but surfaced to graph visualisation clients for edge labelling.

### Edge Semantics

All edges share a single consistent direction — Src is always upstream, Tgt is always downstream. The `Edge_Relationship` optional column carries the semantic label for visualisation clients; the graph analysis tools traverse all edges identically regardless of label.

The same Src→Tgt direction is read differently depending on edge type:

| Edge type | How to read it | Example |
|---|---|---|
| Object dependency | Src *is referenced by* Tgt | `CUSTOMER_TABLE` → `CUSTOMER_VIEW` |
| ETL input | Src *is read by* Tgt | `CUSTOMER_TABLE` → `ETL_LOAD_JOB` |
| ETL output | Src *writes to* Tgt | `ETL_LOAD_JOB` → `CUSTOMER_FEATURES` |

In all three cases: Src is the prerequisite, Tgt is the consumer. A single edge repository can hold both object dependency edges and data lineage edges and be traversed uniformly by the graph tools.

The `lineage_graph` view (Observability Module v1.5) surfaces ETL jobs as first-class nodes, producing two edges per declared flow:
- **Leg 1:** `source_table` →*(is read by)*→ `job_name` (`Edge_Relationship = ETL_INPUT`)
- **Leg 2:** `job_name` →*(writes to)*→ `target_table` (`Edge_Relationship = ETL_OUTPUT`)

This enables end-to-end lineage traversal through jobs, not just between tables.

### AI-Native Data Product Shortcut

If you have a data product built on the [AI-Native Data Product standard](https://github.com/Teradata/ai-native-data-product), the `{ProductName}_Semantic.lineage_graph` view (Observability Module v1.5) already conforms to this contract. Use it directly:

```python
edge_repository="{ProductName}_Semantic.lineage_graph"
```

No DDL generation required.

---

## Package Structure

```
teradata_mcp_server/tools/
├── graph_tools.py                  # Registration hub (imports + GRAPH_TOOLS list only)
├── graph/
│   ├── __init__.py                 # Re-exports all handle_* for ModuleLoader
│   ├── _graph_utils.py             # Shared utilities (internal — not an MCP tool)
│   ├── graph_edge_contract.py      # Tool: DDL generator + Graph Edge Contract text
│   ├── graph_findRootObjects.py    # Tool: SQL-based root object discovery
│   ├── graph_bfsLevels.py          # Tool: Pure-Python BFS
│   ├── graph_traceLineage.py       # Tool: Python + recursive CTE lineage analysis
│   ├── graph_detectCycles.py       # Tool: Python Union-Find + iterative DFS
│   ├── graph_connectedComponents.py # Tool: Python Union-Find WCC analysis
│   └── graph_analyseDatabase.py    # Tool: Composite single-fetch analysis
└── utils.py                        # Shared MCP utilities
```

`graph_tools.py` is intentionally thin — it contains no logic, only imports and the `GRAPH_TOOLS` registration list. See the comments in that file for the rationale.

`_graph_utils.py` is an internal module. It is not registered as an MCP tool. It exports:
- `parse_csv_patterns` — normalise CSV input strings
- `build_like_or` — build single-column LIKE clauses for SQL WHERE
- `bfs_safe_int` — safe int conversion for nullable level columns
- `create_bfs_summary` — BFS result statistics
- `extract_cycle_candidates` — identify direction=BOTH nodes

---

## Tool Reference

### `graph_edgeContractDDL`

Generate Teradata DDL for a Graph Edge Contract-conforming edge repository.

Call this first if you don't yet have an edge repository. No database connection is used — DDL is returned as text ready to run.

#### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `target_database` | string | — | ✅ | Database in which to create the edge repository.<br>For AI-Native Data Products: `{ProductName}_Semantic` |
| `object_name` | string | `EdgeRepository` | ❌ | Name for the edge table or view |
| `output_type` | string | `TABLE` | ❌ | `TABLE`: CREATE TABLE DDL + sample DML<br>`VIEW`: customisable template for mapping an existing lineage source |

#### Example

```python
# Generate a CREATE TABLE with sample DML
result = handle_graph_edgeContractDDL(
    conn=connection,
    target_database="MY_PROJECT_Semantic",
    object_name="EdgeRepository",
    output_type="TABLE"
)
print(result[0]['ddl'])        # Run this in Teradata
print(result[0]['sample_dml']) # Optional: insert sample rows

# Generate a VIEW template to wrap an existing lineage source
result = handle_graph_edgeContractDDL(
    conn=connection,
    target_database="MY_PROJECT_Semantic",
    object_name="lineage_graph",
    output_type="VIEW"
)
```

---

### `graph_findRootObjects`

Find objects with no upstream dependencies in specified containers.

Root objects are foundational data sources that nothing else feeds into. They are the natural starting points for downstream impact analysis and migration wave planning.

#### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `container_pattern` | string | — | ✅ | Database/schema LIKE pattern(s). Supports `%` wildcards and CSV.<br>Examples: `MY_DB%`, `%PROJECT_A%,%PROJECT_B%` |
| `exclude_objects` | string | `''` | ❌ | LIKE patterns to exclude. Matches `Container.Object`.<br>Example: `SANDBOX%,%.temp_%` |
| `edge_repository` | string | — | ✅ | Edge repository conforming to the Graph Edge Contract.<br>AI-Native Data Products: `{ProductName}_Semantic.lineage_graph` |
| `object_types` | string | `''` | ❌ | Filter by object type: `Table`, `View`, `Procedure`, `Macro`.<br>CSV supported: `Table,View`. Empty = all types. |
| `return_format` | string | `detailed` | ❌ | `detailed` — full list with metadata<br>`summary` — statistics only |

#### Use Cases

| Use Case | Configuration |
|----------|---------------|
| Migration seed discovery | `container_pattern="%MY_PROJECT%"` |
| Source table discovery | `object_types="Table"` |
| Exclude sandbox schemas | `exclude_objects="SANDBOX%,%.temp_%"` |
| Quick count | `return_format="summary"` |

#### Example

```python
# Find root tables, ordered by downstream impact
result = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="MY_DB_STD_T,MY_DB_STD_V",
    object_types="Table",
    edge_repository="MY_PROJECT_Semantic.EdgeRepository"
)
for obj in result['results']['summary']['top_impact_objects']:
    print(f"  {obj['name']} → {obj['downstream_count']} dependents")
```

---

### `graph_bfsLevels`

Compute BFS shortest-path hop distances from one or more root nodes.

**Implementation:** Pure Python — One SQL round-trip fetches the scoped edge set; all BFS computation runs in the MCP server process.

**Use this tool for:** deployment sequencing, migration wave grouping, blast-radius sizing, cycle candidate depth analysis.

**Do not use this tool for:** lineage tracing, impact path detail, edge-level analysis — use `graph_traceLineage` for those.

#### Direction Convention

Each edge row: `Src` "is referenced by" `Tgt` → Src is the dependency (upstream); Tgt is the dependent (downstream).

| Direction | Traversal | Meaning |
|-----------|-----------|---------|
| Upstream BFS | Reverse adjacency (Tgt → Src) | Discovers what a node depends on |
| Downstream BFS | Forward adjacency (Src → Tgt) | Discovers what depends on a node |

Root objects with in-degree zero correctly show `upstream_level=None` for all non-root nodes — they have no upstream sources.

#### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `root_node_list` | string | — | ✅ | CSV of exact fully-qualified node names. No wildcards.<br>Example: `MY_DB.table_a,MY_DB.table_b` |
| `max_depth_up` | integer | `10` | ❌ | Maximum upstream hops. `0` = skip upstream analysis. |
| `max_depth_down` | integer | `10` | ❌ | Maximum downstream hops. `0` = skip downstream analysis. |
| `exclude_objects` | string | `''` | ❌ | CSV LIKE patterns to exclude from BFS traversal |
| `include_containers` | string | `''` | ❌ | CSV container LIKE patterns (whitelist). Always supply when scope is known — pushed into SQL to reduce fetch volume. |
| `edge_repository` | string | — | ✅ | Edge repository conforming to the Graph Edge Contract |

#### Example

```python
# Wave planning: downstream only, scoped to project containers
result = handle_graph_bfsLevels(
    conn=connection,
    root_node_list="MY_DB_STD_T.source_a,MY_DB_STD_T.source_b",
    max_depth_up=0,
    max_depth_down=10,
    include_containers="MY_DB%,REPORTING%",
    edge_repository="MY_PROJECT_Semantic.EdgeRepository"
)
# Sort by downstream_level ascending for deployment order
# Group by nearest_root for wave assignment
```

---

### `graph_traceLineage`

Analyse object dependencies — finds upstream dependencies (what the object depends on) and downstream dependents (what depends on the object).

**Implementation:** Hybrid — Python constructs Teradata recursive CTEs that execute entirely server-side. Only the reachable subgraph crosses the network.

**Use this tool for:** impact analysis, lineage tracing, pre-deployment validation, edge-level dependency detail.

**Do not use this tool for:** migration wave sequencing — use `graph_bfsLevels` for that.

#### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `object_name` | string | — | ✅ | Object name pattern(s). Supports `%` wildcards and CSV.<br>Single: `MY_DB.my_table`<br>Wildcard: `MY_DB%.%`<br>Multiple: `MY_DB_A.%,MY_DB_B.%` |
| `max_depth_up` | integer | `3` | ❌ | Maximum upstream levels to traverse (0–10) |
| `max_depth_down` | integer | `3` | ❌ | Maximum downstream levels to traverse (0–10) |
| `exclude_objects` | string | `''` | ❌ | CSV LIKE patterns to exclude. Matches `DB.Object` format. |
| `include_containers` | string | `''` | ❌ | CSV container LIKE patterns (whitelist). Empty = all containers. |
| `edge_repository` | string | — | ✅ | Edge repository conforming to the Graph Edge Contract |
| `return_format` | string | `detailed` | ❌ | `detailed`, `summary`, or `edges_only` |

#### Example

```python
# Full impact analysis — what breaks if this object changes?
result = handle_graph_traceLineage(
    conn=connection,
    object_name="MY_DB_STD_T.core_entity",
    max_depth_up=0,
    max_depth_down=5,
    edge_repository="MY_PROJECT_Semantic.EdgeRepository"
)
print(f"Downstream dependents: {len(result['results']['downstream_edges'])}")
```

---

### `graph_detectCycles`

Detect circular references (cycles) in the dependency graph.

**Implementation:** Pure Python — one SQL SELECT fetches the scoped edge set; Union-Find WCC partitioning followed by iterative DFS cycle detection runs in the MCP server process.

Run this tool before wave planning to confirm the graph is a valid DAG. A cycle will cause topological sort to hang silently.

#### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `container_pattern` | string | — | ✅ | CSV LIKE patterns for container scope.<br>Example: `MY_DB%` or `%PROJECT_A%,%PROJECT_B%` |
| `exclude_objects` | string | `''` | ❌ | CSV LIKE patterns to exclude from the scan |
| `edge_repository` | string | — | ✅ | Edge repository conforming to the Graph Edge Contract |

#### Example

```python
result = handle_graph_detectCycles(
    conn=connection,
    container_pattern="MY_DB%",
    edge_repository="MY_PROJECT_Semantic.EdgeRepository"
)
print(result['results']['summary_stats'][0]['Summary_Message'])
# "No cycles detected — graph is a DAG."
# or: "3 cycle(s) detected."
for cycle in result['results']['cycle_summaries']:
    print(f"  Cycle {cycle['Cycle_Id']}: {cycle['Cycle_Path']}")
```

---

### `graph_connectedComponents`

Identify all Weakly Connected Components (WCC) in the dependency graph.

**Implementation:** Pure Python — one SQL SELECT, then Union-Find WCC partitioning in the MCP server process.

A connected component is a maximal set of nodes reachable from one another when edge direction is ignored. Use this to understand graph structure, identify isolated sub-graphs, and pre-filter before cycle detection.

#### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `container_pattern` | string | — | ✅ | CSV LIKE patterns for container scope |
| `exclude_objects` | string | `''` | ❌ | CSV LIKE patterns to exclude from the scan |
| `edge_repository` | string | — | ✅ | Edge repository conforming to the Graph Edge Contract |

#### Example

```python
result = handle_graph_connectedComponents(
    conn=connection,
    container_pattern="MY_DB%",
    edge_repository="MY_PROJECT_Semantic.EdgeRepository"
)
stats = result['results']['summary_stats'][0]
print(f"{stats['Component_Count']} components, "
      f"largest has {stats['Largest_Component']} nodes")
```

---

### `graph_analyseDatabase`

Composite analysis — runs root object discovery, connected component analysis, cycle detection, and BFS wave planning in a **single MCP call** with **one shared edge fetch**.

Use this instead of calling the four individual tools when you need two or more of those analyses together. It eliminates the scalability bottleneck of serial MCP round-trips (4 SQL fetches → 1; 4 MCP responses → 1).

#### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `container_pattern` | string | — | ✅ | CSV LIKE patterns for container scope |
| `exclude_objects` | string | `''` | ❌ | CSV LIKE patterns to exclude |
| `top_n_roots` | integer | `4` | ❌ | Number of top root objects (by downstream impact) to include in BFS wave analysis |
| `max_depth_down` | integer | `10` | ❌ | Maximum downstream BFS hops from roots |
| `max_depth_up` | integer | `0` | ❌ | Maximum upstream BFS hops. `0` = skip upstream. |
| `edge_repository` | string | — | ✅ | Edge repository conforming to the Graph Edge Contract |

#### Example

```python
# Full database readiness assessment — one call
result = handle_graph_analyseDatabase(
    conn=connection,
    container_pattern="MY_DB%",
    top_n_roots=6,
    max_depth_down=10,
    edge_repository="MY_PROJECT_Semantic.EdgeRepository"
)

root_count   = result['results']['root_objects']['summary']['total_root_objects']
cycle_count  = result['results']['cycles']['stats'][0]['Cycle_Count']
comp_count   = result['results']['components']['stats'][0]['Component_Count']
bfs_nodes    = result['results']['bfs_waves']['summary']['total_nodes']
total_ms     = result['results']['edge_stats']['total_time_ms']

print(f"{root_count} roots | {cycle_count} cycles | "
      f"{comp_count} components | {bfs_nodes} BFS nodes | {total_ms}ms")
```

---

## Architecture

### Python/SQL Design

The only Teradata privilege required across the entire package is `SELECT` on the edge repository view or table.

| Tool | Implementation strategy |
|------|------------------------|
| `graph_edgeContractDDL` | Pure template generation — no SQL executed |
| `graph_findRootObjects` | Single SQL SELECT with NOT EXISTS subquery |
| `graph_bfsLevels` | One bulk edge SELECT; standard queue-based BFS (O(V+E)) in Python |
| `graph_traceLineage` | Python constructs recursive CTEs; traversal runs server-side in Teradata spool |
| `graph_detectCycles` | One scoped edge SELECT; Union-Find WCC + iterative DFS in Python |
| `graph_connectedComponents` | One scoped edge SELECT; path-compressed Union-Find in Python |
| `graph_analyseDatabase` | One shared edge SELECT; all four algorithms run in Python |

### Progressive Disclosure

The package supports both MCP registration modes simultaneously:

- **Static mode:** `graph_tools.py` → `GRAPH_TOOLS` list → MCP server registration at startup
- **Progressive Disclosure mode:** `__init__.py` → ModuleLoader discovers `handle_*` functions → `ContextCatalog` registers them using docstrings

In Progressive Disclosure mode the ContextCatalog uses the function docstrings for both approximate-match summaries and exact-match full documentation. The `*_TOOL` descriptor dicts serve static mode only.

---

## Dependencies

### Teradata

| Requirement | Details |
|------------|---------|
| `SELECT` on edge repository | The only privilege required — applies to all tools |
| Edge repository | A table or view conforming to the Graph Edge Contract.<br>Generate one with `graph_edgeContractDDL`, or use an existing `{ProductName}_Semantic.lineage_graph` view. |

No server-side DDL objects required.

### Python

All packages are standard library or already included in the base MCP server:

| Package | Used by | Source |
|---------|---------|--------|
| `teradatasql` | All tools | MCP server base |
| `collections` | `graph_bfsLevels`, `graph_analyseDatabase` | Standard library |
| `fnmatch` | `graph_bfsLevels` | Standard library |
| `logging` | All tools | Standard library |

---

## Installation

### File Placement

```
teradata_mcp_server/tools/
├── graph_tools.py
├── graph/
│   ├── __init__.py
│   ├── _graph_utils.py
│   ├── graph_edge_contract.py
│   ├── graph_findRootObjects.py
│   ├── graph_bfsLevels.py
│   ├── graph_traceLineage.py
│   ├── graph_detectCycles.py
│   ├── graph_connectedComponents.py
│   └── graph_analyseDatabase.py
└── utils.py
```

### Configuration

Add to your `profiles.yml`:

```yaml
graph:
  allmodule: True
  tool:
    graph_edgeContractDDL: True
    graph_findRootObjects: True
    graph_bfsLevels: True
    graph_traceLineage: True
    graph_detectCycles: True
    graph_connectedComponents: True
    graph_analyseDatabase: True
```

---

## Performance

### Key Principles

**Always supply `include_containers` for `graph_bfsLevels`** — this filter is pushed into the SQL WHERE clause, dramatically reducing edge fetch volume. Without it, every edge in the repository is fetched. One additional LIKE pattern costs almost nothing; fetching a million irrelevant edges costs significantly.

**Use `graph_analyseDatabase` when you need multiple analyses** — it runs four analyses from one edge fetch instead of four separate fetches.

**Start with `max_depth=3` for `graph_traceLineage`** — incrementally increase only if needed. Recursive CTE depth directly affects server-side spool consumption.

**Use `exclude_objects` aggressively** — filter out sandbox schemas, temporary objects, and personal schemas. Document and version-control your team's standard exclusion patterns.

**Run `graph_detectCycles` before wave planning** — a cycle will cause topological sort to hang silently.

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| **Empty BFS results** | Root node FQ name incorrect | Verify exact name via `graph_findRootObjects` — no wildcards in `root_node_list` |
| **`upstream_level` always None** | Correct behaviour for root objects | Root objects with in-degree zero have no upstream sources — this is expected |
| **Large edge fetch for BFS** | No `include_containers` specified | Always supply `include_containers` when scope is known |
| **Query timeout** | Depth too high or large graph | Reduce `max_depth` or add `exclude_objects` / `include_containers` |
| **`edge_repository` error** | Parameter not supplied | Pass the FQ name of your edge repository. AI-Native Data Products: `{ProductName}_Semantic.lineage_graph`. Otherwise run `graph_edgeContractDDL` first. |
| **NULL check violations** | Edge repository has NULL required columns | Run the validation query from the `graph_edgeContractDDL` sample DML output |

### Debug Steps

```python
# 1. Verify object exists and find exact FQ name
result = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="MY_DB_STD_T",
    edge_repository="MY_PROJECT_Semantic.EdgeRepository"
)
# Check result for the exact FullyQualifiedName

# 2. Test BFS with minimal scope and shallow depth
result = handle_graph_bfsLevels(
    conn=connection,
    root_node_list="MY_DB_STD_T.my_root_table",
    max_depth_down=2,
    edge_repository="MY_PROJECT_Semantic.EdgeRepository"
)

# 3. Check cycle-free before wave planning
result = handle_graph_detectCycles(
    conn=connection,
    container_pattern="MY_DB%",
    edge_repository="MY_PROJECT_Semantic.EdgeRepository"
)
print(result['results']['summary_stats'][0]['Summary_Message'])

# 4. Validate edge repository conforms to contract
#    (Run the validation query from graph_edgeContractDDL sample_dml output)
base_readQuery(sql="""
    SELECT 'NULL_CHECK' AS Validation, COUNT(*) AS Violations
    FROM MY_PROJECT_Semantic.EdgeRepository
    WHERE Src_Container_Name IS NULL
       OR Src_Object_Name    IS NULL
       OR Src_Kind           IS NULL
       OR Tgt_Container_Name IS NULL
       OR Tgt_Object_Name    IS NULL
       OR Tgt_Kind           IS NULL
""")
```

---

## Best Practices

1. **Always run `graph_detectCycles` before migration planning** — a cycle will cause topological sort to hang silently.

2. **Use `graph_findRootObjects` to seed `graph_bfsLevels`** — never guess root node names; they must be exact FQ names with no wildcards.

3. **Always supply `include_containers` for `graph_bfsLevels`** — without it, every edge in the repository is fetched regardless of scope.

4. **Deploy in `downstream_level` ascending order within each wave** — depth 0 (root) first, then +1, +2, and so on. Never deploy a consumer before its dependency.

5. **Check `cycle_candidates` in BFS results** — `direction='BOTH'` nodes with unequal absolute levels indicate back-edges. Investigate before treating them as simple dependents.

6. **Prefer `graph_analyseDatabase` for full readiness assessments** — one call, one edge fetch, four analyses.

---

## Future Enhancements

| Tool | Status | Notes |
|------|--------|-------|
| `graph_edgeContractDDL` | ✅ v1.1 | Graph Edge Contract v1.1 — optional enrichment columns |
| `graph_findRootObjects` | ✅ v1.1 | |
| `graph_bfsLevels` | ✅ v2.0 | SP replaced by pure-Python BFS |
| `graph_traceLineage` | ✅ v1.0 | Renamed from `graph_queryDependenciesAgent` |
| `graph_detectCycles` | ✅ v2.0 | SP replaced by Python Union-Find + iterative DFS |
| `graph_connectedComponents` | ✅ v2.0 | SP replaced by Python Union-Find |
| `graph_analyseDatabase` | ✅ v1.0 | Composite single-fetch analysis |
| `graph_findOrphanedObjects` | 🔲 Planned | Objects with no upstream or downstream |
| `graph_calculateMetrics` | 🔲 Planned | Centrality, clustering coefficient |
| `graph_suggestRefactoring` | 🔲 Planned | Structure-based refactoring opportunities |

---

## Version History

### 3.0 (2026-04-10)

Compliance pass, Graph Edge Contract v1.1, SP-free architecture for all tools.

- **Rename:** `graph_queryDependenciesAgent` → `graph_traceLineage`. The tool is a deterministic recursive CTE query, not an agent.
- **New tools:** `graph_edgeContractDDL` (DDL generator + canonical contract text) and `graph_analyseDatabase` (composite single-fetch analysis).
- **SP-free:** `graph_detectCycles` and `graph_connectedComponents` converted from SP-based to pure-Python (Union-Find WCC + iterative DFS). No stored procedures remain anywhere in the package.
- **Graph Edge Contract v1.1:** Column names corrected from `SrcContainer`/`SrcObject`/`SrcKind` to `Src_Container_Name`/`Src_Object_Name`/`Src_Kind` (and Tgt equivalents) — prior generated tables were incompatible with the tool SQL. Optional enrichment columns `Edge_Relationship` and `Transformation_Type` added. `Src_Kind`/`Tgt_Kind` COMPRESS lists expanded to cover both single-letter codes and full-word values.
- **Parameter standardisation:** `object_dependency_table` → `edge_repository`; `excl_patterns` → `exclude_objects` across `graph_detectCycles` and `graph_connectedComponents`.
- **Dead parameter removal:** `strategy` and `max_edges_for_cte` removed from `graph_detectCycles`.
- **Helper consolidation (phase 1):** `parse_csv_patterns` and `build_like_or` extracted to `_graph_utils.py`; 10 local copies removed across 6 files.
- **AI-Native Data Product convention:** `{ProductName}_Semantic.lineage_graph` (Observability Module v1.5) documented as a ready-to-use edge repository requiring no DDL generation.
- Progressive Disclosure compliance: all 7 tools registered in `GRAPH_TOOLS`; `GRAPH_EDGE_CONTRACT_DDL_TOOL` descriptor added.

### 2.0 (2026-03-31)

Major refactor — modular package structure, SP replaced by Python BFS for `graph_bfsLevels`.

- Split monolithic `graph_tools.py` into one file per tool under `graph/` sub-package
- `graph_tools.py` reduced to a thin registration hub
- `graph_bfsLevels` SP replaced by pure-Python BFS — no stored procedure, one SQL round-trip, standard queue-based BFS (O(V+E))
- BFS traversal direction fix: upstream BFS now correctly uses reverse adjacency (Tgt→Src)
- Shared BFS helpers extracted to `graph/_graph_utils.py`

### 1.3 (2026-01-15)

Added `graph_connectedComponents` — Weakly Connected Component analysis.

### 1.2 (2025-12-01)

Added `graph_detectCycles` — WCC-partitioned cycle detection.

### 1.1 (2025-03-05)

Added `graph_findRootObjects` — root object discovery with CSV pattern support, object type filtering, and two return formats.

### 1.0 (2025-03-04)

Initial release — `graph_queryDependenciesAgent` (now `graph_traceLineage`): bidirectional dependency analysis via server-side recursive CTEs.
