# RAG Tools

**Dependencies**

Assumes Teradata >=20.XX.  

**RAG** tools:

- rag_setConfig - sets the config for the current rag session
- rag_storeUserQuery - stores the users natural laguage query
- rag_tokenizeQuery - turns the query into a vector
- rag_createEmbeddingView - Generates sentence embeddings for the most recent tokenized user query
- rag_createQueryEmbeddingTable - creates a table for embeddigs
- rag_semanticSearchChunks - retreives the top N chucks


**RAG** prompts:

- rag_guidelines - guides user through rag example using vector data types.

[Return to Main README](../../../../README.md)