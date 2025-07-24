import logging
from typing import Optional, Any, Dict, List
from teradatasql import TeradataConnection
import json
from datetime import date, datetime
from decimal import Decimal


logger = logging.getLogger("teradata_mcp_server")


def serialize_teradata_types(obj: Any) -> Any:
    """Convert Teradata-specific types to JSON serializable formats"""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)

def rows_to_json(cursor_description: Any, rows: List[Any]) -> List[Dict[str, Any]]:
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

def create_response(data: Any, metadata: Optional[Dict[str, Any]] = None) -> str:
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

def handle_rag_executeWorkflow(
    conn: TeradataConnection,
    question: str,
    k: int = 10,
    *args,
    **kwargs,
):
    """
    Execute complete RAG workflow to answer user questions based on document context.

    This function handles the entire RAG pipeline:
    1. Configuration setup (using hardcoded values)
    2. Store user query (with /rag prefix stripping)
    3. Generate query embeddings (tokenization + embedding)
    4. Perform semantic search against chunk embeddings
    5. Return retrieved context chunks for answer generation

    The function uses hardcoded configuration values:
    - query_db = 'demo_db'
    - query_table = 'user_query'
    - query_embedding_store = 'user_query_embeddings'
    - model_db = 'demo_db'
    - model_id = 'bge-small-en-v1.5'
    - vector_db = 'demo_db'
    - vector_table = 'pdf_embeddings_store'

    Returns the top-k most relevant chunks with metadata for context-grounded answer generation.
    """
    
    global rag_config
    
    logger.debug(f"handle_rag_executeWorkflow: question={question[:60]}..., k={k}")
    
    # Step 1: Set configuration (hardcoded values)
    rag_config = {
        "query_db": "demo_db",
        "query_table": "user_query",
        "query_embedding_store": "user_query_embeddings",
        "model_db": "demo_db",
        "model_id": "bge-small-en-v1.5",
        "vector_db": "demo_db",
        "vector_table": "pdf_embeddings_store",
    }
    
    # Extract config values
    db_name = rag_config["query_db"]
    table_name = rag_config["query_table"]
    dst_table = rag_config["query_embedding_store"]
    model_id = rag_config["model_id"]
    model_db = rag_config["model_db"]
    model_table = "embeddings_models"
    tokenizer_table = "embeddings_tokenizers"
    vector_db = rag_config["vector_db"]
    chunk_embed_table = rag_config["vector_table"]

    with conn.cursor() as cur:
        
        # Step 2: Store user query
        logger.debug(f"Step 2: Storing user query in {db_name}.{table_name}")
        
        # Create table if it doesn't exist
        ddl = f"""
        CREATE TABLE {db_name}.{table_name} (
            id INTEGER GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1) NOT NULL,
            txt VARCHAR(5000),
            created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id)
        )
        """
        
        try:
            cur.execute(ddl)
            logger.debug(f"Table {db_name}.{table_name} created")
        except Exception as e:
            error_msg = str(e).lower()
            if "already exists" in error_msg or "3803" in error_msg:
                logger.debug(f"Table {db_name}.{table_name} already exists, skipping creation")
            else:
                logger.error(f"Error creating table: {e}")
                raise

        # Insert cleaned question
        insert_sql = f"""
        INSERT INTO {db_name}.{table_name} (txt)
        SELECT
          CASE
            WHEN TRIM(?) LIKE '/rag %' THEN SUBSTRING(TRIM(?) FROM 6)
            ELSE TRIM(?)
          END
        """
        cur.execute(insert_sql, [question, question, question])
        
        # Get inserted ID and cleaned text
        cur.execute(f"SELECT MAX(id) AS id FROM {db_name}.{table_name}")
        new_id = cur.fetchone()[0]
        
        cur.execute(f"SELECT txt FROM {db_name}.{table_name} WHERE id = ?", [new_id])
        cleaned_txt = cur.fetchone()[0]
        
        logger.debug(f"Stored query with ID {new_id}: {cleaned_txt[:60]}...")

        # Step 3: Generate query embeddings
        logger.debug(f"Step 3: Generating embeddings in {db_name}.{dst_table}")
        
        # Drop existing embeddings table
        drop_sql = f"DROP TABLE {db_name}.{dst_table}"
        try:
            cur.execute(drop_sql)
            logger.debug(f"Dropped existing table {db_name}.{dst_table}")
        except Exception as e:
            logger.debug(f"DROP failed or table not found: {e}")

        # Create embeddings table using ONNXEmbeddings
        create_sql = f"""
        CREATE TABLE {db_name}.{dst_table} AS (
            SELECT *
            FROM mldb.ONNXEmbeddings(
                ON (SELECT id, txt FROM {db_name}.{table_name})
                ON (SELECT model_id, model FROM {model_db}.{model_table} WHERE model_id = '{model_id}') DIMENSION
                ON (SELECT model AS tokenizer FROM {model_db}.{tokenizer_table} WHERE model_id = '{model_id}') DIMENSION
                USING
                    Accumulate('id', 'txt')
                    ModelOutputTensor('sentence_embedding')
                    OutputFormat('FLOAT32(384)')
            ) AS a
        ) WITH DATA
        """
        
        cur.execute(create_sql)
        logger.debug(f"Created embeddings table {db_name}.{dst_table}")

        # Step 4: Perform semantic search
        logger.debug(f"Step 4: Performing semantic search with k={k}")
        
        search_sql = f"""
        SELECT
            e_ref.txt          AS reference_txt,
            e_ref.chunk_num    AS chunk_num,
            e_ref.page_num     AS page_num,
            e_ref.doc_name     AS doc_name,
            (1.0 - dt.distance) AS similarity
        FROM TD_VECTORDISTANCE (
                ON {vector_db}.{dst_table}      AS TargetTable
                ON {vector_db}.{chunk_embed_table}      AS ReferenceTable DIMENSION
                USING
                    TargetIDColumn('id')
                    TargetFeatureColumns('[emb_0:emb_383]')
                    RefIDColumn('id')
                    RefFeatureColumns('[emb_0:emb_383]')
                    DistanceMeasure('cosine')
                    TopK({k})
            ) AS dt
        JOIN {vector_db}.{chunk_embed_table} e_ref
          ON e_ref.id = dt.reference_id
        ORDER BY similarity DESC;
        """
        
        rows = cur.execute(search_sql)
        data = rows_to_json(cur.description, rows.fetchall())
        
        logger.debug(f"Retrieved {len(data)} chunks for semantic search")

    # Return results with comprehensive metadata
    metadata = {
        "tool_name": "rag_executeWorkflow",
        "workflow_steps": ["config_set", "query_stored", "embeddings_generated", "semantic_search_completed"],
        "query_id": new_id,
        "cleaned_question": cleaned_txt,
        "database": db_name,
        "query_table": table_name,
        "embedding_table": dst_table,
        "vector_table": chunk_embed_table,
        "model_id": model_id,
        "chunks_retrieved": len(data),
        "topk_requested": k,
        "description": "Complete RAG workflow executed: config → store query → generate embeddings → semantic search"
    }

    return create_response(data, metadata)

def handle_rag_executeWorkflow_ivsm(
    conn: TeradataConnection,
    question: str,
    k: int = 10,
    *args,
    **kwargs,
):
    """
    Execute complete RAG workflow to answer user questions based on document context.

    This function handles the entire RAG pipeline using IVSM functions:
    1. Configuration setup (using hardcoded values)
    2. Store user query (with /rag prefix stripping)
    3. Tokenize query using ivsm.tokenizer_encode
    4. Create embedding view using ivsm.IVSM_score
    5. Convert embeddings to vector columns using ivsm.vector_to_columns
    6. Perform semantic search against chunk embeddings

    The function uses hardcoded configuration values:
    - query_db = 'demo_db'
    - query_table = 'user_query'
    - query_embedding_store = 'user_query_embeddings'
    - model_db = 'demo_db'
    - model_id = 'bge-small-en-v1.5'
    - vector_db = 'demo_db'
    - vector_table = 'pdf_embeddings_store'

    Returns the top-k most relevant chunks with metadata for context-grounded answer generation.
    """
    
    global rag_config
    
    logger.debug(f"handle_rag_executeWorkflow (IVSM): question={question[:60]}..., k={k}")
    
    # Step 1: Set configuration (hardcoded values)
    rag_config = {
        "query_db": "demo_db",
        "query_table": "user_query",
        "query_embedding_store": "user_query_embeddings",
        "model_db": "demo_db",
        "model_id": "bge-small-en-v1.5",
        "vector_db": "demo_db",
        "vector_table": "pdf_embeddings_store",
    }
    
    # Extract config values
    db_name = rag_config["query_db"]
    table_name = rag_config["query_table"]
    dst_table = rag_config["query_embedding_store"]
    model_id = rag_config["model_id"]
    vector_db = rag_config["vector_db"]
    chunk_embed_table = rag_config["vector_table"]

    with conn.cursor() as cur:
        
        # Step 2: Store user query
        logger.debug(f"Step 2: Storing user query in {db_name}.{table_name}")
        
        # Create table if it doesn't exist
        ddl = f"""
        CREATE TABLE {db_name}.{table_name} (
            id INTEGER GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1) NOT NULL,
            txt VARCHAR(5000),
            created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id)
        )
        """
        
        try:
            cur.execute(ddl)
            logger.debug(f"Table {db_name}.{table_name} created")
        except Exception as e:
            error_msg = str(e).lower()
            if "already exists" in error_msg or "3803" in error_msg:
                logger.debug(f"Table {db_name}.{table_name} already exists, skipping creation")
            else:
                logger.error(f"Error creating table: {e}")
                raise

        # Insert cleaned question
        insert_sql = f"""
        INSERT INTO {db_name}.{table_name} (txt)
        SELECT
          CASE
            WHEN TRIM(?) LIKE '/rag %' THEN SUBSTRING(TRIM(?) FROM 6)
            ELSE TRIM(?)
          END
        """
        cur.execute(insert_sql, [question, question, question])
        
        # Get inserted ID and cleaned text
        cur.execute(f"SELECT MAX(id) AS id FROM {db_name}.{table_name}")
        new_id = cur.fetchone()[0]
        
        cur.execute(f"SELECT txt FROM {db_name}.{table_name} WHERE id = ?", [new_id])
        cleaned_txt = cur.fetchone()[0]
        
        logger.debug(f"Stored query with ID {new_id}: {cleaned_txt[:60]}...")

        # Step 3: Tokenize query
        logger.debug(f"Step 3: Tokenizing query using ivsm.tokenizer_encode")
        
        cur.execute(f"""
            REPLACE VIEW v_topics_tokenized AS
            (
                SELECT id, txt,
                       IDS AS input_ids,
                       attention_mask
                FROM ivsm.tokenizer_encode(
                    ON (
                        SELECT *
                        FROM {db_name}.{table_name}
                        QUALIFY ROW_NUMBER() OVER (ORDER BY created_ts DESC) = 1
                    )
                    ON (
                        SELECT model AS tokenizer
                        FROM {db_name}.embeddings_tokenizers
                        WHERE model_id = '{model_id}'
                    ) DIMENSION
                    USING
                        ColumnsToPreserve('id','txt')
                        OutputFields('IDS','ATTENTION_MASK')
                        MaxLength(1024)
                        PadToMaxLength('True')
                        TokenDataType('INT64')
                ) AS t
            );
        """)
        
        logger.debug("Tokenized view v_topics_tokenized created")

        # Step 4: Create embedding view
        logger.debug(f"Step 4: Creating embedding view using ivsm.IVSM_score")
        
        cur.execute(f"""
            REPLACE VIEW v_topics_embeddings AS
            (
                SELECT *
                FROM ivsm.IVSM_score(
                    ON v_topics_tokenized
                    ON (
                        SELECT *
                        FROM {db_name}.embeddings_models
                        WHERE model_id = '{model_id}'
                    ) DIMENSION
                    USING
                        ColumnsToPreserve('id','txt')
                        ModelType('ONNX')
                        BinaryInputFields('input_ids','attention_mask')
                        BinaryOutputFields('sentence_embedding')
                        Caching('inquery')
                ) AS s
            );
        """)
        
        logger.debug("Embedding view v_topics_embeddings created")

        # Step 5: Create query embedding table
        logger.debug(f"Step 5: Creating query embedding table using ivsm.vector_to_columns")
        
        # Drop existing embeddings table
        drop_sql = f"DROP TABLE {db_name}.{dst_table}"
        try:
            cur.execute(drop_sql)
            logger.debug(f"Dropped existing table {db_name}.{dst_table}")
        except Exception as e:
            logger.debug(f"DROP failed or table not found: {e}")

        # Create embeddings table using vector_to_columns
        create_sql = f"""
        CREATE TABLE {db_name}.{dst_table} AS (
            SELECT *
            FROM ivsm.vector_to_columns(
                ON v_topics_embeddings
                USING
                    ColumnsToPreserve('id', 'txt') 
                    VectorDataType('FLOAT32')
                    VectorLength(384)
                    OutputColumnPrefix('emb_')
                    InputColumnName('sentence_embedding')
            ) a 
        ) WITH DATA
        """
        
        cur.execute(create_sql)
        logger.debug(f"Created embeddings table {db_name}.{dst_table}")

        # Step 6: Perform semantic search
        logger.debug(f"Step 6: Performing semantic search with k={k}")
        
        search_sql = f"""
        SELECT
            e_ref.txt          AS reference_txt,
            e_ref.chunk_num    AS chunk_num,
            e_ref.page_num     AS page_num,
            e_ref.doc_name     AS doc_name,
            (1.0 - dt.distance) AS similarity
        FROM TD_VECTORDISTANCE (
                ON {vector_db}.{dst_table}      AS TargetTable
                ON {vector_db}.{chunk_embed_table}      AS ReferenceTable DIMENSION
                USING
                    TargetIDColumn('id')
                    TargetFeatureColumns('[emb_0:emb_383]')
                    RefIDColumn('id')
                    RefFeatureColumns('[emb_0:emb_383]')
                    DistanceMeasure('cosine')
                    TopK({k})
            ) AS dt
        JOIN {vector_db}.{chunk_embed_table} e_ref
          ON e_ref.id = dt.reference_id
        ORDER BY similarity DESC;
        """
        
        rows = cur.execute(search_sql)
        data = rows_to_json(cur.description, rows.fetchall())
        
        logger.debug(f"Retrieved {len(data)} chunks for semantic search")

    # Return results with comprehensive metadata
    metadata = {
        "tool_name": "rag_executeWorkflow_ivsm",
        "workflow_type": "IVSM",
        "workflow_steps": ["config_set", "query_stored", "query_tokenized", "embedding_view_created", "embedding_table_created", "semantic_search_completed"],
        "query_id": new_id,
        "cleaned_question": cleaned_txt,
        "database": db_name,
        "query_table": table_name,
        "embedding_table": dst_table,
        "vector_table": chunk_embed_table,
        "model_id": model_id,
        "chunks_retrieved": len(data),
        "topk_requested": k,
        "views_created": ["v_topics_tokenized", "v_topics_embeddings"],
        "description": "Complete RAG workflow executed using IVSM functions: config → store query → tokenize → create embedding view → create embedding table → semantic search"
    }

    return create_response(data, metadata)