##################################################################################
# SQL Clustering Optimization Tools
##################################################################################
 
import logging
import yaml
from typing import Optional, Any, Dict, List
import json
from datetime import date, datetime
from decimal import Decimal
from teradatasql import TeradataConnection
from pathlib import Path

logger = logging.getLogger("teradata_mcp_server")


def serialize_teradata_types(obj: Any) -> Any:
    """Convert Teradata-specific types to JSON serializable formats"""
    if isinstance(obj, date | datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)

def rows_to_json(cursor_description: Any, rows: list[Any]) -> list[dict[str, Any]]:
    """Convert database rows to JSON objects using column names as keys"""
    if not cursor_description or not rows:
        return []

    columns = [col[0] for col in cursor_description]
    return [
        {
            col: serialize_teradata_types(value)
            for col, value in zip(columns, row)
        }
        for row in rows
    ]

def create_response(data: Any, metadata: dict[str, Any] | None = None) -> str:
    """Create a standardized JSON response structure"""
    if metadata:
        response = {
            "status": "success",
            "metadata": metadata,
            "results": data
        }
    else:
        response = {
            "status": "success",
            "results": data
        }

    return json.dumps(response, default=serialize_teradata_types)


# Load SQL Clustering configuration
def load_sql_clustering_config():
    """Load SQL clustering configuration from sql_opt_config.yml"""
    try:
        # Get the directory path
        current_dir = Path(__file__).parent
        # Go to config/
        config_path = current_dir.parent.parent / 'config' / 'sql_opt_config.yml'
        
        with open(config_path, 'r') as file:
            logger.info(f"Loading SQL clustering config from: {config_path}")
            return yaml.safe_load(file)
    except FileNotFoundError:
        logger.warning(f"SQL clustering config file not found: {config_path}, using defaults")
        return get_default_sql_clustering_config()
    except Exception as e:
        logger.error(f"Error loading SQL clustering config: {e}")
        return get_default_sql_clustering_config()

def get_default_sql_clustering_config():
    """Default SQL clustering configuration as fallback"""
    return {
        'version': 'ivsm',
        'databases': {
            'feature_db': 'feature_ext_db',
            'model_db': 'feature_ext_db'
        },
        'tables': {
            'sql_query_log_main': 'sql_query_log_main',
            'sql_log_tokenized_for_embeddings': 'sql_log_tokenized_for_embeddings',
            'sql_log_embeddings': 'sql_log_embeddings',
            'sql_log_embeddings_store': 'sql_log_embeddings_store',
            'sql_query_clusters_temp': 'sql_query_clusters_temp',
            'sql_query_clusters': 'sql_query_clusters',
            'query_cluster_stats': 'query_cluster_stats',
            'embedding_models': 'embedding_models',
            'embedding_tokenizers': 'embedding_tokenizers'
        },
        'model': {
            'model_id': 'bge-small-en-v1.5'
        },
        'clustering': {
            'optimal_k': 14,
            'max_queries': 10000,
            'seed': 10,
            'stop_threshold': 0.0395,
            'max_iterations': 100
        },
        'embedding': {
            'vector_length': 384,
            'max_length': 1024,
            'pad_to_max_length': 'False'
        }
    }

# Load config
SQL_CLUSTERING_CONFIG = load_sql_clustering_config()

def handle_sql_Execute_Full_Pipeline(
    conn,
    optimal_k: int = None,
    max_queries: int = None,
    *args,
    **kwargs
):
    """
        **COMPLETE SQL QUERY CLUSTERING PIPELINE FOR HIGH-USAGE QUERY OPTIMIZATION**

        This tool executes the entire SQL query clustering workflow to identify and analyze high CPU usage queries for optimization opportunities. It's designed for database performance analysts and DBAs who need to systematically identify query optimization candidates.

        **FULL PIPELINE WORKFLOW:**
        1. **Query Log Extraction**: Extracts SQL queries from DBC.DBQLSqlTbl with comprehensive performance metrics
        2. **Performance Metrics Calculation**: Computes CPU skew, I/O skew, PJI (Physical to Logical I/O ratio), UII (Unit I/O Intensity)
        3. **Query Tokenization**: Tokenizes SQL text using {sql_clustering_config.get('model', {}).get('model_id', 'bge-small-en-v1.5')} tokenizer via ivsm.tokenizer_encode
        4. **Embedding Generation**: Creates semantic embeddings using ivsm.IVSM_score with ONNX models
        5. **Vector Store Creation**: Converts embeddings to vector columns via ivsm.vector_to_columns
        6. **K-Means Clustering**: Groups similar queries using TD_KMeans with optimal K from configuration
        7. **Silhouette Analysis**: Calculates clustering quality scores using TD_Silhouette
        8. **Statistics Generation**: Creates comprehensive cluster statistics with performance aggregations

        **PERFORMANCE METRICS EXPLAINED:**
        - **AMPCPUTIME**: Total CPU seconds across all AMPs (primary optimization target)
        - **CPUSKW/IOSKW**: CPU/I/O skew ratios (>2.0 indicates distribution problems)
        - **PJI**: Physical-to-Logical I/O ratio (higher = more CPU-intensive)
        - **UII**: Unit I/O Intensity (higher = more I/O-intensive relative to CPU)
        - **LogicalIO**: Total logical I/O operations (indicates scan intensity)
        - **NumSteps**: Query plan complexity (higher = more complex plans)

        **CONFIGURATION (from sql_opt_config.yml):**
        - Uses top {default_max_queries} queries by CPU time (configurable)
        - Creates {default_optimal_k} clusters by default (configurable via optimal_k parameter)
        - Embedding model: {sql_clustering_config.get('model', {}).get('model_id', 'bge-small-en-v1.5')}
        - Vector dimensions: {sql_clustering_config.get('embedding', {}).get('vector_length', 384)}
        - All database and table names are configurable

        **OPTIMIZATION WORKFLOW:**
        After running this tool, use:
        1. sql_Analyze_Cluster_Stats to identify problematic clusters
        2. sql_Retrieve_Cluster_Queries to get actual SQL from target clusters
        3. LLM analysis to identify patterns and propose specific optimizations

        **USE CASES:**
        - Identify query families consuming the most system resources
        - Find queries with similar patterns but different performance
        - Discover optimization opportunities through clustering analysis
        - Prioritize DBA effort on highest-impact query improvements
        - Understand workload composition and resource distribution

        **PREREQUISITES:**
        - DBC.DBQLSqlTbl and DBC.DBQLOgTbl must be accessible
        - Embedding models and tokenizers must be installed in feature_ext_db
        - Sufficient space in feature_ext_db for intermediate and final tables
        """
    
    config = SQL_CLUSTERING_CONFIG
    
    # Use config defaults if not provided
    if optimal_k is None:
        optimal_k = config['clustering']['optimal_k']
    if max_queries is None:
        max_queries = config['clustering']['max_queries']
    
    logger.debug(f"handle_sql_Execute_Full_Pipeline: optimal_k={optimal_k}, max_queries={max_queries}")
    
    # Extract config values
    feature_db = config['databases']['feature_db']
    model_db = config['databases']['model_db']
    model_id = config['model']['model_id']
    
    tables = config['tables']
    embedding_config = config['embedding']
    clustering_config = config['clustering']

    with conn.cursor() as cur:
        
        # Create main SQL query log table
        logger.debug(f"Step 1: Creating main query log table {feature_db}.{tables['sql_query_log_main']}")
        
        try:
            cur.execute(f"DROP TABLE {feature_db}.{tables['sql_query_log_main']}")
            logger.debug(f"Dropped existing table {feature_db}.{tables['sql_query_log_main']}")
        except Exception as e:
            logger.debug(f"DROP failed or table not found: {e}")

        main_query_sql = f"""
        CREATE TABLE {feature_db}.{tables['sql_query_log_main']} AS (
            SELECT 
                CAST(a.QueryID AS BIGINT) AS id,
                a.SQLTextInfo AS txt,
                b.username,
                b.appid,
                b.numsteps,
                b.ampcputime,
                b.TotalIOCount AS logicalio,
                b.wdname,
                CASE WHEN b.ampcputime < HashAmp()+1 OR (b.ampcputime / (HashAmp()+1)) = 0 
                     THEN 0 ELSE b.maxampcputime/(b.ampcputime / (HashAmp()+1)) END (DEC(8,2)) AS CPUSKW,
                CASE WHEN b.ampcputime < HashAmp()+1 OR (b.TotalIOCount / (HashAmp()+1)) = 0 
                     THEN 0 ELSE b.maxampio/(b.TotalIOCount / (HashAmp()+1)) END (DEC(8,2)) AS IOSKW,
                CASE WHEN b.ampcputime < HashAmp()+1 OR b.TotalIOCount = 0 
                     THEN 0 ELSE (b.ampcputime * 1000)/b.TotalIOCount END AS PJI,
                CASE WHEN b.ampcputime < HashAmp()+1 OR b.ampcputime = 0 
                     THEN 0 ELSE b.TotalIOCount/(b.ampcputime * 1000) END AS UII,
                CAST(EXTRACT(HOUR FROM ((b.FirstRespTime - b.StartTime) HOUR(3) TO SECOND(6))) * 3600
                     + EXTRACT(MINUTE FROM ((b.FirstRespTime - b.StartTime) HOUR(3) TO SECOND(6))) * 60
                     + EXTRACT(SECOND FROM ((b.FirstRespTime - b.StartTime) HOUR(3) TO SECOND(6))) AS DECIMAL(10,2)) AS response_secs,
                (CAST(EXTRACT(HOUR FROM ((b.FirstRespTime - b.StartTime) HOUR(3) TO SECOND(6))) * 3600
                     + EXTRACT(MINUTE FROM ((b.FirstRespTime - b.StartTime) HOUR(3) TO SECOND(6))) * 60
                     + EXTRACT(SECOND FROM ((b.FirstRespTime - b.StartTime) HOUR(3) TO SECOND(6))) AS DECIMAL(10,2)))/60.0 AS response_mins,
                CASE WHEN b.delaytime IS NULL THEN 0.0 ELSE b.delaytime END AS delaytime
            FROM DBC.DBQLSqlTbl a 
            JOIN (
                -- OPTIMIZATION: Filter to top queries by CPU BEFORE joining
                SELECT * FROM DBC.DBQLOgTbl 
                WHERE LOWER(statementtype) IN ('select','create table')
                QUALIFY ROW_NUMBER() OVER (ORDER BY ampcputime DESC) <= {max_queries}
            ) b ON a.queryid = b.queryid AND a.procid = b.procid
            WHERE
                a.SQLTextInfo NOT LIKE '%SET QUERY_BAND%' AND
                a.SQLTextInfo NOT LIKE '%ParamValue%' AND
                a.SQLTextInfo NOT LIKE '%SELECT CURRENT_TIMESTAMP%' AND
                LOWER(a.SQLTextInfo) NOT LIKE '%dbc.%' AND 
                a.SqlRowNo = 1
        ) WITH DATA
        """
        
        cur.execute(main_query_sql)
        logger.debug(f"Created main query log table")

        # Create tokenized table for embeddings
        logger.debug(f"Step 2: Creating tokenized table {feature_db}.{tables['sql_log_tokenized_for_embeddings']}")
        
        try:
            cur.execute(f"DROP TABLE {feature_db}.{tables['sql_log_tokenized_for_embeddings']}")
        except Exception as e:
            logger.debug(f"DROP failed or table not found: {e}")

        tokenize_sql = f"""
        CREATE TABLE {feature_db}.{tables['sql_log_tokenized_for_embeddings']} AS (
            SELECT
                id,
                txt,
                IDS AS input_ids,
                attention_mask
            FROM ivsm.tokenizer_encode(
                ON (SELECT * FROM {feature_db}.{tables['sql_query_log_main']})
                ON (SELECT model AS tokenizer FROM {model_db}.{tables['embedding_tokenizers']} 
                    WHERE model_id = '{model_id}') DIMENSION
                USING
                    ColumnsToPreserve('id', 'txt')
                    OutputFields('IDS', 'ATTENTION_MASK')
                    MaxLength({embedding_config['max_length']})
                    PadToMaxLength('{embedding_config['pad_to_max_length']}')
                    TokenDataType('INT64')
            ) AS dt
        ) WITH DATA
        """
        
        cur.execute(tokenize_sql)
        logger.debug(f"Created tokenized table")

        # Create embeddings table
        logger.debug(f"Step 3: Creating embeddings table {feature_db}.{tables['sql_log_embeddings']}")
        
        try:
            cur.execute(f"DROP TABLE {feature_db}.{tables['sql_log_embeddings']}")
        except Exception as e:
            logger.debug(f"DROP failed or table not found: {e}")

        embeddings_sql = f"""
        CREATE TABLE {feature_db}.{tables['sql_log_embeddings']} AS (
            SELECT *
            FROM ivsm.IVSM_score(
                ON {feature_db}.{tables['sql_log_tokenized_for_embeddings']}
                ON (SELECT * FROM {model_db}.{tables['embedding_models']} 
                    WHERE model_id = '{model_id}') DIMENSION
                USING
                    ColumnsToPreserve('id', 'txt')
                    ModelType('ONNX')
                    BinaryInputFields('input_ids', 'attention_mask')
                    BinaryOutputFields('sentence_embedding')
                    Caching('inquery')
            ) a
        ) WITH DATA
        """
        
        cur.execute(embeddings_sql)
        logger.debug(f"Created embeddings table")

        # Create embeddings store table
        logger.debug(f"Step 4: Creating embeddings store table {feature_db}.{tables['sql_log_embeddings_store']}")
        
        try:
            cur.execute(f"DROP TABLE {feature_db}.{tables['sql_log_embeddings_store']}")
        except Exception as e:
            logger.debug(f"DROP failed or table not found: {e}")

        embeddings_store_sql = f"""
        CREATE TABLE {feature_db}.{tables['sql_log_embeddings_store']} AS (
            SELECT *
            FROM ivsm.vector_to_columns(
                ON {feature_db}.{tables['sql_log_embeddings']}
                USING
                    ColumnsToPreserve('id', 'txt')
                    VectorDataType('FLOAT32')
                    VectorLength({embedding_config['vector_length']})
                    OutputColumnPrefix('emb_')
                    InputColumnName('sentence_embedding')
            ) a
        ) WITH DATA
        """
        
        cur.execute(embeddings_store_sql)
        logger.debug(f"Created embeddings store table")

        # Perform K-means clustering
        logger.debug(f"Step 5: Performing K-means clustering with k={optimal_k}")
        
        try:
            cur.execute(f"DROP TABLE {feature_db}.{tables['sql_query_clusters_temp']}")
        except Exception as e:
            logger.debug(f"DROP failed or table not found: {e}")

        kmeans_sql = f"""
        CREATE TABLE {feature_db}.{tables['sql_query_clusters_temp']} AS (
            SELECT td_clusterid_kmeans, a.*
            FROM TD_KMeans (
                ON {feature_db}.{tables['sql_log_embeddings_store']} AS InputTable
                USING
                    IdColumn('id')
                    TargetColumns('[2:385]')
                    NumClusters({optimal_k})
                    Seed({clustering_config['seed']})
                    StopThreshold({clustering_config['stop_threshold']})
                    OutputClusterAssignment('true')
                    MaxIterNum({clustering_config['max_iterations']})
            ) AS dt
            JOIN {feature_db}.{tables['sql_query_log_main']} a ON a.id = dt.id
        ) WITH DATA
        """
        
        cur.execute(kmeans_sql)
        logger.debug(f"Created temporary clusters table")

        # Create final clusters table with silhouette scores
        logger.debug(f"Step 6: Creating final clusters table with silhouette scores")
        
        try:
            cur.execute(f"DROP TABLE {feature_db}.{tables['sql_query_clusters']}")
        except Exception as e:
            logger.debug(f"DROP failed or table not found: {e}")

        final_clusters_sql = f"""
        CREATE TABLE {feature_db}.{tables['sql_query_clusters']} AS (
            SELECT a.*, b.silhouette_score 
            FROM {feature_db}.{tables['sql_query_clusters_temp']} a
            JOIN (SELECT * FROM TD_Silhouette(
                ON (SELECT td_clusterid_kmeans, b.* 
                    FROM {feature_db}.{tables['sql_query_clusters_temp']} a 
                    JOIN {feature_db}.{tables['sql_log_embeddings_store']} b
                    ON a.id = b.id) AS InputTable
                USING
                    IdColumn('id')
                    ClusterIdColumn('td_clusterid_kmeans')
                    TargetColumns('[4:]')
                    OutputType('SAMPLE_SCORES')
            ) AS dt) AS b
            ON a.id = b.id
        ) WITH DATA PRIMARY INDEX(id)
        """
        
        cur.execute(final_clusters_sql)
        logger.debug(f"Created final clusters table")

        # Create cluster statistics table
        logger.debug(f"Step 7: Creating cluster statistics table")
        
        try:
            cur.execute(f"DROP TABLE {feature_db}.{tables['query_cluster_stats']}")
        except Exception as e:
            logger.debug(f"DROP failed or table not found: {e}")

        cluster_stats_sql = f"""
        CREATE TABLE {feature_db}.{tables['query_cluster_stats']} AS (
            SELECT a.td_clusterid_kmeans,
                AVG(a.numsteps) AS avg_numsteps, 
                VAR_SAMP(a.numsteps) AS var_numsteps,
                AVG(a.ampcputime) AS avg_cpu, 
                VAR_SAMP(a.ampcputime) AS var_cpu,
                AVG(a.logicalio) AS avg_io, 
                VAR_SAMP(a.logicalio) AS var_io,
                AVG(a.cpuskw) AS avg_cpuskw, 
                VAR_SAMP(a.cpuskw) AS var_cpuskw,
                AVG(a.ioskw) AS avg_ioskw, 
                VAR_SAMP(a.ioskw) AS var_ioskw,
                AVG(a.pji) AS avg_pji, 
                VAR_SAMP(a.pji) AS var_pji,
                AVG(a.uii) AS avg_uii, 
                VAR_SAMP(a.uii) AS var_uii,
                MAX(un.top_username) AS top_username,
                MAX(top_wdname) AS top_wdname,
                MAX(top_appid) AS top_appid,
                MAX(s1.silhouette_score) AS overall_silhouette_score,
                MAX(s2.silhouette_score) AS cluster_silhouette_score,
                COUNT(*) AS queries
            FROM {feature_db}.{tables['sql_query_clusters']} a 
            JOIN (
                SELECT td_clusterid_kmeans, 
                       username AS top_UserName
                FROM {feature_db}.{tables['sql_query_clusters']}
                GROUP BY td_clusterid_kmeans, username
                QUALIFY ROW_NUMBER() OVER (PARTITION BY td_clusterid_kmeans ORDER BY COUNT(*) DESC) = 1
            ) un ON a.td_clusterid_kmeans = un.td_clusterid_kmeans
            JOIN (
                SELECT td_clusterid_kmeans, 
                       wdname AS top_wdname
                FROM {feature_db}.{tables['sql_query_clusters']}
                GROUP BY td_clusterid_kmeans, wdname
                QUALIFY ROW_NUMBER() OVER (PARTITION BY td_clusterid_kmeans ORDER BY COUNT(*) DESC) = 1
            ) wd ON un.td_clusterid_kmeans = wd.td_clusterid_kmeans
            JOIN (
                SELECT td_clusterid_kmeans, 
                       appid AS top_AppId
                FROM {feature_db}.{tables['sql_query_clusters']}
                GROUP BY td_clusterid_kmeans, appid
                QUALIFY ROW_NUMBER() OVER (PARTITION BY td_clusterid_kmeans ORDER BY COUNT(*) DESC) = 1
            ) ap ON un.td_clusterid_kmeans = ap.td_clusterid_kmeans
            CROSS JOIN (
                SELECT * FROM TD_Silhouette(
                    ON (SELECT td_clusterid_kmeans, b.* 
                        FROM {feature_db}.{tables['sql_query_clusters']} a 
                        JOIN {feature_db}.{tables['sql_log_embeddings_store']} b
                        ON a.id = b.id) AS InputTable
                    USING
                        IdColumn('id')
                        ClusterIdColumn('td_clusterid_kmeans')
                        TargetColumns('[4:]')
                        OutputType('SCORE')
                ) AS dt
            ) AS s1
            JOIN (
                SELECT * FROM TD_Silhouette(
                    ON (SELECT td_clusterid_kmeans, b.* 
                        FROM {feature_db}.{tables['sql_query_clusters']} a 
                        JOIN {feature_db}.{tables['sql_log_embeddings_store']} b
                        ON a.id = b.id) AS InputTable
                    USING
                        IdColumn('id')
                        ClusterIdColumn('td_clusterid_kmeans')
                        TargetColumns('[4:]')
                        OutputType('CLUSTER_SCORES')
                ) AS dt
            ) s2 ON a.td_clusterid_kmeans = s2.td_clusterid_kmeans
            GROUP BY a.td_clusterid_kmeans
        ) WITH DATA PRIMARY INDEX(td_clusterid_kmeans)
        """
        
        cur.execute(cluster_stats_sql)
        logger.debug(f"Created cluster statistics table")

        # Get final results
        cur.execute(f"SELECT COUNT(*) FROM {feature_db}.{tables['sql_query_clusters']}")
        total_queries = cur.fetchone()[0]
        
        cur.execute(f"SELECT COUNT(DISTINCT td_clusterid_kmeans) FROM {feature_db}.{tables['sql_query_clusters']}")
        total_clusters = cur.fetchone()[0]
        
        cur.execute(f"SELECT AVG(silhouette_score) FROM {feature_db}.{tables['sql_query_clusters']}")
        avg_silhouette = cur.fetchone()[0]

    # Return metadata
    metadata = {
        "tool_name": "sql_Execute_Full_Pipeline",
        "workflow_steps": [
            "query_log_extracted", "queries_tokenized", "embeddings_generated", 
            "embeddings_stored", "kmeans_clustering_completed", "silhouette_scores_calculated", 
            "cluster_statistics_generated"
        ],
        "configuration": {
            "optimal_k": optimal_k,
            "max_queries_processed": max_queries,
            "model_id": model_id,
            "clustering_parameters": clustering_config,
            "embedding_parameters": embedding_config
        },
        "results": {
            "total_queries_clustered": total_queries,
            "total_clusters_created": total_clusters,
            "average_silhouette_score": float(avg_silhouette) if avg_silhouette else None
        },
        "tables_created": [
            f"{feature_db}.{tables['sql_query_log_main']}",
            f"{feature_db}.{tables['sql_log_tokenized_for_embeddings']}",
            f"{feature_db}.{tables['sql_log_embeddings']}",
            f"{feature_db}.{tables['sql_log_embeddings_store']}",
            f"{feature_db}.{tables['sql_query_clusters']}",
            f"{feature_db}.{tables['query_cluster_stats']}"
        ],
        "description": "Complete SQL query clustering pipeline executed: extracted SQL logs → tokenized → embedded → clustered → analyzed"
    }

    return create_response({"status": "success", "pipeline_completed": True}, metadata)


def handle_sql_Analyze_Cluster_Stats(
    conn,
    sort_by_metric: str = "avg_cpu",
    limit_results: int = None,
    *args,
    **kwargs
):
    """
        **ANALYZE SQL QUERY CLUSTER PERFORMANCE STATISTICS**

        This tool analyzes pre-computed cluster statistics to identify optimization opportunities without re-running the clustering pipeline. Perfect for iterative analysis and decision-making on which query clusters to focus optimization efforts.

        **ANALYSIS CAPABILITIES:**
        - **Performance Ranking**: Sort clusters by any performance metric to identify top resource consumers
        - **Resource Impact Assessment**: Compare clusters by CPU usage, I/O volume, and execution complexity
        - **Skew Problem Detection**: Identify clusters with CPU or I/O distribution issues
        - **Workload Characterization**: Understand query patterns by user, application, and workload type
        - **Optimization Prioritization**: Focus on clusters with highest impact potential

        **AVAILABLE SORTING METRICS:**
        - **avg_cpu**: Average CPU seconds per cluster (primary optimization target)
        - **avg_io**: Average logical I/O operations (scan intensity indicator)
        - **avg_cpuskw**: Average CPU skew (distribution problem indicator)
        - **avg_ioskw**: Average I/O skew (hot spot indicator)
        - **avg_pji**: Average Physical-to-Logical I/O ratio (compute intensity)
        - **avg_uii**: Average Unit I/O Intensity (I/O efficiency)
        - **avg_numsteps**: Average query plan complexity
        - **queries**: Number of queries in cluster (frequency indicator)
        - **cluster_silhouette_score**: Clustering quality measure

        **PERFORMANCE CATEGORIZATION:**
        Automatically categorizes clusters using configurable thresholds (from sql_opt_config.yml):
        - **HIGH_CPU_USAGE**: Average CPU > config.performance_thresholds.cpu.high
        - **HIGH_IO_USAGE**: Average I/O > config.performance_thresholds.io.high
        - **HIGH_CPU_SKEW**: CPU skew > config.performance_thresholds.skew.high
        - **HIGH_IO_SKEW**: I/O skew > config.performance_thresholds.skew.high
        - **NORMAL**: Clusters within configured normal performance ranges

        **TYPICAL ANALYSIS WORKFLOW:**
        1. Sort by 'avg_cpu' or 'avg_io' to find highest resource consumers
        2. Sort by 'avg_cpuskw' or 'avg_ioskw' to find distribution problems
        4. Use limit_results to focus on top problematic clusters

        **OPTIMIZATION DECISION FRAMEWORK:**
        - **High CPU + High Query Count**: Maximum impact optimization candidates
        - **High Skew + Moderate CPU**: Distribution/statistics problems
        - **High I/O + Low PJI**: Potential indexing opportunities
        - **High NumSteps**: Complex query rewriting candidates

        **OUTPUT FORMAT:**
        Returns detailed cluster statistics with performance rankings, categories, and metadata for LLM analysis and optimization recommendations.
        """
    
    config = SQL_CLUSTERING_CONFIG
    
    logger.debug(f"handle_sql_Analyze_Cluster_Stats: sort_by={sort_by_metric}, limit={limit_results}")
    
    feature_db = config['databases']['feature_db']
    stats_table = config['tables']['query_cluster_stats']
    
    # Validate sort metric
    valid_metrics = [
        'avg_cpu', 'avg_io', 'avg_cpuskw', 'avg_ioskw', 'avg_pji', 'avg_uii',
        'avg_numsteps', 'queries', 'cluster_silhouette_score'
    ]
    
    if sort_by_metric not in valid_metrics:
        sort_by_metric = 'avg_cpu'  # Default fallback

    with conn.cursor() as cur:
        
        # Build the query with optional limit
        limit_clause = f"TOP {limit_results}" if limit_results else ""
        
        # Get thresholds from config
        thresholds = config.get('performance_thresholds', {})
        cpu_high = thresholds.get('cpu', {}).get('high', 100)
        skew_high = thresholds.get('skew', {}).get('high', 3.0)
        io_high = thresholds.get('io', {}).get('high', 1000000)

        stats_query = f"""
        SELECT {limit_clause}
            td_clusterid_kmeans,
            avg_numsteps, 
            var_numsteps,
            avg_cpu, 
            var_cpu,
            avg_io, 
            var_io,
            avg_cpuskw, 
            var_cpuskw,
            avg_ioskw, 
            var_ioskw,
            avg_pji, 
            var_pji,
            avg_uii, 
            var_uii,
            top_username,
            top_wdname,
            top_appid,
            overall_silhouette_score,
            cluster_silhouette_score,
            queries,
            -- Additional analysis columns with configurable thresholds
            CASE 
                WHEN avg_cpuskw > {skew_high} THEN 'HIGH_CPU_SKEW'
                WHEN avg_ioskw > {skew_high} THEN 'HIGH_IO_SKEW'
                WHEN avg_cpu > {cpu_high} THEN 'HIGH_CPU_USAGE'
                WHEN avg_io > {io_high} THEN 'HIGH_IO_USAGE'
                ELSE 'NORMAL'
            END AS performance_category,
            RANK() OVER (ORDER BY {sort_by_metric} DESC) AS performance_rank
        FROM {feature_db}.{stats_table}
        ORDER BY {sort_by_metric} DESC
        """
        
        cur.execute(stats_query)
        data = rows_to_json(cur.description, cur.fetchall())
        
        # Get summary statistics
        cur.execute(f"""
        SELECT 
            COUNT(*) AS total_clusters,
            AVG(avg_cpu) AS system_avg_cpu,
            AVG(avg_io) AS system_avg_io,
            AVG(queries) AS avg_queries_per_cluster,
            MAX(avg_cpu) AS max_cluster_cpu,
            MIN(cluster_silhouette_score) AS min_silhouette_score
        FROM {feature_db}.{stats_table}
        """)
        
        summary_stats = rows_to_json(cur.description, cur.fetchall())[0]
        
        logger.debug(f"Retrieved {len(data)} cluster statistics")

    # Return results with metadata
    metadata = {
        "tool_name": "sql_Analyze_Cluster_Stats",
        "analysis_parameters": {
            "sort_by_metric": sort_by_metric,
            "limit_results": limit_results,
            "valid_metrics": valid_metrics
        },
        "summary_statistics": summary_stats,
        "clusters_analyzed": len(data),
        "table_source": f"{feature_db}.{stats_table}",
        "description": f"Cluster statistics analysis sorted by {sort_by_metric} - ready for LLM optimization recommendations"
    }

    return create_response(data, metadata)


def handle_sql_Retrieve_Cluster_Queries(
    conn,
    cluster_ids: List[int],
    metric: str = "ampcputime",
    limit_per_cluster: int = 250,
    *args,
    **kwargs
):
    """
        **RETRIEVE ACTUAL SQL QUERIES FROM SPECIFIC CLUSTERS FOR PATTERN ANALYSIS**

        This tool extracts the actual SQL query text and performance metrics from selected clusters, enabling detailed pattern analysis and specific optimization recommendations. Essential for moving from cluster-level analysis to actual query optimization.

        **DETAILED ANALYSIS CAPABILITIES:**
        - **SQL Pattern Recognition**: Analyze actual query structures, joins, predicates, and functions
        - **Performance Correlation**: Connect query patterns to specific performance characteristics
        - **Optimization Identification**: Identify common anti-patterns, missing indexes, inefficient joins
        - **Code Quality Assessment**: Evaluate query construction, complexity, and best practices
        - **Workload Understanding**: See actual business logic and data access patterns

        **QUERY SELECTION STRATEGIES:**
        - **By CPU Impact**: Sort by 'ampcputime' to focus on highest CPU consumers
        - **By I/O Volume**: Sort by 'logicalio' to find scan-intensive queries
        - **By Skew Problems**: Sort by 'cpuskw' or 'ioskw' for distribution issues
        - **By Complexity**: Sort by 'numsteps' for complex execution plans
        - **By Response Time**: Sort by 'response_secs' for user experience impact

        **AVAILABLE METRICS FOR SORTING:**
        - **ampcputime**: Total CPU seconds (primary optimization target)
        - **logicalio**: Total logical I/O operations (scan indicator)
        - **cpuskw**: CPU skew ratio (distribution problems)
        - **ioskw**: I/O skew ratio (hot spot indicators)
        - **pji**: Physical-to-Logical I/O ratio (compute intensity)
        - **uii**: Unit I/O Intensity (I/O efficiency)
        - **numsteps**: Query execution plan steps (complexity)
        - **response_secs**: Wall-clock execution time (user impact)
        - **delaytime**: Time spent in queue (concurrency issues)

        **AUTOMATIC PERFORMANCE CATEGORIZATION:**
        Each query is categorized using configurable thresholds (from sql_opt_config.yml):
        - **CPU Categories**: VERY_HIGH_CPU (>config.very_high), HIGH_CPU (>config.high), MEDIUM_CPU (>10s), LOW_CPU
        - **CPU Skew**: SEVERE_CPU_SKEW (>config.severe), HIGH_CPU_SKEW (>config.high), MODERATE_CPU_SKEW (>config.moderate), NORMAL
        - **I/O Skew**: SEVERE_IO_SKEW (>config.severe), HIGH_IO_SKEW (>config.high), MODERATE_IO_SKEW (>config.moderate), NORMAL
        
        Use thresholds set in config file for, CPU - high, very_high, Skew moderate, high, severe

        **TYPICAL OPTIMIZATION WORKFLOW:**
        1. Start with clusters identified from sql_Analyze_Cluster_Stats
        2. Retrieve top queries by impact metric (usually 'ampcputime')
        3. Analyze SQL patterns for common issues:
           - Missing WHERE clauses or inefficient predicates
           - Cartesian products or missing JOIN conditions
           - Inefficient GROUP BY or ORDER BY operations
           - Suboptimal table access patterns
           - Missing or outdated statistics
        4. Develop specific optimization recommendations

        **QUERY LIMIT STRATEGY:**
        - Use the query limit set in config file for  pattern recognition and analysis, unless user specifies a different limit

        **OUTPUT INCLUDES:**
        - Complete SQL query text for each query
        - All performance metrics, user, application, and workload context, cluster membership and rankings
        - Performance categories for quick filtering        
        """
    
    config = SQL_CLUSTERING_CONFIG
    
    logger.debug(f"handle_sql_Retrieve_Cluster_Queries: clusters={cluster_ids}, metric={metric}, limit={limit_per_cluster}")
    
    feature_db = config['databases']['feature_db']
    clusters_table = config['tables']['sql_query_clusters']
    
    # Validate metric
    valid_metrics = [
        'ampcputime', 'logicalio', 'cpuskw', 'ioskw', 'pji', 'uii',
        'numsteps', 'response_secs', 'delaytime'
    ]
    
    if metric not in valid_metrics:
        metric = 'ampcputime'  # Default fallback

    # Convert cluster_ids list to comma-separated string for SQL IN clause
    cluster_ids_str = ','.join(map(str, cluster_ids))

    with conn.cursor() as cur:
        
        # Get thresholds from config
        thresholds = config.get('performance_thresholds', {})
        cpu_high = thresholds.get('cpu', {}).get('high', 100)
        cpu_very_high = thresholds.get('cpu', {}).get('very_high', 1000)
        skew_moderate = thresholds.get('skew', {}).get('moderate', 2.0)
        skew_high = thresholds.get('skew', {}).get('high', 3.0)
        skew_severe = thresholds.get('skew', {}).get('severe', 5.0)
        
        retrieve_queries_sql = f"""
        SELECT 
            td_clusterid_kmeans,
            id,
            txt,
            username,
            appid,
            numsteps,
            ampcputime,
            logicalio,
            wdname,
            cpuskw,
            ioskw,
            pji,
            uii,
            response_secs,
            response_mins,
            delaytime,
            silhouette_score,
            -- Ranking within cluster by selected metric
            ROW_NUMBER() OVER (PARTITION BY td_clusterid_kmeans ORDER BY {metric} DESC) AS rank_in_cluster,
            -- Overall ranking across all selected clusters
            ROW_NUMBER() OVER (ORDER BY {metric} DESC) AS overall_rank,
            -- Performance categorization with configurable thresholds
            CASE 
                WHEN ampcputime > {cpu_very_high} THEN 'VERY_HIGH_CPU'
                WHEN ampcputime > {cpu_high} THEN 'HIGH_CPU'
                WHEN ampcputime > 10 THEN 'MEDIUM_CPU'
                ELSE 'LOW_CPU'
            END AS cpu_category,
            CASE 
                WHEN cpuskw > {skew_severe} THEN 'SEVERE_CPU_SKEW'
                WHEN cpuskw > {skew_high} THEN 'HIGH_CPU_SKEW'
                WHEN cpuskw > {skew_moderate} THEN 'MODERATE_CPU_SKEW'
                ELSE 'NORMAL_CPU_SKEW'
            END AS cpu_skew_category,
            CASE 
                WHEN ioskw > {skew_severe} THEN 'SEVERE_IO_SKEW'
                WHEN ioskw > {skew_high} THEN 'HIGH_IO_SKEW'
                WHEN ioskw > {skew_moderate} THEN 'MODERATE_IO_SKEW'
                ELSE 'NORMAL_IO_SKEW'
            END AS io_skew_category
        FROM {feature_db}.{clusters_table}
        WHERE td_clusterid_kmeans IN ({cluster_ids_str})
        QUALIFY ROW_NUMBER() OVER (PARTITION BY td_clusterid_kmeans ORDER BY {metric} DESC) <= {limit_per_cluster}
        ORDER BY td_clusterid_kmeans, {metric} DESC
        """
        
        cur.execute(retrieve_queries_sql)
        data = rows_to_json(cur.description, cur.fetchall())
        
        # Get summary by cluster
        cur.execute(f"""
        SELECT 
            td_clusterid_kmeans,
            COUNT(*) AS queries_retrieved,
            AVG({metric}) AS avg_metric_value,
            MAX({metric}) AS max_metric_value,
            MIN({metric}) AS min_metric_value
        FROM {feature_db}.{clusters_table}
        WHERE td_clusterid_kmeans IN ({cluster_ids_str})
        GROUP BY td_clusterid_kmeans
        ORDER BY td_clusterid_kmeans
        """)
        
        cluster_summary = rows_to_json(cur.description, cur.fetchall())
        
        logger.debug(f"Retrieved {len(data)} queries from {len(cluster_ids)} clusters")

    # Return results with metadata
    metadata = {
        "tool_name": "sql_Retrieve_Cluster_Queries",
        "retrieval_parameters": {
            "cluster_ids": cluster_ids,
            "sort_metric": metric,
            "limit_per_cluster": limit_per_cluster,
            "valid_metrics": valid_metrics
        },
        "cluster_summary": cluster_summary,
        "queries_retrieved": len(data),
        "table_source": f"{feature_db}.{clusters_table}",
        "analysis_ready": True,
        "description": f"Retrieved top {limit_per_cluster} queries per cluster sorted by {metric} - ready for pattern analysis and optimization recommendations"
    }

    return create_response(data, metadata)






