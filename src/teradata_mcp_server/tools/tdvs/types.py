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

from typing import Literal

from pydantic import BaseModel, Field


class VectorStoreSimilaritySearch(BaseModel):
    """Model for performing similarity search for a question in Teradata VectorStore."""
    question: str = Field(..., description="Specifies a string of text for which similarity search needs to be performed.")
    batch_data: str | None = Field(None, description="Optional Specifies the table name or teradataml DataFrame to be indexed for batch mode")
    batch_id_column: str | None = Field(None, description="Optional Specifies the ID column to be indexed for batch mode")
    batch_query_column: str | None = Field(None, description="Optional Specifies the query column to be indexed for batch mode.")


class VectorStoreAsk(BaseModel):
    """Model for asking a question to a VectorStore."""
    question: str = Field(..., description="The question to ask the VectorStore.")
    prompt: str | None = Field(None, description="Optional prompt to guide the response.")
    batch_data: str | None = Field(None, description="Optional Specifies the table name or teradataml DataFrame to be indexed for batch mode")
    batch_id_column: str | None = Field(None, description="Optional Specifies the ID column to be indexed for batch mode")
    batch_query_column: str | None = Field(None, description="Optional Specifies the query column to be indexed for batch mode.")


class VectorStoreCreate(BaseModel):
    """Model for creating a Teradata VectorStore."""
    description: str = Field(..., description="Specifies the description of the VectorStore.")
    target_database: str | None = Field(None, description="Specifies the target database where the VectorStore will be created.")
    object_names: str = Field(..., description="Specifies the table name(s)/teradataml DataFrame(s) to be indexed for vector store.")
    key_columns: list[str] = Field(None, description="Optional Specifies the name(s) of the key column(s) to be used for indexing.")
    data_columns: list[str] = Field(None, description="Optional Specifies the name(s) of the data column(s) to be used for embedding generation(vectorization).")
    vector_column: str | None = Field(None, description="Specifies the name of the column where the vectorized data will be stored.")
    chunk_size: int | None = Field(None, description="Optional Specifies the size of each chunk when dividing document files into chunks.")
    optimized_chunking: bool | None = Field(None, description="Optional Specifies whether an optimized splitting mechanism supplied by Teradata should be used.")
    header_height: int | None = Field(None, description="Optional Specifies the height of the header in the document file.")
    footer_height: int | None = Field(None, description="Optional Specifies the height of the footer in the document file.")
    embeddings_model: str = Field(None, description="Optional Specifies the embedding model to be used for vectorization.")
    embeddings_dims: int | None = Field(None, description="Optional Specifies the number of dimensions for the embeddings.")
    metric: str | None = Field(None, description="Optional Specifies the metric to be used for calculating the distance between the vectors.")
    search_algorithm: str | None = Field(None, description="Optional Specifies the search algorithm to be used for similarity search.")
    initial_centroids_method: str | None = Field(None, description="Optional Specifies the method to be used for initializing centroids.")
    train_numclusters: int | None = Field(None, description="Optional Specifies the number of clusters to be used for training.")
    max_iternum: int | None = Field(None, description="Optional Specifies the maximum number of iterations for training.")
    stop_threshold: float | None = Field(None, description="Optional Specifies the threshold for stopping the training process.")
    seed: int | None = Field(None, description="Optional Specifies the seed value for random number generation.")
    num_init: int | None = Field(None, description="Optional Specifies the number of initializations to be performed for k-means.")
    top_k: int | None = Field(None, description="Optional Specifies the number of top results to be returned for similarity search.")
    search_threshold: float | None = Field(None, description="OptionalSpecifies the threshold value to consider for matching tables/views while searching.")
    search_numcluster: int | None = Field(None, description="Optional Specifies the number of clusters to be used for searching.")
    prompt: str | None = Field(None, description="Optional Specifies the prompt to be used by language model to generate responses using top matches.")
    chat_completion_model: str | None = Field(None, description="Optional Specifies the chat completion model to be used for generating responses.")
    document_files: list[str] | None = Field(None, description="Optional Specifies the list of document files to be indexed for vector store.")
    ef_search: int | None = Field(None, description="Optional Specifies the number of neighbors to be considered for hnsw algorithm during similarity search.")
    num_layers: int | None = Field(None, description="Optional Specifies the maximum number of layers to be used for hnsw algorithm during vector store creation.")
    ef_construction: int | None = Field(None, description="Optional Specifies the number of neighbors to be considered for hnsw algorithm during vector store creation.")
    num_connpernode: int | None = Field(None, description="Optional Specifies the number of connections per node to be used for hnsw algorithm during vector store creation.")
    maxnum_connpernode: int | None = Field(None, description="Optional Specifies the maximum number of connections per node to be used for hnsw algorithm during vector store creation.")
    apply_heuristics: bool | None = Field(None, description="Optional Specifies whether to apply heuristics for hnsw algorithm during vector store creation.")
    include_objects: list[str] | None = Field(None, description="Optional Specifies the list of tables/views included in the metadata based vector store.")
    exclude_objects: list[str] | None = Field(None, description="Optional Specifies the list of tables/views excluded from the metadata based vector store.")
    sample_size: int | None = Field(None, description="Optional Specifies the number of rows to sample tables/views for the metadata based vector store embeddings.")
    rerank_weight: float | None = Field(None, description="Optional Specifies the weight to be used for reranking the search results.")
    relevance_top_k: int | None = Field(None, description="Optional Specifies the number of top  similarity matches to be considered for reranking.")
    relevance_search_threshold: float | None = Field(None, description="Optional Specifies the threshold value to be consider matching tables/views while reranking.")
    include_patterns: list[str] | None = Field(None, description="Optional Specifies the list of patterns to be included in the metadata based vector store.")
    exclude_patterns: list[str] | None = Field(None, description="Optional Specifies the list of patterns to be excluded from the metadata based vector store.")
    batch: bool | None = Field(None, description="Optional Specifies whether to use batch processing for embedding generation. Applicable only for AWS.")
    ignore_embedding_errors: bool | None = Field(None, description="Optional Specifies whether to ignore embedding errors during embedding generation. Applicable only for AWS.")
    chat_completion_max_tokens: int | None = Field(None, description="Optional Specifies the maximum number of tokens to be generated by chat completion model.")
    embeddings_base_url: str | None = Field(None, description="Optional Specifies the base URL for the service to be used for embeddings.")
    completions_base_url: str | None = Field(None, description="Optional Specifies the base URL for the service to be used for completions.")
    ranking_url: str | None = Field(None, description="Optional Specifies the URL for the service to be used for reranking.")
    ingest_host: str | None = Field(None, description="Optional Specifies the http host for document parsing.")
    ingest_port: int | None = Field(None, description="Optional Specifies the port for document parsing.")


class VectorStoreUpdate(BaseModel):
    """Model for updating a Teradata VectorStore."""
    description: str = Field(..., description="Specifies the description of the VectorStore.")
    target_database: str | None = Field(None, description="Specifies the target database where the VectorStore will be created.")
    object_names: str = Field(..., description="Specifies the table name(s)/teradataml DataFrame(s) to be indexed for vector store.")
    alter_operation: Literal["ADD", "DELETE"] = Field(..., description="Optional Specifies the alter operation such as ADD or DELETE to be performed on the VectorStore.")
    update_style: Literal["MINOR", "MAJOR"] | None = Field(None, description="Optional Specifies the update style to be used for the VectorStore.")
    embeddings_model: str = Field(None, description="Optional Specifies the embedding model to be used for vectorization.")
    embeddings_dims: int | None = Field(None, description="Optional Specifies the number of dimensions for the embeddings.")
    metric: str | None = Field(None, description="Optional Specifies the metric to be used for calculating the distance between the vectors.")
    search_algorithm: str | None = Field(None, description="Optional Specifies the search algorithm to be used for similarity search.")
    initial_centroids_method: str | None = Field(None, description="Optional Specifies the method to be used for initializing centroids.")
    train_numclusters: int | None = Field(None, description="Optional Specifies the number of clusters to be used for training.")
    max_iternum: int | None = Field(None, description="Optional Specifies the maximum number of iterations for training.")
    stop_threshold: float | None = Field(None, description="Optional Specifies the threshold for stopping the training process.")
    seed: int | None = Field(None, description="Optional Specifies the seed value for random number generation.")
    num_init: int | None = Field(None, description="Optional Specifies the number of initializations to be performed for k-means.")
    top_k: int | None = Field(None, description="Optional Specifies the number of top results to be returned for similarity search.")
    search_threshold: float | None = Field(None, description="OptionalSpecifies the threshold value to consider for matching tables/views while searching.")
    search_numcluster: int | None = Field(None, description="Optional Specifies the number of clusters to be used for searching.")
    prompt: str | None = Field(None, description="Optional Specifies the prompt to be used by language model to generate responses using top matches.")
    chat_completion_model: str | None = Field(None, description="Optional Specifies the chat completion model to be used for generating responses.")
    document_files: list[str] | None = Field(None, description="Optional Specifies the list of document files to be indexed for vector store.")
    ef_search: int | None = Field(None, description="Optional Specifies the number of neighbors to be considered for hnsw algorithm during similarity search.")
    num_layers: int | None = Field(None, description="Optional Specifies the maximum number of layers to be used for hnsw algorithm during vector store creation.")
    ef_construction: int | None = Field(None, description="Optional Specifies the number of neighbors to be considered for hnsw algorithm during vector store creation.")
    num_connpernode: int | None = Field(None, description="Optional Specifies the number of connections per node to be used for hnsw algorithm during vector store creation.")
    maxnum_connpernode: int | None = Field(None, description="Optional Specifies the maximum number of connections per node to be used for hnsw algorithm during vector store creation.")
    apply_heuristics: bool | None = Field(None, description="Optional Specifies whether to apply heuristics for hnsw algorithm during vector store creation.")
    include_objects: list[str] | None = Field(None, description="Optional Specifies the list of tables/views included in the metadata based vector store.")
    exclude_objects: list[str] | None = Field(None, description="Optional Specifies the list of tables/views excluded from the metadata based vector store.")
    sample_size: int | None = Field(None, description="Optional Specifies the number of rows to sample tables/views for the metadata based vector store embeddings.")
    rerank_weight: float | None = Field(None, description="Optional Specifies the weight to be used for reranking the search results.")
    relevance_top_k: int | None = Field(None, description="Optional Specifies the number of top  similarity matches to be considered for reranking.")
    relevance_search_threshold: float | None = Field(None, description="Optional Specifies the threshold value to be consider matching tables/views while reranking.")
    include_patterns: list[str] | None = Field(None, description="Optional Specifies the list of patterns to be included in the metadata based vector store.")
    exclude_patterns: list[str] | None = Field(None, description="Optional Specifies the list of patterns to be excluded from the metadata based vector store.")
    ignore_embedding_errors: bool | None = Field(None, description="Optional Specifies whether to ignore embedding errors during embedding generation. Applicable only for AWS.")
    chat_completion_max_tokens: int | None = Field(None, description="Optional Specifies the maximum number of tokens to be generated by chat completion model.")
