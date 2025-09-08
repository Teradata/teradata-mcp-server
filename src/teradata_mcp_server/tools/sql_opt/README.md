# SQL Optimization Tools

**Dependencies**

- Access to **DBC.DBQLSqlTbl** and **DBC.DBQLOgTbl**  
- Embedding models and tokenizers available in the configured database  

---

**Tools:**

- **sql_Execute_Full_Pipeline**  
  Runs the complete SQL query clustering workflow end-to-end:
  - Query log extraction  
  - Tokenization & embeddings  
  - Vector store creation  
  - KMeans clustering  
  - Silhouette scoring  
  - Cluster statistics generation  

- **sql_Analyze_Cluster_Stats**  
  Analyzes pre-computed cluster statistics:  
  - Sorts/ranks clusters by CPU, I/O, skew, steps, or silhouette score  
  - Categorizes clusters (HIGH_CPU, HIGH_IO, HIGH_SKEW, NORMAL)  
  - Returns performance metadata and summary statistics  

- **sql_Retrieve_Cluster_Queries**  
  Retrieves raw SQL from selected clusters:  
  - Ranks queries by CPU, I/O, skew, complexity, or response time  
  - Categorizes queries using thresholds (CPU usage, skew levels)  
  - Provides context (user, app, workload, metrics) for optimization analysis  

---

**Configuration**

All settings are managed in **`sql_opt_config.yml`**.  
You can adjust:  

- Database and table locations  
- Model identifiers and embedding parameters  
- Clustering parameters (e.g., K, iterations, thresholds)  
- Performance thresholds for CPU, I/O, and skew categorization  

---

**Workflow**

1. Run **sql_Execute_Full_Pipeline** to generate clusters and statistics.  
2. Use **sql_Analyze_Cluster_Stats** to identify problematic clusters.  
3. Call **sql_Retrieve_Cluster_Queries** to inspect raw SQL and plan optimization actions.  

---

**Use Cases**

- Identify query families consuming the most system resources  
- Detect skew/distribution issues  
- Prioritize DBA optimization efforts  
- Retrieve and analyze problematic queries for rewrites or indexing  
- Provide LLMs with structured cluster/query data for recommendations  

---

[Return to Main README](../../../../README.md)
