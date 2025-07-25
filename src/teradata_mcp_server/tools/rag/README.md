# RAG Tools

**Dependencies**

Assumes Teradata >=20.XX.  

**RAG** tools:

- rag_executeWorkflow - executes complete RAG pipeline (config setup, query storage, embedding generation, and semantic search) in a single step


**Configuration:**

The RAG system is fully configurable through `rag_config.yaml`. You can customize:

- **Database locations** (query_db, model_db, vector_db)
- **Table names** (query_table, vector_table, model_table, etc.)
- **Model settings** (model_id, embedding dimensions)
- **Vector store metadata fields**
- **Embedding parameters** (vector length, column prefix, distance measure)
- **Retrieval settings** (default chunk count, maximum limits)

**Version Selection:**

The RAG tool supports two implementations:

- **BYOM (default)**: Uses ONNXEmbeddings for embedding generation
- **IVSM**: Uses IVSM functions for embedding generation

To switch between versions, edit `rag_config.yaml`:

```yaml
version: 'byom'  # Options: 'byom' or 'ivsm'
```

**Vector Store Compatibility:**

The system automatically adapts to your vector store schema. Configure your setup in `rag_config.yaml`:

```yaml
# Database Configuration
databases:
  query_db: "your_db"
  vector_db: "your_vector_db"

# Table Configuration  
tables:
  vector_table: "your_vector_store_table"

# Model Configuration (adjust for different embedding models)
model:
  model_id: "your-model-id"

# RAG Retrieval Configuration
retrieval:
  default_k: 10  # Default number of chunks to retrieve
  max_k: 50      # Maximum allowed chunks

# Embedding Configuration (change for different model dimensions)
embedding:
  vector_length: 384  # Change based on your model
  feature_columns: "[emb_0:emb_383]"  # Adjust range accordingly

# Vector Store Schema
vector_store_schema:
  metadata_fields_in_vector_store:
    - "chunk_num"
    - "doc_name"
    # Add any other metadata columns from your vector store
```


The RAG tool supports two implementations that can be selected via configuration:


- rag_guidelines - guidelines for llm for rag workflow.


[Return to Main README](../../../../README.md)