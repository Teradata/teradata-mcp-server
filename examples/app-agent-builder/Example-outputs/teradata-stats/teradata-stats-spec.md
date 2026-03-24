# Teradata Statistics Agent Specification

## Agent Overview

**Name:** `teradata-stats`  
**Color:** cyan  
**Model:** sonnet  
**Type:** Proactive monitoring and analysis agent

## Purpose

A specialized agent that monitors and analyzes Teradata database statistics health across all user-created databases. The agent identifies stale statistics, missing statistics, and generates actionable recommendations to maintain optimal query performance.

## Core Functionality

### 1. Statistics Health Monitoring
- **Stale Statistics Detection**
  - High-activity tables: Statistics older than 7 days
  - Low-activity tables: Statistics older than 30 days
  - Activity level determined by row change percentage and query frequency
  
- **Missing Statistics Detection**
  - Tables with no statistics collected
  - Indexes without statistics
  - Large tables (>1000 rows) that should have statistics

### 2. Scope & Coverage
- **Database Selection**
  - Scan all user-created databases
  - Exclude system databases: `DBC`, `SYSLIB`, `SYSUIF`, `SYSUDTLIB`, `SYSBAR`, `SystemFe`, `TDSTATS`, `TDQCD`
  - Configurable exclusion list for custom system databases
  
- **Statistics Focus**
  - Primary focus: Index statistics
  - Secondary: Column statistics on indexed columns
  - Track last collection date and row change metrics

### 3. Analysis & Prioritization
- **Activity Classification**
  - **High-activity**: Tables with >10% row changes or >100 queries in last 7 days
  - **Low-activity**: All other tables
  
- **Priority Ranking**
  - Priority 1 (Critical): High-activity tables with stale/missing stats
  - Priority 2 (Important): Large tables (>100K rows) with stale/missing stats
  - Priority 3 (Standard): Low-activity tables with stale/missing stats
  - Priority 4 (Optional): Small tables (<10K rows) with old stats

### 4. Actionable Output
The agent generates:
- **Executive Summary**
  - Total databases scanned
  - Total tables analyzed
  - Count of issues by priority
  - Estimated impact on performance
  
- **Detailed Findings**
  - Database and table names
  - Current statistics age
  - Row counts and change percentages
  - Last collection date
  - Activity level classification
  
- **Action Plan**
  - Ready-to-run `COLLECT STATISTICS` commands
  - Recommended execution order (by priority)
  - Estimated time/resource requirements
  - Batch grouping for large-scale collection

## Configuration File Structure

The agent uses a YAML configuration file (`teradata_stats_config.yml`) with the following parameters:

```yaml
# Staleness Thresholds (days)
staleness_thresholds:
  high_activity: 7
  low_activity: 30

# Activity Classification
activity_thresholds:
  row_change_percent: 10
  query_count_days: 7
  query_count_threshold: 100

# Database Exclusions
excluded_databases:
  - DBC
  - SYSLIB
  - SYSUIF
  - SYSUDTLIB
  - SYSBAR
  - SystemFe
  - TDSTATS
  - TDQCD
  # Add custom exclusions here

# Table Size Filters
table_filters:
  minimum_rows: 1000
  large_table_threshold: 100000
  small_table_threshold: 10000

# Reporting Limits
limits:
  max_tables_to_report: 500
  max_commands_per_batch: 50
  
# Statistics Focus
statistics_types:
  focus_on_indexes: true
  include_column_stats: false
  check_histogram_stats: false

# Output Preferences
output:
  generate_sql_commands: true
  include_execution_estimates: true
  group_by_priority: true
  summary_first: true
```

## Required MCP Tools

The agent will utilize the following teradataMCP tools:

### Core Tools
- `base_databaseList` - List all databases to scan
- `base_tableList` - Get tables within each database
- `base_columnDescription` - Get column and index information
- `base_tablePreview` - Get row counts and basic metrics
- `base_readQuery` - Execute custom SQL for statistics metadata

### DBA Tools
- `dba_tableSpace` - Get table size information
- `dba_tableSqlList` - Get query activity for activity classification
- `dba_tableUsageImpact` - Measure table usage patterns

## Workflow Steps

1. **Initialize Configuration**
   - Load or create default configuration file
   - Validate parameters

2. **Database Discovery**
   - Get list of all databases
   - Filter out excluded system databases

3. **Table Analysis** (per database)
   - Get all tables in database
   - For each table:
     - Check if statistics exist
     - Get last collection date
     - Calculate statistics age
     - Get row count and change metrics
     - Determine activity level
     - Assess priority level

4. **Issue Identification**
   - Classify issues: missing vs stale
   - Assign priority levels
   - Calculate performance impact

5. **Report Generation**
   - Executive summary
   - Detailed findings by priority
   - Generate COLLECT STATISTICS commands
   - Provide execution recommendations

6. **Output Delivery**
   - Display summary in chat
   - Optionally write detailed report to file
   - Provide copy-paste ready SQL commands

## Success Criteria

The agent is successful when it:
- ✅ Scans all user databases (excluding configured system databases)
- ✅ Correctly identifies stale statistics based on activity level
- ✅ Identifies tables with missing statistics
- ✅ Prioritizes issues appropriately
- ✅ Generates valid, executable COLLECT STATISTICS commands
- ✅ Provides clear, actionable recommendations
- ✅ Completes analysis within reasonable time (< 5 minutes for typical systems)

## Edge Cases & Error Handling

- **No Issues Found**: Report healthy state with summary statistics
- **Insufficient Permissions**: Clearly indicate which databases/tables couldn't be accessed
- **Large Systems**: Use pagination and batching to handle 1000+ tables
- **Configuration Errors**: Fall back to defaults with warnings
- **Query Failures**: Log errors but continue with remaining analysis

## Future Enhancements (Out of Scope for V1)

- Automatic statistics collection scheduling
- Historical trending of statistics health
- Machine learning-based activity prediction
- Integration with workload management
- Cost estimation for statistics collection
- Recommendations for sampled vs full statistics
