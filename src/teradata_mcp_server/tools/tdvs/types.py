# ------------------------------------------------------------------------------ #
#  Copyright (C) 2025 by Teradata Corporation.                                   #
#  All Rights Reserved.                                                          #
#                                                                                #
#  File: types.py                                                       #
#                                                                                #
#  Description:                                                                  #
#    This file has various pydantic models if need for your tools                #
#                                                                                #
#    Enable LLMs to perform actions through your server                          #
#                                                                                #
#  Tools are a powerful primitive in the Model Context Protocol (MCP) that       #
#  enable servers to expose executable functionality to clients. Through tools,  #
#  LLMs can interact with external systems, perform computations, and take       #
#  actions in the real world.                                                    #
# ------------------------------------------------------------------------------ #

from pydantic import BaseModel, Field
from typing import Literal, Optional, List

class VectorStoreSimilaritySearch(BaseModel):
    """Model for performing similarity search for a question in Teradata VectorStore."""
    question: str = Field(..., description="Specifies a string of text for which similarity search needs to be performed.")
    batch_data: Optional[str] = Field(None, description="Optional Specifies the table name or teradataml DataFrame to be indexed for batch mode")
    batch_id_column: Optional[str] = Field(None, description="Optional Specifies the ID column to be indexed for batch mode")
    batch_query_column: Optional[str] = Field(None, description="Optional Specifies the query column to be indexed for batch mode.")
    

class VectorStoreAsk(BaseModel):
    """Model for asking a question to a VectorStore."""
    question: str = Field(..., description="The question to ask the VectorStore.")
    prompt: Optional[str] = Field(None, description="Optional prompt to guide the response.")
    batch_data: Optional[str] = Field(None, description="Optional Specifies the table name or teradataml DataFrame to be indexed for batch mode")
    batch_id_column: Optional[str] = Field(None, description="Optional Specifies the ID column to be indexed for batch mode")
    batch_query_column: Optional[str] = Field(None, description="Optional Specifies the query column to be indexed for batch mode.")
    

class VectorStoreCreate(BaseModel):
    """Model for creating a Teradata VectorStore."""
    description: str = Field(..., description="Specifies the description of the VectorStore.")
    target_database: Optional[str] = Field(None, description="Specifies the target database where the VectorStore will be created.")
    object_names: str = Field(..., description="Specifies the table name(s)/teradataml DataFrame(s) to be indexed for vector store.")
    key_columns: List[str] = Field(None, description="Optional Specifies the name(s) of the key column(s) to be used for indexing.")
    data_columns: List[str] = Field(None, description="Optional Specifies the name(s) of the data column(s) to be used for embedding generation(vectorization).")
    vector_column: Optional[str] = Field(None, description="Specifies the name of the column where the vectorized data will be stored.")
    chunk_size: Optional[int] = Field(None, description="Optional Specifies the size of each chunk when dividing document files into chunks.")
    optimized_chunking: Optional[bool] = Field(None, description="Optional Specifies whether an optimized splitting mechanism supplied by Teradata should be used.")
    header_height: Optional[int] = Field(None, description="Optional Specifies the height of the header in the document file.")
    footer_height: Optional[int] = Field(None, description="Optional Specifies the height of the footer in the document file.")
    embeddings_model: str = Field(None, description="Optional Specifies the embedding model to be used for vectorization.")
    embeddings_dims: Optional[int] = Field(None, description="Optional Specifies the number of dimensions for the embeddings.")
    metric: Optional[str] = Field(None, description="Optional Specifies the metric to be used for calculating the distance between the vectors.")
    search_algorithm: Optional[str] = Field(None, description="Optional Specifies the search algorithm to be used for similarity search.")
    initial_centroids_method: Optional[str] = Field(None, description="Optional Specifies the method to be used for initializing centroids.")
    train_numclusters: Optional[int] = Field(None, description="Optional Specifies the number of clusters to be used for training.")
    max_iternum: Optional[int] = Field(None, description="Optional Specifies the maximum number of iterations for training.")
    stop_threshold: Optional[float] = Field(None, description="Optional Specifies the threshold for stopping the training process.")
    seed: Optional[int] = Field(None, description="Optional Specifies the seed value for random number generation.")
    num_init: Optional[int] = Field(None, description="Optional Specifies the number of initializations to be performed for k-means.")
    top_k: Optional[int] = Field(None, description="Optional Specifies the number of top results to be returned for similarity search.")
    search_threshold: Optional[float] = Field(None, description="OptionalSpecifies the threshold value to consider for matching tables/views while searching.")
    search_numcluster: Optional[int] = Field(None, description="Optional Specifies the number of clusters to be used for searching.")
    prompt: Optional[str] = Field(None, description="Optional Specifies the prompt to be used by language model to generate responses using top matches.")
    chat_completion_model: Optional[str] = Field(None, description="Optional Specifies the chat completion model to be used for generating responses.")
    document_files: Optional[List[str]] = Field(None, description="Optional Specifies the list of document files to be indexed for vector store.")
    ef_search: Optional[int] = Field(None, description="Optional Specifies the number of neighbors to be considered for hnsw algorithm during similarity search.")
    num_layers: Optional[int] = Field(None, description="Optional Specifies the maximum number of layers to be used for hnsw algorithm during vector store creation.")
    ef_construction: Optional[int] = Field(None, description="Optional Specifies the number of neighbors to be considered for hnsw algorithm during vector store creation.")
    num_connpernode: Optional[int] = Field(None, description="Optional Specifies the number of connections per node to be used for hnsw algorithm during vector store creation.")
    maxnum_connpernode: Optional[int] = Field(None, description="Optional Specifies the maximum number of connections per node to be used for hnsw algorithm during vector store creation.")
    apply_heuristics: Optional[bool] = Field(None, description="Optional Specifies whether to apply heuristics for hnsw algorithm during vector store creation.")
    include_objects: Optional[List[str]] = Field(None, description="Optional Specifies the list of tables/views included in the metadata based vector store.")
    exclude_objects: Optional[List[str]] = Field(None, description="Optional Specifies the list of tables/views excluded from the metadata based vector store.")
    sample_size: Optional[int] = Field(None, description="Optional Specifies the number of rows to sample tables/views for the metadata based vector store embeddings.")
    rerank_weight: Optional[float] = Field(None, description="Optional Specifies the weight to be used for reranking the search results.")
    relevance_top_k: Optional[int] = Field(None, description="Optional Specifies the number of top  similarity matches to be considered for reranking.")
    relevance_search_threshold: Optional[float] = Field(None, description="Optional Specifies the threshold value to be consider matching tables/views while reranking.")
    include_patterns: Optional[List[str]] = Field(None, description="Optional Specifies the list of patterns to be included in the metadata based vector store.")
    exclude_patterns: Optional[List[str]] = Field(None, description="Optional Specifies the list of patterns to be excluded from the metadata based vector store.")
    batch: Optional[bool] = Field(None, description="Optional Specifies whether to use batch processing for embedding generation. Applicable only for AWS.")
    ignore_embedding_errors: Optional[bool] = Field(None, description="Optional Specifies whether to ignore embedding errors during embedding generation. Applicable only for AWS.")
    chat_completion_max_tokens: Optional[int] = Field(None, description="Optional Specifies the maximum number of tokens to be generated by chat completion model.")
    embeddings_base_url: Optional[str] = Field(None, description="Optional Specifies the base URL for the service to be used for embeddings.")
    completions_base_url: Optional[str] = Field(None, description="Optional Specifies the base URL for the service to be used for completions.")
    ranking_url: Optional[str] = Field(None, description="Optional Specifies the URL for the service to be used for reranking.")
    ingest_host: Optional[str] = Field(None, description="Optional Specifies the http host for document parsing.")
    ingest_port: Optional[int] = Field(None, description="Optional Specifies the port for document parsing.")
    
    
class VectorStoreUpdate(BaseModel):
    """Model for updating a Teradata VectorStore."""
    description: str = Field(..., description="Specifies the description of the VectorStore.")
    target_database: Optional[str] = Field(None, description="Specifies the target database where the VectorStore will be created.")
    object_names: str = Field(..., description="Specifies the table name(s)/teradataml DataFrame(s) to be indexed for vector store.")
    alter_operation: Literal["ADD", "DELETE"] = Field(..., description="Optional Specifies the alter operation such as ADD or DELETE to be performed on the VectorStore.")
    update_style: Optional[Literal["MINOR", "MAJOR"]] = Field(None, description="Optional Specifies the update style to be used for the VectorStore.")
    embeddings_model: str = Field(None, description="Optional Specifies the embedding model to be used for vectorization.")
    embeddings_dims: Optional[int] = Field(None, description="Optional Specifies the number of dimensions for the embeddings.")
    metric: Optional[str] = Field(None, description="Optional Specifies the metric to be used for calculating the distance between the vectors.")
    search_algorithm: Optional[str] = Field(None, description="Optional Specifies the search algorithm to be used for similarity search.")
    initial_centroids_method: Optional[str] = Field(None, description="Optional Specifies the method to be used for initializing centroids.")
    train_numclusters: Optional[int] = Field(None, description="Optional Specifies the number of clusters to be used for training.")
    max_iternum: Optional[int] = Field(None, description="Optional Specifies the maximum number of iterations for training.")
    stop_threshold: Optional[float] = Field(None, description="Optional Specifies the threshold for stopping the training process.")
    seed: Optional[int] = Field(None, description="Optional Specifies the seed value for random number generation.")
    num_init: Optional[int] = Field(None, description="Optional Specifies the number of initializations to be performed for k-means.")
    top_k: Optional[int] = Field(None, description="Optional Specifies the number of top results to be returned for similarity search.")
    search_threshold: Optional[float] = Field(None, description="OptionalSpecifies the threshold value to consider for matching tables/views while searching.")
    search_numcluster: Optional[int] = Field(None, description="Optional Specifies the number of clusters to be used for searching.")
    prompt: Optional[str] = Field(None, description="Optional Specifies the prompt to be used by language model to generate responses using top matches.")
    chat_completion_model: Optional[str] = Field(None, description="Optional Specifies the chat completion model to be used for generating responses.")
    document_files: Optional[List[str]] = Field(None, description="Optional Specifies the list of document files to be indexed for vector store.")
    ef_search: Optional[int] = Field(None, description="Optional Specifies the number of neighbors to be considered for hnsw algorithm during similarity search.")
    num_layers: Optional[int] = Field(None, description="Optional Specifies the maximum number of layers to be used for hnsw algorithm during vector store creation.")
    ef_construction: Optional[int] = Field(None, description="Optional Specifies the number of neighbors to be considered for hnsw algorithm during vector store creation.")
    num_connpernode: Optional[int] = Field(None, description="Optional Specifies the number of connections per node to be used for hnsw algorithm during vector store creation.")
    maxnum_connpernode: Optional[int] = Field(None, description="Optional Specifies the maximum number of connections per node to be used for hnsw algorithm during vector store creation.")
    apply_heuristics: Optional[bool] = Field(None, description="Optional Specifies whether to apply heuristics for hnsw algorithm during vector store creation.")
    include_objects: Optional[List[str]] = Field(None, description="Optional Specifies the list of tables/views included in the metadata based vector store.")
    exclude_objects: Optional[List[str]] = Field(None, description="Optional Specifies the list of tables/views excluded from the metadata based vector store.")
    sample_size: Optional[int] = Field(None, description="Optional Specifies the number of rows to sample tables/views for the metadata based vector store embeddings.")
    rerank_weight: Optional[float] = Field(None, description="Optional Specifies the weight to be used for reranking the search results.")
    relevance_top_k: Optional[int] = Field(None, description="Optional Specifies the number of top  similarity matches to be considered for reranking.")
    relevance_search_threshold: Optional[float] = Field(None, description="Optional Specifies the threshold value to be consider matching tables/views while reranking.")
    include_patterns: Optional[List[str]] = Field(None, description="Optional Specifies the list of patterns to be included in the metadata based vector store.")
    exclude_patterns: Optional[List[str]] = Field(None, description="Optional Specifies the list of patterns to be excluded from the metadata based vector store.")
    ignore_embedding_errors: Optional[bool] = Field(None, description="Optional Specifies whether to ignore embedding errors during embedding generation. Applicable only for AWS.")
    chat_completion_max_tokens: Optional[int] = Field(None, description="Optional Specifies the maximum number of tokens to be generated by chat completion model.")
