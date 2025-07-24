# RAG Tools

**Dependencies**

Assumes Teradata >=20.XX.  

**RAG** tools:

- rag_executeWorkflow - executes complete RAG pipeline (config setup, query storage, embedding generation, and semantic search) in a single step

**Version Selection:**

The RAG tool supports two implementations that can be selected via configuration:

- **BYOM (default)**: Uses ONNXEmbeddings for embedding generation
- **IVSM**: Uses IVSM functions for embedding generation

To switch between versions, update the `version` parameter in `configure_tools.yaml`:

```yaml
rag:
    allmodule: True
    version: 'byom'  # Options: 'byom' or 'ivsm'
    tool:
        rag_executeWorkflow: True
    prompt:
        rag_guidelines: True

[Return to Main README](../../../../README.md)