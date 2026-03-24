# teradataMCP Tools

A comprehensive reference of all available teradataMCP tools for working with Teradata databases.

## Base/Core Database Tools

### base_columnDescription
Get detailed column information for a table.

**Parameters:**
- `database_name` - Database name
- `obj_name` - Table or view name

### base_databaseList
List all databases in the Teradata system.

### base_readQuery
Execute SQL queries with bind parameters.

**Parameters:**
- `sql` - SQL text with optional bind-parameter placeholders

### base_tableAffinity
Get tables commonly used together (relationship inference).

**Parameters:**
- `database_name` - Database name
- `obj_name` - Table or view name

### base_tableDDL
Display DDL definition of a table.

**Parameters:**
- `database_name` - Database name
- `table_name` - Table name

### base_tableList
List all tables in a database.

**Parameters:**
- `database_name` - Database name

### base_tablePreview
Get data sample and inferred structure from a table.

**Parameters:**
- `table_name` - Table or view name
- `database_name` - Database name (optional)

### base_tableUsage
Measure table/view usage by users in a schema.

**Parameters:**
- `database_name` - Database name (optional)

---

## DBA (Database Administration) Tools

### dba_databaseSpace
Get database space allocations.

**Parameters:**
- `database_name` - Database name (returns all if null)

### dba_databaseVersion
Get Teradata database version information.

### dba_featureUsage
Get user feature usage metrics for a date range.

**Parameters:**
- `start_date` - Start date (format: YYYY-MM-DD)
- `end_date` - End date (format: YYYY-MM-DD)

### dba_flowControl
Get flow control metrics for a date range.

**Parameters:**
- `start_date` - Start date (format: YYYY-MM-DD)
- `end_date` - End date (format: YYYY-MM-DD)

### dba_resusageSummary
Get system resource usage summary by workload type and query complexity.

**Parameters:**
- `dimensions` - List of dimensions to aggregate: ["LogDate", "hourOfDay", "dayOfWeek", "workloadType", "workloadComplexity", "UserName", "AppId"]
- `user_name` - User name (optional)
- `date` - Date to analyze (format: YYYY-MM-DD) (optional)
- `dayOfWeek` - Day of the week (optional)
- `hourOfDay` - Hour of day (optional)
- `workloadType` - Workload type: 'LOAD', 'ETL/ELT', 'EXPORT', 'QUERY', 'ADMIN', 'OTHER' (optional)
- `workloadComplexity` - Workload complexity: 'Ingest & Prep', 'Answers', 'System/Procedural' (optional)
- `AppId` - Application ID: 'TPTLOAD%', 'TPTUPD%', 'FASTLOAD%', etc. (optional)

### dba_sessionInfo
Get session information for a user.

**Parameters:**
- `user_name` - User name

### dba_systemSpace
Get total system database space usage.

### dba_tableSpace
Get table space used for tables in a database.

**Parameters:**
- `database_name` - Database name (optional)
- `table_name` - Table name (optional)

### dba_tableSqlList
Get SQL queries run against a table in the last N days.

**Parameters:**
- `table_name` - Table name
- `no_days` - Number of days (default: 7)

### dba_tableUsageImpact
Measure table usage impact by users - understand what users and tables drive most resource usage.

**Parameters:**
- `database_name` - Database name (optional)
- `user_name` - User name (optional)

### dba_userDelay
Get user delay metrics for a date range.

**Parameters:**
- `start_date` - Start date (format: YYYY-MM-DD)
- `end_date` - End date (format: YYYY-MM-DD)

### dba_userSqlList
Get SQL queries run by a user in the last N days.

**Parameters:**
- `user_name` - User name
- `no_days` - Number of days (default: 7)

---

## Quality Analysis Tools

### qlty_columnSummary
Get column summary statistics for a table.

**Parameters:**
- `database_name` - Database name
- `table_name` - Table name

### qlty_distinctCategories
Get distinct categories from a column.

**Parameters:**
- `database_name` - Database name
- `table_name` - Table name
- `column_name` - Column name

### qlty_missingValues
Get columns with missing values in a table.

**Parameters:**
- `database_name` - Database name
- `table_name` - Table name

### qlty_negativeValues
Get columns with negative values in a table.

**Parameters:**
- `database_name` - Database name
- `table_name` - Table name

### qlty_rowsWithMissingValues
Get rows with missing values in a column.

**Parameters:**
- `database_name` - Database name
- `table_name` - Table name
- `column_name` - Column name

### qlty_standardDeviation
Get standard deviation for a column.

**Parameters:**
- `database_name` - Database name
- `table_name` - Table name
- `column_name` - Column name

### qlty_univariateStatistics
Get univariate statistics for a column.

**Parameters:**
- `database_name` - Database name
- `table_name` - Table name
- `column_name` - Column name

---

## Security Tools

### sec_rolePermissions
Get permissions for a role.

**Parameters:**
- `role_name` - Role name

### sec_userDbPermissions
Get database permissions for a user.

**Parameters:**
- `user_name` - User name

### sec_userRoles
Get roles assigned to a user.

**Parameters:**
- `user_name` - User name

---

## Vector Store (TDVS) Tools

### tdvs_ask
Ask questions using RAG from a vector store.

**Parameters:**
- `vs_name` - Vector store name
- `vs_ask` - VectorStoreAsk object containing:
  - `question` - The question to ask
  - `prompt` - Optional prompt to guide the response
  - `batch_data` - Optional table name for batch mode
  - `batch_id_column` - Optional ID column for batch mode
  - `batch_query_column` - Optional query column for batch mode

### tdvs_create
Create a new vector store.

**Parameters:**
- `vs_name` - Vector store name
- `vs_create` - VectorStoreCreate object with comprehensive configuration options

### tdvs_destroy
Delete a vector store.

**Parameters:**
- `vs_name` - Vector store name

### tdvs_get_details
Get details of a specific vector store.

**Parameters:**
- `vs_name` - Vector store name

### tdvs_get_health
Check health/status of vector store.

### tdvs_grant_user_permission
Grant user permissions to a vector store.

**Parameters:**
- `vs_name` - Vector store name
- `user_name` - User name
- `permission` - Permission type ('ADMIN' or 'USER')

### tdvs_list
List all vector stores with details.

### tdvs_revoke_user_permission
Revoke user permissions from a vector store.

**Parameters:**
- `vs_name` - Vector store name
- `user_name` - User name
- `permission` - Permission type ('ADMIN' or 'USER')

### tdvs_similarity_search
Perform similarity search in a vector store.

**Parameters:**
- `vs_name` - Vector store name
- `vs_similaritysearch` - VectorStoreSimilaritySearch object containing:
  - `question` - Text for similarity search
  - `batch_data` - Optional table name for batch mode
  - `batch_id_column` - Optional ID column for batch mode
  - `batch_query_column` - Optional query column for batch mode

### tdvs_update
Update an existing vector store.

**Parameters:**
- `vs_name` - Vector store name
- `vs_update` - VectorStoreUpdate object with configuration options

---

## SQL Optimization Tools

### sql_Analyze_Cluster_Stats
Analyze pre-computed SQL query cluster performance statistics to identify optimization opportunities.

**Parameters:**
- `sort_by_metric` - Metric to sort by: 'avg_cpu', 'avg_io', 'avg_cpuskw', 'avg_ioskw', 'avg_pji', 'avg_uii', 'avg_numsteps', 'queries', 'cluster_silhouette_score' (default: 'avg_cpu')
- `limit_results` - Limit number of results (optional)

**Use Cases:**
- Performance ranking by CPU, I/O, or complexity
- Skew problem detection
- Optimization prioritization

### sql_Execute_Full_Pipeline
Execute complete SQL query clustering pipeline for high-usage query optimization.

**Parameters:**
- `max_queries` - Maximum number of queries to analyze (optional)
- `optimal_k` - Number of clusters to create (optional)

**Pipeline Steps:**
1. Query log extraction from DBC.DBQLSqlTbl
2. Performance metrics calculation
3. Query tokenization and embedding generation
4. K-Means clustering
5. Silhouette analysis
6. Statistics generation

### sql_Retrieve_Cluster_Queries
Retrieve actual SQL queries from specific clusters for pattern analysis.

**Parameters:**
- `cluster_ids` - List of cluster IDs to retrieve
- `metric` - Metric to sort by: 'ampcputime', 'logicalio', 'cpuskw', 'ioskw', 'pji', 'uii', 'numsteps', 'response_secs', 'delaytime' (default: 'ampcputime')
- `limit_per_cluster` - Limit queries per cluster (default: 250)

**Use Cases:**
- SQL pattern recognition
- Performance correlation
- Optimization identification

---

## RAG (Retrieval-Augmented Generation) Tools

### rag_Execute_Workflow
Execute complete RAG workflow to answer questions based on document context.

**Parameters:**
- `question` - User question (automatically strips '/rag ' prefix if present)
- `k` - Number of top chunks to retrieve (optional)

**Workflow:**
1. Configuration setup from rag_config.yml
2. Query storage
3. Generate query embeddings (BYOM or IVSM)
4. Semantic search against precomputed embeddings
5. Return context chunks for answer generation

**Critical Rules:**
- Answer only using retrieved chunks
- Quote source content directly
- Include document/page references when available
- No paraphrasing or inference

---

## Feature Store Tools

### fs_createDataset
Create a dataset using selected features and entity.

**Parameters:**
- `entity_name` - Entity for dataset creation
- `feature_selection` - List of features to include
- `dataset_name` - Name of the dataset
- `target_database` - Database where dataset will be created

### fs_featureStoreContent
Get summary of feature store content.

### fs_getAvailableDatasets
List available datasets.

### fs_getAvailableEntities
List available entities for a data domain.

### fs_getDataDomains
List available data domains.

### fs_getFeatureDataModel
Get feature store data model including feature catalog, process catalog, and dataset catalog.

### fs_getFeatures
List available features.

### fs_isFeatureStorePresent
Check if feature store exists in a database.

**Parameters:**
- `database_name` - Database name to check

---

## Plotting/Visualization Tools

### plot_line_chart
Generate line plots.

**Parameters:**
- `table_name` - Table name
- `labels` - Labels column (x-axis)
- `columns` - Column(s) for y-axis

### plot_pie_chart
Generate pie charts.

**Parameters:**
- `table_name` - Table name
- `labels` - Labels column
- `column` - Column to plot

### plot_polar_chart
Generate polar area plots.

**Parameters:**
- `table_name` - Table name
- `labels` - Labels column
- `column` - Column to plot

### plot_radar_chart
Generate radar plots.

**Parameters:**
- `table_name` - Table name
- `labels` - Labels column
- `columns` - Column(s) to plot

---

## Notes

- All database-related tools work with Teradata databases via the teradataMCP server
- Tools use SQLAlchemy for database operations
- Many tools support optional parameters for flexible querying
- Performance metrics and statistics are calculated using Teradata system tables (DBC.DBQLSqlTbl, DBC.DBQLogTbl)
- Vector store tools support both BYOM (Bring Your Own Model) and IVSM (In-Vantage Scoring Model) approaches
