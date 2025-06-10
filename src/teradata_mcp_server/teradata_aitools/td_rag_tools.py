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


"""
Tools that power Retrieval-Augmented Generation (RAG) on Teradata Vantage.

They let an MCP agent
1. store the user’s question,
2. create an embedding for that question, and
3. fetch the top-k most-similar PDF chunks.

All SQL objects (DB, table, model-ID) are passed in as parameters.
"""

import logging
from typing import Optional, List
from teradatasql import TeradataConnection
from datetime import datetime

from .td_base_tools import rows_to_json, create_response  # reuse helpers

logger = logging.getLogger("teradata_mcp_server")



# Store RAG config for the session in a global or module-level variable
rag_config = {}

def handle_set_rag_config(
    conn: TeradataConnection,
    query_db: str,
    model_db: str,
    vector_db: str,
    vector_table: str,
    *args,
    **kwargs,
):
    """
    Store session-wide RAG configuration for downstream tools:
    - query_db / query_table: where to store user questions
    - model_db / model_table / model_id: where the embedding model lives
    - query_embedding_store: where to store user query embeddings
    - vector_db / vector_table: where chunk embeddings are stored for similarity search
    """
    global rag_config

    rag_config = {
        "query_db": query_db,
        "query_table": "user_query",
        "query_embedding_store": "user_query_embeddings",
        "model_db": model_db,
        "model_id": "bge-small-en-v1.5",
        "vector_db": vector_db,
        "vector_table": vector_table,
    }

    return create_response({"message": "RAG config successfully set."}, metadata=rag_config)

def handle_store_user_query(
    conn: TeradataConnection,
    question: str,
    *args,
    **kwargs,
):
    """
    Insert the user's question into rag_config["query_db"].rag_config["query_table"].
    Strips '/rag ' prefix if present. Creates the table if it does not exist.
    """
    global rag_config

    db_name = rag_config.get("query_db")
    table_name = rag_config.get("query_table")

    if not db_name or not table_name:
        raise ValueError("RAG config not set — call `rag_set_config` first to configure database and table.")

    logger.debug(
        f"handle_store_user_query: db={db_name}, table={table_name}, text={question[:60]}"
    )

    ddl = f"""
    CREATE TABLE {db_name}.{table_name} (
        id INTEGER GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1) NOT NULL,
        txt VARCHAR(5000),
        created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id)
    )
    """

    with conn.cursor() as cur:
        try:
            cur.execute(ddl)
            logger.info(f"Table {db_name}.{table_name} created")
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

        # Fetch ID and cleaned question
        cur.execute(f"SELECT MAX(id) AS id FROM {db_name}.{table_name}")
        new_id = cur.fetchone()[0]

        cur.execute(f"SELECT txt FROM {db_name}.{table_name} WHERE id = ?", [new_id])
        cleaned_txt = cur.fetchone()[0]

    meta = {
        "tool_name": "store_user_query",
        "database": db_name,
        "table": table_name,
        "inserted_id": new_id,
    }

    return create_response([{"id": new_id, "txt": cleaned_txt}], meta)

def create_tokenized_view(conn: TeradataConnection):
    """
    Tokenizes the most recent user-submitted query using the tokenizer specified in rag_config.
    
    It:
    - Pulls the latest row from the user query table (e.g., 'pdf_topics_of_interest')
    - Tokenizes it using the ONNX tokenizer model (e.g., 'bge-small-en-v1.5')
    - Creates or replaces a view named <db>.v_topics_tokenized with input_ids and attention_mask
    
    Configuration like database name, table name, and model_id is pulled from rag_config.
    """
    global rag_config
    db_name   = rag_config["query_db"]
    src_table = rag_config["query_table"]
    model_id  = rag_config["model_id"]

    with conn.cursor() as cur:
        cur.execute(f"""
            REPLACE VIEW {db_name}.v_topics_tokenized AS
            (
                SELECT id, txt,
                       IDS AS input_ids,
                       attention_mask
                FROM ivsm.tokenizer_encode(
                    ON (
                        SELECT *
                        FROM {db_name}.{src_table}
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

    meta = {
        "tool_name": "create_tokenized_view",
        "database": db_name,
        "source_table": src_table,
        "model_id": model_id,
        "view_created": f"{db_name}.v_topics_tokenized"
    }

    return create_response("Tokenized view created successfully.", meta)

def create_embedding_view(conn: TeradataConnection):
    """
    Generates sentence embeddings for the most recent user query using the model specified in rag_config.

    It:
    - Reads tokenized input from <db>.v_topics_tokenized
    - Applies IVSM_score using the ONNX model identified by rag_config['model_id']
    - Creates or replaces a view <db>.v_topics_embeddings with the original input and sentence_embedding column

    All table names and model info are pulled from the rag_config set earlier via 'configure_rag'.
    """
    global rag_config
    db_name  = rag_config["query_db"]
    model_id = rag_config["model_id"]

    with conn.cursor() as cur:
        cur.execute(f"""
            REPLACE VIEW {db_name}.v_topics_embeddings AS
            (
                SELECT *
                FROM ivsm.IVSM_score(
                    ON {db_name}.v_topics_tokenized
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

    meta = {
        "tool_name": "create_embedding_view",
        "database": db_name,
        "tokenized_view": f"{db_name}.v_topics_tokenized",
        "embedding_model_id": model_id,
        "view_created": f"{db_name}.v_topics_embeddings"
    }

    return create_response("Embedding view created successfully.", meta)


def handle_create_query_embeddings(conn: TeradataConnection, *args, **kwargs):
    global rag_config
    db_name = rag_config.get("query_db")
    dst_table = rag_config.get("query_embedding_store")

    if not db_name or not dst_table:
        raise ValueError("RAG config not set — call `rag_set_config` first to configure vector store for query embeddings.")

    logger.debug(f"Tool: handle_create_query_embeddings: db={db_name}, dst={dst_table}")

    drop_sql = f"DROP TABLE {db_name}.{dst_table}"
    create_sql = f"""
    CREATE TABLE {db_name}.{dst_table} AS (
        SELECT *
        FROM ivsm.vector_to_columns(
            ON {db_name}.v_topics_embeddings
            USING
                ColumnsToPreserve('id', 'txt') 
                VectorDataType('FLOAT32')
                VectorLength(384)
                OutputColumnPrefix('emb_')
                InputColumnName('sentence_embedding')
        ) a 
    ) WITH DATA
    """

    with conn.cursor() as cur:
        try:
            cur.execute(drop_sql)
            logger.debug(f"Dropped existing table {db_name}.{dst_table}")
        except Exception as e:
            logger.debug(f"DROP failed or table not found: {e}")

        cur.execute(create_sql)
        logger.debug(f"Created table {db_name}.{dst_table} with embedding columns")

        return create_response(
            [],
            metadata={
                "tool_name": "materialize_query_embeddings",
                "database": db_name,
                "table": dst_table,
                "status": "table created (or replaced)"
            }
        )


def handle_semantic_search(
    conn: TeradataConnection,
    topk: int = 10,
    *args,
    **kwargs,
):
    """
    Return the top-k most similar chunk texts based on the latest query embedding.
    Also returns chunk_num, page_num, and doc_name for context attribution.
    Uses session-wide RAG config.
    """
    global rag_config

    db_name            = rag_config["vector_db"]
    query_embed_table  = rag_config["query_embedding_store"]
    chunk_embed_table  = rag_config["vector_table"]

    logger.debug(
        f"handle_semantic_search: db={db_name}, q_table={query_embed_table}, c_table={chunk_embed_table}, k={topk}"
    )

    sql = f"""
    SELECT
        e_ref.txt          AS reference_txt,
        e_ref.chunk_num    AS chunk_num,
        e_ref.page_num     AS page_num,
        e_ref.doc_name     AS doc_name,
        (1.0 - dt.distance) AS similarity
    FROM TD_VECTORDISTANCE (
            ON {db_name}.{query_embed_table}      AS TargetTable
            ON {db_name}.{chunk_embed_table}      AS ReferenceTable DIMENSION
            USING
                TargetIDColumn('id')
                TargetFeatureColumns('[emb_0:emb_383]')
                RefIDColumn('id')
                RefFeatureColumns('[emb_0:emb_383]')
                DistanceMeasure('cosine')
                TopK({topk})
        ) AS dt
    JOIN {db_name}.{chunk_embed_table} e_ref
      ON e_ref.id = dt.reference_id
    ORDER BY similarity DESC;
    """

    with conn.cursor() as cur:
        rows = cur.execute(sql)
        data = rows_to_json(cur.description, rows.fetchall())

    meta = {
        "tool_name": "semantic_search",
        "vector_db": db_name,
        "query_embedding_store": query_embed_table,
        "chunk_embedding_store": chunk_embed_table,
        "topk": topk,
        "returned": len(data),
    }

    return create_response(data, meta)



