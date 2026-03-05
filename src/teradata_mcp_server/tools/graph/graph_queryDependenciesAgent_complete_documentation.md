# graph_queryDependenciesAgent Tool - Complete Function Documentation

**Version:** 1.0  
**Last Updated:** 2025-03-04  
**Purpose:** Teradata Object Dependency Analysis via ODEX Framework

---

## Overview

Analyse object dependencies in Teradata using graph traversal via the QueryDependenciesAgent stored procedure.

Finds **upstream dependencies** (what the object depends on) and **downstream dependencies** (what depends on the object). Returns nodes and edges representing the complete dependency graph.

### Primary Use Cases
- **Impact Analysis:** "What breaks if I change/drop this object?"
- **Lineage Tracing:** "Where does this data come from?"
- **Dependency Discovery:** "What does this object use?"
- **Documentation:** Understanding object relationships
- **Pre-deployment Validation:** Checking impacts before making changes

---

## Parameters Reference

### object_name
**Type:** `string`  
**Required:** `true`  

Fully qualified object name in the format `DatabaseName.ObjectName`.

Supports SQL LIKE wildcards (%):
- `DEV01_StGeo_STD_T.mortgage_account` - Exact match for specific table
- `DEV01_StGeo_STD_T.%` - All objects in a specific database
- `%.mortgage_%` - All objects with 'mortgage_' prefix across all databases

**Examples:**
```
DBC.TablesV
DEV01_StGeo_STD_T.mortgage_account
DEV02_WBC_STD_V.Mortgage_CDE_View
DEV_01_ODEX_STD_0_P.CheckSQLValidity
```

**Note:** Wildcards enable bulk analysis but may return very large result sets.

---

### max_depth_up
**Type:** `integer`  
**Required:** `false`  
**Default:** `3`  
**Range:** `0-10`

Maximum levels to traverse **upstream** (dependencies this object relies on).

**Depth Levels:**
- `0` = No upstream analysis (downstream only)
- `1` = Direct dependencies only (immediate parents)
- `2` = Parents + grandparents
- `3` = Three levels up (default - good balance)
- `5` = Deep lineage analysis
- `10` = Maximum depth (may return very large graphs)

**Performance Impact:**  
Higher values increase query time exponentially and result size. Use lower values for quick checks, higher values for comprehensive lineage analysis.

**Examples:**

| Value | Use Case |
|-------|----------|
| 0 | Downstream impact only |
| 1 | Find immediate dependencies |
| 3 | Standard impact analysis (default) |
| 10 | Complete lineage trace |

---

### max_depth_down
**Type:** `integer`  
**Required:** `false`  
**Default:** `3`  
**Range:** `0-10`

Maximum levels to traverse **downstream** (objects that depend on this one).

**Depth Levels:**
- `0` = No downstream analysis (upstream only)
- `1` = Direct dependents only (immediate children)
- `2` = Children + grandchildren  
- `3` = Three levels down (default - good balance)
- `5` = Deep blast radius analysis
- `10` = Maximum depth (complete impact)

**Critical for Impact Analysis:**  
Shows the complete blast radius of changes. Higher values reveal full downstream impact but significantly increase processing time.

**Examples:**

| Value | Use Case |
|-------|----------|
| 0 | Upstream lineage only |
| 1 | Find immediate consumers |
| 3 | Standard blast radius (default) |
| 10 | Complete impact trace |

---

### exclude_objects
**Type:** `string`  
**Required:** `false`  
**Default:** `""` (empty string - no exclusions)

Comma-separated list of fully qualified object name patterns to exclude. Supports SQL LIKE wildcards (%).

**🔥 CRITICAL:** This is **SERVER-SIDE filtering** - significantly more efficient than client-side post-processing.

#### Pattern Matching Rules
- `%` matches zero or more characters
- Patterns are **case-sensitive** (match actual database naming)
- Multiple patterns separated by commas
- Matches against full qualified name: `DatabaseName.ObjectName`

#### Database-Level Exclusions
Exclude entire database families by matching the database prefix:

```
-- Single database family
PRD_%              -- All objects in databases starting with PRD_

-- Multiple database families  
PRD_%,TST_%,UAT_%  -- Production, test, and UAT databases

-- Specific database
PROD_DB.%          -- All objects in PROD_DB only
```

#### Object-Level Exclusions
Exclude objects by name pattern across all databases:

```
-- Temporary objects
%.temp_%           -- All objects with 'temp_' prefix

-- Backup objects
%.bak_%,%.backup_% -- Backup and archive objects

-- System objects
%._sys_%,%.#%      -- System and temporary objects
```

#### Common Use Cases

**Production Safety:**
```
PRD_%,PROD_%
-- Excludes all production databases
```

**Multi-Environment Focus:**
```
TST_%,UAT_%,STG_%,PRD_%
-- Focus on DEV only by excluding all other environments
```

**Cleanup Analysis:**
```
OLD_%,ARCHIVE_%,DEPRECATED_%,LEGACY_%
-- Exclude deprecated and archived databases
```

**Regulatory Compliance:**
```
COMPLIANCE_%,REG_%,AUDIT_%,PII_%
-- Exclude sensitive/regulated databases
```

**Session-Specific:**
```
C_D02%,DFJ%
-- Exclude specific project or personal schemas
```

#### Real-World Example

**Scenario:** Analyse DBC.TablesV dependencies, but exclude production, test schemas, and deprecated databases.

```python
graph_queryDependenciesAgent(
    object_name="DBC.TablesV",
    max_depth_down=10,
    exclude_objects="PRD_%,DFJ%,C_D02%,TST_%,OLD_%"
)
```

**Result:** Reduced from 71 edges to 52 edges (19 objects excluded = 27% reduction)

---

### include_containers
**Type:** `string`  
**Required:** `false`  
**Default:** `""` (empty - all containers included)

Comma-separated list of schemas/databases to include in analysis. Acts as a **whitelist**.

**When empty (default):** All containers included (subject to exclude_objects filter)  
**When specified:** ONLY listed containers are analysed

#### Use Cases
- Focus analysis on specific project databases
- Limit scope to specific data domains  
- Isolate particular application schemas

#### Combining with exclude_objects
Fine-grained control by combining include (whitelist) and exclude (blacklist):

```python
include_containers="DEV_%"         # Only dev databases
exclude_objects="DEV_ARCHIVE_%"    # But not archived dev
```

#### Examples

**Single Project:**
```
DEV01_StGeo_STD_T,DEV01_StGeo_STD_V
-- Only StGeo tables and views
```

**Multiple Business Domains:**
```
MORTGAGE_%,LENDING_%,CREDIT_%
-- Multiple related domains
```

**Environment-Specific:**
```
DEV_%
-- All development databases (using wildcard)
```

---

### edge_repository
**Type:** `string`  
**Required:** `false`  
**Default:** `DEV_01_ODEX_STD_0_V.ODEXRepository`

Edge table containing pre-computed dependency information.

#### What is the ODEX Repository?

The ODEX (Object Dependency Exchange) repository stores dependency relationships between database objects, populated by:
- SQL parsing tools
- Metadata analysis engines
- Manual curation for edge cases

#### Repository Structure

Typically includes:
- **Source object:** Container name + object name
- **Target object:** Container name + object name  
- **Relationship type:** "referenced by", "calls", "inserts into", etc.
- **Edge metadata:** Last updated timestamp, confidence score, etc.

#### Environment-Specific Repositories

Different repositories exist for different environments:

```
-- Development
DEV_01_ODEX_STD_0_V.ODEXRepository

-- Production  
PRD_01_ODEX_STD_0_V.ODEXRepository

-- Project-specific
PROJECT_ODEX.DependencyGraph
MIGRATION_META.EdgeRepository
```

#### Performance Considerations

- ✅ **Good:** Repository has indexes on source/target containers
- ⚠️ **Warning:** Stale repositories return incomplete dependencies
- 🔄 **Best Practice:** Regular updates ensure accuracy

**Index Requirements:**
```sql
CREATE INDEX idx_src ON ODEXRepository(Src_Container_Name, Src_Object_Name);
CREATE INDEX idx_tgt ON ODEXRepository(Tgt_Container_Name, Tgt_Object_Name);
```

---

### return_format
**Type:** `string`  
**Required:** `false`  
**Default:** `detailed`  
**Valid Values:** `detailed`, `summary`, `edges_only`

Output format controlling level of detail in results.

#### Format Comparison

| Format | Nodes | Edges | Stats | Metadata | Use Case |
|--------|-------|-------|-------|----------|----------|
| **detailed** | ✅ Full | ✅ Full | ✅ Yes | ✅ Yes | Visualisation, debugging |
| **summary** | ❌ Count only | ❌ Count only | ✅ Yes | ✅ Yes | Quick impact check |
| **edges_only** | ❌ No | ✅ Full | ❌ Minimal | ⚠️ Basic | Graph construction |

#### detailed (Default)
Returns complete information:
- Full node list with all attributes (type, depth, direction)
- Complete edge list with relationship details
- Summary statistics
- Extensive metadata about query execution

**Best for:**
- Comprehensive dependency analysis
- Building visualisations (D3.js, Cytoscape)
- Debugging dependency issues
- Documentation generation

#### summary
Returns high-level statistics only:
- Node counts by type and depth
- Edge counts by direction
- Aggregate metrics
- No individual node/edge details

**Best for:**
- Quick impact assessment ("How many objects affected?")
- Performance monitoring
- Executive reporting
- Change management approvals

#### edges_only
Returns only edge relationships:
- Complete edge list
- Minimal metadata
- No node details (can be derived from edges)

**Best for:**
- Building dependency graphs (nodes derived from edges)
- Network analysis algorithms
- Importing into graph databases (Neo4j, etc.)
- Minimising data transfer size

**Performance:**
- `summary` is **fastest** (least data transferred)
- `edges_only` is **medium** (nodes can be derived)
- `detailed` is **slowest** but most complete

---

## Best Practices

### 1. Start Conservative
Always begin with `max_depth=1` or `max_depth=3` for initial exploration. Incrementally increase depth only if needed.

### 2. Filter Aggressively
Use `exclude_objects` liberally to reduce noise and improve performance. Common patterns:
```python
exclude_objects="PRD_%,OLD_%,temp_%,%.bak_%"
```

### 3. Cache Results
Store frequently accessed dependency graphs to avoid repeated expensive queries.

### 4. Validate Repository Currency
Before critical decisions, ensure the ODEX repository is up to date.

### 5. Validate Object Names
Use `base_tableList` to verify object exists before querying dependencies.

### 6. Choose Right Format
- Use `detailed` for visualisation and documentation
- Use `summary` for quick checks and approvals
- Use `edges_only` for graph databases

### 7. Document Exclusion Patterns
As exclusion patterns evolve, document them for team consistency.

### 8. Test with Depth 1 First
Before running deep queries, test with `max_depth=1` to estimate result size.

---

## Common Parameter Combinations

| Scenario | Parameters |
|----------|------------|
| **Impact Analysis** | `max_depth_up=0, max_depth_down=5` |
| **Data Lineage** | `max_depth_up=10, max_depth_down=0` |
| **Full Context** | `max_depth_up=5, max_depth_down=5` |
| **Quick Check** | `max_depth_down=1, return_format="summary"` |
| **Safe Dev** | `exclude_objects="PRD_%,PROD_%"` |
| **Project Focus** | `include_containers="PROJECT_%"` |

---

## Common Exclusion Patterns

```python
# Production safety
"PRD_%,PROD_%"

# Multi-environment
"PRD_%,TST_%,UAT_%,STG_%"

# Deprecated/legacy
"OLD_%,ARCHIVE_%,DEPRECATED_%,LEGACY_%"

# Temporary/system
"%.temp_%,%.bak_%,%._sys_%"

# Personal/sandbox
"DFJ%,C_D02%,SANDBOX_%"
```

---

## Performance Targets

| Metric | Target | Action if Exceeded |
|--------|--------|-------------------|
| Query Time | < 10s | Reduce depth or add exclusions |
| Result Nodes | < 500 | Add exclude_objects |
| Result Edges | < 1000 | Reduce max_depth or scope |
| Depth Setting | ≤ 5 | Only use 10 for complete traces |

---

**End of Documentation**
