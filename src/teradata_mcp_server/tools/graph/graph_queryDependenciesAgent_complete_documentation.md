# graph_findRootObjects Tool - Complete Function Documentation

**Version:** 1.0  
**Last Updated:** 2025-03-05  
**Purpose:** Identify Root Objects for Downstream Impact Analysis

---

## Overview

Find root objects (objects with no upstream dependencies) in specified Teradata databases or schemas using the ODEX framework.

Root objects represent **foundational data sources** that nothing else depends upon. They are ideal starting points for downstream impact analysis because they sit at the beginning of data flow pipelines.

### What Are Root Objects?

Root objects are database objects that:
- **Have NO upstream dependencies** - they don't depend on any other objects
- **Appear only as sources** in the ODEX repository (never as targets)
- **Represent foundation data** - base tables, landing tables, source feeds
- **Are ideal starting points** for downstream impact analysis

### Primary Use Cases
- **Finding starting points** for downstream impact analysis
- **Identifying source tables** and base objects in data pipelines
- **Discovering independent objects** that can be safely analysed in isolation
- **Understanding data flow origins** in a schema or database
- **Planning migration or refactoring** by identifying foundation objects

---

## Parameters Reference

### container_pattern
**Type:** `string`  
**Required:** `true`  

Database or schema pattern(s) to search for root objects.

Supports SQL LIKE wildcards (%):
- `DEV01_StGeo_STD_T` - Exact match for specific database
- `%WBC%` - All databases containing 'WBC'
- `DEV01_%` - All databases starting with 'DEV01_'
- `%_STD_T` - All databases ending with '_STD_T'

**CRITICAL: CSV Support**  
Multiple patterns can be specified as a **comma-separated string** (NOT an array):
- `%WBC%,%StGeo%` - All WBC and StGeo databases
- `DEV01_%,DEV02_%` - All DEV01 and DEV02 databases
- `DEV01_StGeo_STD_T,DEV02_WBC_STD_T` - Specific databases

**Examples:**
```
%WBC%
%StGeo%
%WBC%,%StGeo%
DEV01_StGeo_STD_T
DEV01_%,DEV02_%
```

**Whitespace Handling:**  
Whitespace is automatically trimmed from patterns:
- `%WBC%,%StGeo%` (recommended - no spaces)
- `%WBC%, %StGeo%` (also valid - spaces will be trimmed)

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
# Single database family
PRD_%              # All objects in databases starting with PRD_

# Multiple database families  
PRD_%,TST_%,UAT_%  # Production, test, and UAT databases

# Specific database
PROD_DB.%          # All objects in PROD_DB only
```

#### Object-Level Exclusions
Exclude objects by name pattern across all databases:

```
# Temporary objects
%.temp_%           # All objects with 'temp_' prefix

# Backup objects
%.bak_%,%.backup_% # Backup and archive objects

# System objects
%._sys_%,%.#%      # System and temporary objects
```

#### Common Exclusion Patterns

**Production Safety:**
```
PRD_%,PROD_%
# Excludes all production databases
```

**Multi-Environment Focus (Dev Only):**
```
PRD_%,TST_%,UAT_%,STG_%
# Focus on DEV by excluding all other environments
```

**Cleanup Analysis:**
```
OLD_%,ARCHIVE_%,DEPRECATED_%,LEGACY_%
# Exclude deprecated and archived databases
```

**Personal/Sandbox Exclusion:**
```
DFJ%,C_D02%,SANDBOX_%
# Exclude personal and sandbox schemas
```

---

### edge_repository
**Type:** `string`  
**Required:** `false`  
**Default:** `DEV_01_ODEX_STD_0_V.ODEXRepository`

Edge table containing pre-computed dependency information from the ODEX framework.

#### What is the ODEX Repository?

The ODEX (Object Dependency Exchange) repository stores dependency relationships between database objects.

#### Environment-Specific Repositories

Different repositories exist for different environments:

```
# Development
DEV_01_ODEX_STD_0_V.ODEXRepository

# Production  
PRD_01_ODEX_STD_0_V.ODEXRepository
```

---

### object_types
**Type:** `string`  
**Required:** `false`  
**Default:** `""` (empty - all types included)

Comma-separated list of object types to include (optional filter).

#### Valid Object Types

| Code | Object Type | Example Use Case |
|------|-------------|------------------|
| `T` | Tables | Find base tables only |
| `V` | Views | Find foundational views |
| `P` | Stored Procedures | Find independent procedures |
| `M` | Macros | Find base macros |

#### Examples

```python
# Tables only
object_types="T"

# Tables and views
object_types="T,V"

# Procedures only
object_types="P"

# Empty (all types)
object_types=""
```

---

### return_format
**Type:** `string`  
**Required:** `false`  
**Default:** `detailed`  
**Valid Values:** `detailed`, `summary`

Output format controlling level of detail in results.

#### Format Comparison

| Format | Object List | Statistics | Metadata | Use Case |
|--------|-------------|------------|----------|----------|
| **detailed** | ✅ Full | ✅ Yes | ✅ Yes | See complete list |
| **summary** | ❌ Names only | ✅ Yes | ✅ Yes | Quick overview |

#### detailed (Default)
Returns complete information:
- Full list of root objects with all attributes
- Summary statistics
- Database and type breakdowns
- Top impact objects (by downstream dependent count)

**Best for:**
- Comprehensive root object analysis
- Identifying specific objects to analyse
- Understanding distribution across databases
- Planning downstream impact studies

#### summary
Returns high-level statistics only:
- Total count of root objects
- Breakdown by object type
- Breakdown by database
- Top 10 objects by downstream impact
- List of root object names

**Best for:**
- Quick counts ("How many root objects?")
- Executive reporting
- Initial scoping
- Performance (less data transferred)

---

## Return Structure

### Detailed Format

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
      },
      ...
    ],
    "summary": {
      "total_root_objects": 42,
      "container_pattern": "%WBC%,%StGeo%",
      "object_type_counts": {
        "T": 35,
        "V": 7
      },
      "database_counts": {
        "DEV01_StGeo_STD_T": 20,
        "DEV02_WBC_STD_T": 22
      },
      "total_downstream_dependencies": 387,
      "average_downstream_per_root": 9.21,
      "top_impact_objects": [
        {
          "name": "DEV01_StGeo_STD_T.mortgage_account",
          "type": "T",
          "downstream_count": 15
        },
        ...
      ]
    }
  },
  "metadata": {
    "tool_name": "graph_findRootObjects",
    "container_pattern": "%WBC%,%StGeo%",
    "row_count": 42,
    "status": "success"
  }
}
```

### Summary Format

```json
{
  "results": {
    "summary_text": "ROOT OBJECTS ANALYSIS SUMMARY\n...",
    "statistics": {
      "total_root_objects": 42,
      "object_type_counts": {...},
      "database_counts": {...},
      "top_impact_objects": [...]
    },
    "root_object_names": [
      "DEV01_StGeo_STD_T.mortgage_account",
      "DEV02_WBC_STD_T.Mortgage",
      ...
    ]
  }
}
```

---

## Best Practices

### 1. Use Wildcards Effectively
Always use wildcards when searching multiple databases:
```python
# ✅ Good - searches all WBC databases
container_pattern="%WBC%"

# ❌ Bad - searches for exact match "WBC"
container_pattern="WBC"
```

### 2. Filter Aggressively
Use `exclude_objects` to reduce noise:
```python
exclude_objects="PRD_%,OLD_%,%.temp_%,%.bak_%"
```

### 3. Filter by Object Type When Needed
Focus on specific object types:
```python
# Only find root tables
object_types="T"

# Only find root tables and views
object_types="T,V"
```

### 4. Choose Right Format
- Use `detailed` when you need to see the actual objects
- Use `summary` for quick counts and overviews

### 5. Start Broad, Then Narrow
Begin with broad patterns, then add filters:
```python
# Step 1: Find all root objects
container_pattern="%WBC%,%StGeo%"

# Step 2: Refine with exclusions
exclude_objects="PRD_%,%.temp_%"

# Step 3: Filter by type if needed
object_types="T"
```

### 6. Use Results for Downstream Analysis
Root objects with highest `DownstreamDependentCount` have broadest impact:
```python
# Results are automatically sorted by DownstreamDependentCount DESC
# Top objects in results list have highest downstream impact
```

---

## Common Parameter Combinations

| Scenario | Parameters |
|----------|------------|
| **All Root Objects in WBC/StGeo** | `container_pattern="%WBC%,%StGeo%"` |
| **Root Tables Only** | `object_types="T"` |
| **Excluding Production** | `exclude_objects="PRD_%,PROD_%"` |
| **Quick Count** | `return_format="summary"` |
| **Dev Environment Only** | `container_pattern="DEV%", exclude_objects="PRD_%,TST_%"` |

---

## Example Queries

### Natural Language (Triggers)

```
"Which objects in WBC and StGeo databases should I start analysing?"
"Find root objects in DEV01 databases"
"What are the starting points for impact analysis in StGeo?"
"Show me base tables with no upstream dependencies"
"Which objects have no dependencies in WBC?"
```

### Python Code Examples

**1. Basic Root Object Search**

```python
# Find all root objects in WBC and StGeo databases
result = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="%WBC%,%StGeo%"
)

print(f"Found {len(result['results']['root_objects'])} root objects")
for obj in result['results']['root_objects'][:10]:
    print(f"  {obj['FullyQualifiedName']} → {obj['DownstreamDependentCount']} dependents")
```

**2. Root Tables Only**

```python
# Find only root tables (no views, procedures, etc.)
result = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="DEV01_%",
    object_types="T"
)
```

**3. Excluding Production and Temporary Objects**

```python
# Find root objects in dev, excluding production and temp objects
result = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="%WBC%,%StGeo%",
    exclude_objects="PRD_%,%.temp_%,%.bak_%"
)
```

**4. Quick Summary**

```python
# Get quick overview without full object list
result = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="%StGeo%",
    return_format="summary"
)

print(result['results']['summary_text'])
```

**5. Identifying High-Impact Root Objects**

```python
# Find root objects and identify those with most downstream impact
result = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="%WBC%,%StGeo%",
    return_format="detailed"
)

# Objects are sorted by DownstreamDependentCount DESC
top_impact = result['results']['summary']['top_impact_objects']
print("Start downstream analysis with these high-impact roots:")
for obj in top_impact[:5]:
    print(f"  {obj['name']} ({obj['type']}) → {obj['downstream_count']} dependents")
```

---

## Performance Guide

### Query Time Expectations

| Container Scope | Typical Time | Notes |
|-----------------|--------------|-------|
| Single database | 2-5 seconds | Fast |
| Multiple databases (%WBC%) | 5-15 seconds | Standard |
| All databases (%) | 20-60+ seconds | Use exclusions |

### Result Size Expectations

| Scope | Typical Root Objects |
|-------|---------------------|
| Single small database | 5-20 |
| Single large database | 20-100 |
| Multiple databases | 50-500+ |

### Optimisation Strategies

1. **Use specific container patterns**
   - `DEV01_StGeo_STD_T` faster than `%StGeo%`
   - `%WBC%,%StGeo%` faster than `%`

2. **Use exclude_objects aggressively**
   - Can reduce result set by 30-70%
   - Server-side filtering is very efficient

3. **Filter by object_types**
   - `object_types="T"` focuses on tables only
   - Reduces result set significantly

4. **Use return_format wisely**
   - `summary` for quick checks (smallest transfer)
   - `detailed` when you need the actual list

---

## Integration Patterns

### With Downstream Impact Analysis

```python
# Step 1: Find root objects
root_result = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="%WBC%,%StGeo%",
    object_types="T"  # Tables only
)

# Step 2: Analyse downstream impact for each root
for root_obj in root_result['results']['root_objects']:
    if root_obj['DownstreamDependentCount'] > 10:  # High impact
        impact_result = handle_graph_queryDependenciesAgent(
            conn=connection,
            object_name=root_obj['FullyQualifiedName'],
            max_depth_up=0,
            max_depth_down=5
        )
        
        print(f"\nImpact analysis for {root_obj['FullyQualifiedName']}:")
        print(f"  Downstream objects affected: {impact_result['results']['summary']['downstream_nodes']}")
```

### With Change Management

```python
# Find root objects for migration planning
root_result = handle_graph_findRootObjects(
    conn=connection,
    container_pattern="LEGACY_%",
    exclude_objects="%.temp_%,%.bak_%"
)

# Prioritise by downstream impact
roots = root_result['results']['root_objects']
high_priority = [r for r in roots if r['DownstreamDependentCount'] > 20]
medium_priority = [r for r in roots if 5 <= r['DownstreamDependentCount'] <= 20]
low_priority = [r for r in roots if r['DownstreamDependentCount'] < 5]

print(f"Migration planning:")
print(f"  High priority (>20 dependents): {len(high_priority)} objects")
print(f"  Medium priority (5-20 dependents): {len(medium_priority)} objects")
print(f"  Low priority (<5 dependents): {len(low_priority)} objects")
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| **No Results** | Pattern doesn't match any databases | Verify database names with `base_databaseList` |
| **Too Many Results** | Pattern too broad | Add `exclude_objects` or narrow `container_pattern` |
| **Unexpected Objects** | Object has hidden dependencies | Check ODEX repository currency |
| **Query Timeout** | Searching too many containers | Use more specific patterns or add exclusions |

### Debug Steps

1. **Verify databases exist**
   ```python
   base_databaseList(scope='user')
   ```

2. **Test with specific database**
   ```python
   result = handle_graph_findRootObjects(
       container_pattern="DEV01_StGeo_STD_T"  # Specific, not wildcard
   )
   ```

3. **Check ODEX repository**
   ```python
   base_readQuery(sql=f"""
       SELECT COUNT(*) as EdgeCount
       FROM DEV_01_ODEX_STD_0_V.ODEXRepository
       WHERE Src_Container_Name LIKE '%WBC%'
   """)
   ```

---

## Technical Implementation Notes

### SQL Query Strategy

The tool uses a subquery approach to identify root objects:

1. **Main Query**: Find all objects in specified containers
2. **Subquery**: Find all objects that appear as targets (have upstream dependencies)
3. **Exclusion**: Remove objects from main query that appear in subquery
4. **Result**: Objects that are only sources (root objects)

### Why This Approach?

- **Efficient**: Single query with subquery is faster than multiple queries
- **Accurate**: Guaranteed to find true roots (no upstream dependencies)
- **Scalable**: Server-side filtering and grouping
- **Flexible**: Supports wildcards, CSV patterns, and exclusions

---

**End of Documentation**
