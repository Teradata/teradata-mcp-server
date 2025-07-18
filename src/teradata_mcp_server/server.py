import os
import asyncio
import logging
import signal
import json
import yaml
from typing import Any, List, Optional
from pydantic import Field, BaseModel
import mcp.types as types
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts.base import UserMessage, TextContent
from dotenv import load_dotenv
import tdfs4ds
import teradataml as tdml
import inspect
from sqlalchemy.engine import Engine, Connection
import typing
# Import the ai_tools module, clone-and-run friendly
try:
    from teradata_mcp_server import tools as td
except ImportError:
    import tools as td

load_dotenv()

# Load tool configuration from YAML file
with open('configure_tools.yml', 'r') as file:
    config = yaml.safe_load(file)

# Set up logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(),
              logging.FileHandler(os.path.join("logs", "teradata_mcp_server.log"))],
)
logger = logging.getLogger("teradata_mcp_server")    
logger.info("Starting Teradata MCP server")

# Connect to MCP server
mcp = FastMCP("teradata-mcp-server")

#global shutdown flag
shutdown_in_progress = False

# Initiate connection to Teradata
_tdconn = td.TDConn()

#afm-defect:
_enableEVS = False
# Only attempt to connect to EVS is the system has an EVS installed/configured
if (len(os.getenv("VS_NAME", "").strip()) > 0):
    try:
        _evs    = td.get_evs()
        _enableEVS = True
    except:
        logger.error("Unable to establish connection to EVS, disabling")
        
#afm-defect: moved establish teradataml connection into main TDConn to enable auto-reconnect.
#td.teradataml_connection()



#------------------ Tool utilies  ------------------#
ResponseType = List[types.TextContent | types.ImageContent | types.EmbeddedResource]

def format_text_response(text: Any) -> ResponseType:
    """Format a text response."""
    if isinstance(text, str):
        try:
            # Try to parse as JSON if it's a string
            parsed = json.loads(text)
            return [types.TextContent(
                type="text", 
                text=json.dumps(parsed, indent=2, ensure_ascii=False)
            )]
        except json.JSONDecodeError:
            # If not JSON, return as plain text
            return [types.TextContent(type="text", text=str(text))]
    # For non-string types, convert to string
    return [types.TextContent(type="text", text=str(text))]

def format_error_response(error: str) -> ResponseType:
    """Format an error response."""
    return format_text_response(f"Error: {error}")

def execute_db_tool(tool, *args, **kwargs):
    """
    Execute a database tool with the given connection and arguments.
    Currently support both tools expecting DB API or SQLAlchemy engine:
      - If annotated Connection, pass SQLAlchemy engine
      - Otherwise, pass raw DB-API connection
    The second option should be eventually retired as all tools move to SQLAlchemy.
    """
    global _tdconn
    # (Re)initialize if needed
    if not getattr(_tdconn, "engine", None):
        logger.info("Reinitializing TDConn")
        _tdconn = td.TDConn()

    # Check is the first argument of the tool is a SQLAlchemy Connection
    sig = inspect.signature(tool)
    first_param = next(iter(sig.parameters.values()))
    ann = first_param.annotation
    use_sqla = inspect.isclass(ann) and issubclass(ann, Connection)

    try:
        if use_sqla:
            # Use a Connection that has .execute()
            with _tdconn.engine.connect() as conn:
                result = tool(conn, *args, **kwargs)
        else:
            # Raw DB-API path
            raw = _tdconn.engine.raw_connection()
            try:
                result = tool(raw, *args, **kwargs)
            finally:
                raw.close()

        return format_text_response(result)

    except Exception as e:
        logger.error(f"Error in execute_db_tool: {e}", exc_info=True)
        return format_error_response(str(e))
    

def execute_vs_tool(tool, *args, **kwargs) -> ResponseType:
    global _evs
    global _enableEVS

    if _enableEVS:
        try:
            return format_text_response(tool(_evs, *args, **kwargs))
        except Exception as e:
            if "401" in str(e) or "Session expired" in str(e):
                logger.warning("EVS session expired, refreshing …")
                _evs = td.evs_connect.refresh_evs()
                try:
                    return format_text_response(tool(_evs, *args, **kwargs))
                except Exception as retry_err:
                    logger.error(f"EVS retry failed: {retry_err}")
                    return format_error_response(f"After refresh, still failed: {retry_err}")
    
            logger.error(f"EVS tool error: {e}")
            return format_error_response(str(e))
    else:
        return format_error_response("Enterprise Vector Store is not available on this server.")

    

#------------------ Dynamic Tool Registration ------------------#

import inspect

def register_td_tools(config, td, mcp):
    """
    Dynamically register all handle_* functions in td as mcp.tool(),
    using config to enable/disable each tool.
    """
    for name, func in inspect.getmembers(td, inspect.isfunction):
        if not name.startswith("handle_"):
            continue
        tool_name = name.replace("handle_", "")
        # Find which config section this tool belongs to
        section = None
        for sec in ["base", "dba", "qlty"]:
            if tool_name.startswith(sec):
                section = sec
                break
        if not section:
            continue
        # Check if enabled in config
        if not (config.get(section, {}).get("allmodule") and config[section]["tool"].get(tool_name)):
            continue
        sig = inspect.signature(func)
        # Only include user parameters (skip connection, *args, **kwargs)
        params = [
            p for p in list(sig.parameters.values())[1:]  # skip first param (connection)
            if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        ]
        # Build dynamic async function
        async def dynamic_tool(*args, __func=func, __params=params):
            kwargs = {p.name: a for p, a in zip(__params, args)}
            return execute_db_tool(__func, **kwargs)
        # Set correct signature
        dynamic_tool.__signature__ = inspect.Signature(params)
        dynamic_tool.__name__ = tool_name
        dynamic_tool.__doc__ = func.__doc__ or ""
        # Register with mcp
        mcp.tool(name=tool_name, description=dynamic_tool.__doc__)(dynamic_tool)

register_td_tools(config, td, mcp)


# ------------------ DBA Prompts ------------------ #
if config['dba']['prompt']['dba_databaseHealthAssessment'] or config['dba']['allmodule']:
    @mcp.prompt()
    async def dba_databaseHealthAssessment() -> UserMessage:
        """Create a database health assessment for a Teradata system."""
        return UserMessage(role="user", content=TextContent(type="text", text=td.handle_dba_databaseHealthAssessment))

if config['dba']['prompt']['dba_userActivityAnalysis'] or config['dba']['allmodule']:
    @mcp.prompt()
    async def dba_userActivityAnalysis() -> UserMessage:
        """Create a user activity analysis for a Teradata system."""
        return UserMessage(role="user", content=TextContent(type="text", text=td.handle_dba_userActivityAnalysis))

if config['dba']['prompt']['dba_tableArchive']  or config['dba']['allmodule']:
    @mcp.prompt()
    async def dba_tableArchive() -> UserMessage:
        """Create a table archive strategy for database tables."""
        return UserMessage(role="user", content=TextContent(type="text", text=td.handle_dba_tableArchive))

if config['dba']['prompt']['dba_databaseLineage'] or config['dba']['allmodule']:
    @mcp.prompt()
    async def dba_databaseLineage(database_name: str, number_days: int) -> UserMessage:
        """Create a database lineage map for tables in a database."""
        return UserMessage(role="user", content=TextContent(type="text", text=td.handle_dba_databaseLineage.format(database_name=database_name, number_days=number_days)))

if config['dba']['prompt']['dba_tableDropImpact'] or config['dba']['allmodule']:
    @mcp.prompt()
    async def dba_tableDropImpact(database_name: str, table_name: str, number_days: int) -> UserMessage:
        """Assess the impact of dropping a table."""
        return UserMessage(role="user", content=TextContent(type="text", text=td.handle_dba_tableDropImpact.format(database_name=database_name, table_name=table_name, number_days=number_days)))

# ------------------ Quality Prompts ------------------ #

if config['qlty']['prompt']['qlty_databaseQuality'] or config['qlty']['allmodule']:
    @mcp.prompt()
    async def qlty_databaseQuality(database_name: str) -> UserMessage:
        """Assess the data quality of a database."""
        return UserMessage(role="user", content=TextContent(type="text", text=td.handle_qlty_databaseQuality.format(database_name=database_name)))


# ------------------ RAG Tools ------------------ #

if config['rag']['allmodule']:
    if config['rag']['tool']['rag_setConfig']:
        @mcp.tool(description="""
        Set the configuration for the current Retrieval-Augmented Generation (RAG) session.
        This MUST be called before any other RAG-related tools.

        The following values are hardcoded:
        - query_table = 'user_query'
        - query_embedding_store = 'user_query_embeddings'
        - model_id = 'bge-small-en-v1.5'

        You only need to provide the database locations:
        - query_db: where user queries and query embeddings will be stored
        - model_db: where the embedding model metadata is stored
        - vector_db + vector_table: where PDF chunk embeddings are stored

        Once this configuration is set, all other RAG tools will reuse it automatically.
        """)
        async def rag_setConfig(
            query_db: str = Field(description="Database to store user questions and query embeddings"),
            model_db: str = Field(description="Database where the embedding model is stored"),
            vector_db: str = Field(description="Database containing the chunk vector store"),
            vector_table: str = Field(description="Table containing chunk embeddings for similarity search"),
        ) -> ResponseType:
            return execute_db_tool( td.handle_rag_setConfig, query_db=query_db, model_db=model_db, vector_db=vector_db, vector_table=vector_table,)

    if config['rag']['tool']['rag_storeUserQuery']:
        @mcp.tool(
            description=(
                "Store a user's natural language question as the first step in a Retrieval-Augmented Generation (RAG) workflow."
                "This tool should always be run **before any embedding or similarity search** steps."
                "It inserts the raw question into a Teradata table specified by `db_name` and `table_name`. "
                "If the question starts with the prefix '/rag ', the prefix is automatically stripped before storage. "
                "Each question is appended as a new row with a generated ID and timestamp."
                "If the specified table does not exist, it will be created with columns: `id`, `txt`, and `created_ts`."
                "Returns the inserted row ID and cleaned question text."
                "This tool is **only needed once per user question** — downstream embedding and vector search tools "
                "can then reference this ID or re-use the stored question text."
            )
        )
        async def rag_storeUserQuery(
            db_name: str = Field(..., description="Name of the Teradata database where the question will be stored."),
            table_name: str = Field(..., description="Name of the table to store user questions (e.g., 'pdf_user_queries')."),
            question: str = Field(..., description="Natural language question from the user. Can optionally start with '/rag '."),
        ) -> ResponseType:
            return execute_db_tool( td.handle_rag_storeUserQuery, db_name=db_name, table_name=table_name, question=question)

    if config['rag']['tool']['rag_tokenizeQuery']:
        @mcp.tool(
            description=(
                "Tokenizes the latest user-submitted question using the tokenizer specified in the current RAG configuration. "
                "This tool must be used *after* calling 'configure_rag' (to initialize the config) and 'store_user_query' (to capture a user question). "
                "It selects the most recent row from the query table (e.g., 'pdf_topics_of_interest'), runs it through the ONNX tokenizer, "
                "and creates a temporary view '<query_db>.v_topics_tokenized' containing 'id', 'txt', 'input_ids', and 'attention_mask'. "
                "This view is used downstream to generate vector embeddings for similarity search."
            )
        )
        async def rag_tokenizeQuery() -> ResponseType:
            return execute_db_tool( td.handle_rag_tokenizedQuery)

    if config['rag']['tool']['rag_createEmbeddingView']:
        @mcp.tool(
            description=(
                "Generates sentence embeddings for the most recent tokenized user query using the model specified in the RAG configuration. "
                "Reads from the view `<db>.v_topics_tokenized` and applies the ONNX model from `<model_db>.embeddings_models`. "
                "Creates or replaces the view `<db>.v_topics_embeddings` which includes the original input and a `sentence_embedding` column. "
                "This must be run *after* create_tokenized_view and before vector_to_columns()."
            )
        )
        async def rag_createEmbeddingView() -> ResponseType:
            return execute_db_tool( td.handle_rag_createEmbeddingView)

    if config['rag']['tool']['rag_createQueryEmbeddingTable']:
        @mcp.tool(
            description=(
                "Converts the sentence embedding from the view `v_topics_embeddings` into 384 vector columns using `ivsm.vector_to_columns`. "
                "Creates or replaces a physical table to store the latest query embeddings for use in similarity search. "
                "The table location is defined via `rag_set_config`. "
                "This tool must be run *after* `create_embedding_view` and before `semantic_search_chunks`."
            )
        )
        async def rag_createQueryEmbeddingTable() -> ResponseType:
            return execute_db_tool( td.handle_rag_createQueryEmbeddingTable)

    if config['rag']['tool']['rag_semanticSearchChunks']:
        @mcp.tool(
            description=(
                "Retrieve top-k most relevant PDF chunks for the user's latest embedded query. "
                "This tool is part of the RAG workflow and should be called after the query has been embedded. "
                "If the RAG config has not been set, use `rag_set_config` first to define where queries, models, and chunk embeddings are stored. "
                "Uses cosine similarity via `TD_VECTORDISTANCE` to compare embeddings. "
                "Each result includes similarity score, chunk text, page number, chunk number, and document name."
            )
        )
        async def rag_semanticSearchChunks(
            k: int = Field(10, description="Number of top matching chunks to retrieve."),
        ) -> ResponseType:
            return execute_db_tool( td.handle_rag_semanticSearchChunks, topk=k)

    if config['rag']['prompt']['rag_guidelines']:
        @mcp.prompt()
        async def rag_guidelines() -> UserMessage:
            return UserMessage(role="user", content=TextContent(type="text", text=td.rag_guidelines))


#------------------ Enterprise Vector Store Tools  ------------------#

# if config['evs']['allmodule']:
#     if config['evs']['tool']['evs_vectorStoreSimilaritySearch']:
#         @mcp.tool(description="Enterprise Vector Store similarity search")
#         async def evs_vectorStoreSimilaritySearch(
#             question: str = Field(description="Natural language question"),
#             top_k: int = Field(1, description="top matches to return"),
#         ) -> ResponseType:

#             return execute_vs_tool(
#                 td.evs_tools.handle_evs_vectorStoreSimilaritySearch,
#                 question=question,
#                 top_k=top_k,
#             )



#--------------- Feature Store Tools ---------------#
# Feature tools leveraging the tdfs4ds package.

if config['fs']['allmodule']:
    class FeatureStoreConfig(BaseModel):
        """
        Configuration class for the feature store. This model defines the metadata and catalog sources 
        used to organize and access features, processes, and datasets across data domains.
        """

        data_domain: Optional[str] = Field(
            default=None,
            description="The data domain associated with the feature store, grouping features within the same namespace."
        )

        entity: Optional[str] = Field(
            default=None,
            description="The list of entities, comma separated and in alphabetical order, upper case."
        )

        db_name: Optional[str] = Field(
            default=None,
            description="Name of the database where the feature store is hosted."
        )

        feature_catalog: Optional[str] = Field(
            default=None,
            description=(
                "Name of the feature catalog table. "
                "This table contains detailed metadata about features and entities."
            )
        )

        process_catalog: Optional[str] = Field(
            default=None,
            description=(
                "Name of the process catalog table. "
                "Used to retrieve information about feature generation processes, features, and associated entities."
            )
        )

        dataset_catalog: Optional[str] = Field(
            default=None,
            description=(
                "Name of the dataset catalog table. "
                "Used to list and manage available datasets within the feature store."
            )
        )

    fs_config = FeatureStoreConfig() 

    if config['fs']['tool']['fs_reconnect_to_database']:
        @mcp.tool(description="Reconnect to the Teradata database if the connection is lost.")
        async def reconnect_to_database() -> ResponseType:
            """Reconnect to Teradata database if connection is lost."""
            global _tdconn
            try:
                _tdconn = td.TDConn()
                td.teradataml_connection()
                return format_text_response("Reconnected to Teradata database successfully.")
            except Exception as e:
                logger.error(f"Error reconnecting to database: {e}")
                return format_error_response(str(e))

    if config['fs']['tool']['fs_setFeatureStoreConfig']:
        @mcp.tool(description="Set or update the feature store configuration (database and data domain).")
        async def fs_setFeatureStoreConfig(
            data_domain: Optional[str] = None,
            db_name: Optional[str] = None,
            entity: Optional[str] = None,
        ) -> ResponseType:
            if db_name:
                if tdfs4ds.connect(database=db_name):
                    logger.info(f"connected to the feature store of the {db_name} database")
                    # Reset data_domain if DB name changes
                    if not (fs_config.db_name and fs_config.db_name.upper() == db_name.upper()):
                        fs_config.data_domain = None
                    
                    fs_config.db_name = db_name
                    logger.info(f"connected to the feature store of the {db_name} database")
                    fs_config.feature_catalog = f"{db_name}.{tdfs4ds.FEATURE_CATALOG_NAME_VIEW}"
                    logger.info(f"feature catalog {fs_config.feature_catalog}")
                    fs_config.process_catalog = f"{db_name}.{tdfs4ds.PROCESS_CATALOG_NAME_VIEW}"
                    logger.info(f"process catalog {fs_config.process_catalog}")
                    fs_config.dataset_catalog = f"{db_name}.FS_V_FS_DATASET_CATALOG"  # <- fixed line
                    logger.info(f"dataset catalog {fs_config.dataset_catalog}")

            if fs_config.db_name is not None and data_domain is not None:
                sql_query_ = f"SEL count(*) AS N FROM {fs_config.feature_catalog} WHERE UPPER(data_domain) = '{data_domain.upper()}'"
                logger.info(f"{sql_query_}")
                result = tdml.execute_sql(sql_query_)
                logger.info(f"{result}")
                if result.fetchall()[0][0] > 0:
                    fs_config.data_domain = data_domain
                else:
                    fs_config.data_domain = None

            if fs_config.db_name is not None and fs_config.data_domain is not None and entity is not None:
                sql_query_ = f"SEL count(*) AS N FROM {fs_config.feature_catalog} WHERE UPPER(data_domain) = '{data_domain.upper()}' AND ENTITY_NAME = '{entity.upper()}'"
                logger.info(f"{sql_query_}")
                result = tdml.execute_sql(sql_query_)
                logger.info(f"{result}")
                if result.fetchall()[0][0] > 0:
                    fs_config.entity = entity
            return format_text_response(f"Feature store config updated: {fs_config.dict(exclude_none=True)}")

    if config['fs']['tool']['fs_getFeatureStoreConfig']:
        @mcp.tool(description="Display the current feature store configuration (database and data domain).")
        async def fs_getFeatureStoreConfig() -> ResponseType:
            return format_text_response(f"Current feature store config: {fs_config.dict(exclude_none=True)}")

    if config['fs']['tool']['fs_isFeatureStorePresent']:
        @mcp.tool(description=("Check if a feature store is present in the specified database." ))
        async def fs_isFeatureStorePresent(
            db_name: str = Field(..., description="Name of the database to check for a feature store.")
        ) -> ResponseType:
            return execute_db_tool(td.handle_fs_isFeatureStorePresent, db_name=db_name)

    if config['fs']['tool']['fs_featureStoreContent']:
        @mcp.tool(description=("Returns a summary of the feature store content. Use this to understand what data is available in the feature store"))
        async def fs_featureStoreContent(
        ) -> ResponseType:
            return execute_db_tool(td.handle_fs_featureStoreContent, fs_config=fs_config)

    if config['fs']['tool']['fs_getDataDomains']:
        @mcp.tool(description=( "List the available data domains. Requires a configured `db_name`  in the feature store config. Use this to explore which entities can be used when building a dataset."))
        async def fs_getDataDomains(
            entity: str = Field(..., description="The .")
        ) -> ResponseType:
            return execute_db_tool(td.handle_fs_getDataDomains, fs_config=fs_config)

    if config['fs']['tool']['fs_getFeatures']:
        @mcp.tool(description=("List the list of features. Requires a configured `db_name` and  `data_domain` in the feature store config. Use this to explore the features available ."))
        async def fs_getFeatures(
        ) -> ResponseType:
            return execute_db_tool(td.handle_fs_getFeatures, fs_config=fs_config)

    if config['fs']['tool']['fs_getAvailableDatasets']:
        @mcp.tool(description=("List the list of available datasets.Requires a configured `db_name` in the feature store config.Use this to explore the datasets that are available ."))
        async def fs_getAvailableDatasets(
        ) -> ResponseType:
            return execute_db_tool(td.handle_fs_getAvailableDatasets, fs_config=fs_config)

    if config['fs']['tool']['fs_getFeatureDataModel']:
        @mcp.tool(description=("Return the schema of the feature store.Requires a feature store in the configured database (`db_name`)."))
        async def fs_getFeatureDataModel(
        ) -> ResponseType:
            return execute_db_tool(td.handle_fs_getFeatureDataModel, fs_config=fs_config)


    if config['fs']['tool']['fs_getAvailableEntities']:
        @mcp.tool(description=("List the available entities for a given data domain. Requires a configured `db_name` and `data_domain` and  `entity` in the feature store config. Use this to explore which entities can be used when building a dataset."))
        async def fs_getAvailableEntities(
        ) -> ResponseType:
            return execute_db_tool(td.handle_fs_getAvailableEntities, fs_config=fs_config)

    if config['fs']['tool']['fs_createDataset']:
        @mcp.tool( description=("Create a dataset using selected features and an entity from the feature store. The dataset is created in the specified target database under the given name. Requires a configured feature store and data domain. Registers the dataset in the catalog automatically. Use this when you want to build and register a new dataset for analysis or modeling." ) )
        async def fs_createDataset(
            entity_name: str = Field(..., description="Entity for which the dataset will be created. Available entities are reported in the feature catalog."),
            feature_selection: list[str] = Field(..., description="List of features to include in the dataset. Available features are reported in the feature catalog."),
            dataset_name: str = Field(..., description="Name of the dataset to create."),
            target_database: str = Field(..., description="Target database where the dataset will be created.")
        ) -> ResponseType:
            return execute_db_tool(td.handle_fs_createDataset, fs_config=fs_config, entity_name=entity_name, feature_selection=feature_selection, dataset_name=dataset_name, target_database=target_database)


#------------------ Custom Objects  ------------------#
# Custom tools, resources and prompts are defined as SQL queries in a YAML file and loaded at startup.

custom_object_files = [file for file in os.listdir() if file.endswith("_objects.yaml")]
custom_objects = {}
custom_glossary = {}

for file in custom_object_files:
    with open(file) as f:
        loaded = yaml.safe_load(f)
        if loaded:
            custom_objects.update(loaded)  # Merge dictionaries


def make_custom_prompt(prompt_name: str, prompt: str, desc: str):
    async def _dynamic_prompt():
        # SQL is closed over without parameters
        return UserMessage(role="user", content=TextContent(type="text", text=prompt))
    _dynamic_prompt.__name__ = prompt_name
    return mcp.prompt(description=desc)(_dynamic_prompt)

def make_custom_query_tool(name, tool):
    param_defs = tool.get("parameters", {})
    # 1. Build Parameter objects
    parameters = []
    annotations = {}
    # param_defs is now a dict keyed by name
    for param_name, p in param_defs.items():
        type_hint = p.get("type_hint", str)    # e.g. int, float, str, etc.
        default = inspect.Parameter.empty if p.get("required", True) else p.get("default", None)
        parameters.append(
            inspect.Parameter(
                param_name,
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=default,
                annotation=type_hint
            )
        )
        annotations[param_name] = type_hint

    # 2. Create the new signature
    sig = inspect.Signature(parameters)

    # 3. Define your generic handler
    async def _dynamic_tool(**kwargs):
        """Dynamically generated tool for {name}"""
        missing = [n for n in annotations if n not in kwargs]
        if missing:
            raise ValueError(f"Missing parameters: {missing}")
        return execute_db_tool(td.handle_base_readQuery, tool["sql"], **kwargs)

    # 4. Inject signature & annotations
    _dynamic_tool.__signature__   = sig
    _dynamic_tool.__annotations__ = annotations

    # 5. Register with FastMCP
    return mcp.tool(
        name=name,
        description=tool.get("description", "")
    )(_dynamic_tool)

def generate_cube_query_tool(name, cube):
    """
    Generate a function to create aggregation SQL from a cube definition.

    :param cube: The cube definition
    :return: A SQL query string generator function taking dimensions and measures as comma-separated strings.
    """
    def _cube_query_tool(dimensions: str, measures: str) -> str:
        """
        Generate a SQL query string for the cube using the specified dimensions and measures.

        Args:
            dimensions (str): Comma-separated dimension names (keys in cube['dimensions']).
            measures (str): Comma-separated measure names (keys in cube['measures']).

        Returns:
            str: The generated SQL query.
        """
        dim_list_raw = [d.strip() for d in dimensions.split(",") if d.strip()]
        met_list_raw = [m.strip() for m in measures.split(",") if m.strip()]
        # Get dimension expressions from dictionary
        dim_list = ",\n  ".join([
            cube["dimensions"][d]["expression"] if d in cube["dimensions"] else d
            for d in dim_list_raw
        ])
        met_lines = []
        for measure in met_list_raw:
            mdef = cube["measures"].get(measure)
            if mdef is None:
                raise ValueError(f"Measure '{measure}' not found in cube '{name}'.")
            expr = mdef["expression"]
            met_lines.append(f"{expr} AS {measure}")
        met_block = ",\n  ".join(met_lines)
        sql = (
            "SELECT\n"
            f"  {dim_list},\n"
            f"  {met_block}\n"
            "FROM (\n"
            f"{cube['sql'].strip()}\n"
            ") AS c\n"
            f"GROUP BY {', '.join(dim_list_raw)};"
        )
        return sql
    return _cube_query_tool

def make_custom_cube_tool(name, cube):
    async def _dynamic_tool(dimensions, measures):
        # Accept dimensions and measures as comma-separated strings, parse to lists
        return execute_db_tool(
            td.handle_base_dynamicQuery,
            sql_generator=generate_cube_query_tool(name, cube),
            dimensions=dimensions,
            measures=measures
        )
    _dynamic_tool.__name__ = 'get_cube_' + name
    # Build allowed values and definitions for dimensions and measures
    dim_lines = []
    for name, d in cube.get('dimensions', {}).items():
        dim_lines.append(f"    - {name}: {d.get('description', '')}")
    measure_lines = []
    for name, m in cube.get('measures', {}).items():
        measure_lines.append(f"    - {name}: {m.get('description', '')}")
    _dynamic_tool.__doc__ = f"""
    Tool to query the cube '{name}'.
    {cube.get('description', '')}

    Expected inputs:
        dimensions (str): Comma-separated dimension names to group by. Allowed values:
{chr(10).join(dim_lines)}

        measures (str): Comma-separated measure names to aggregate (must match cube definition). Allowed values:
{chr(10).join(measure_lines)}

    Returns:
        Query result as a formatted response.
    """
    return mcp.tool(description=_dynamic_tool.__doc__)(_dynamic_tool)

# Instantiate custom query tools from YAML
custom_terms = []
for name, obj in custom_objects.items():
    obj_type = obj.get("type")
    if obj_type == "tool":
        fn = make_custom_query_tool(name, obj)
        globals()[name] = fn
        logger.info(f"Created custom tool: {name}")
    elif obj_type == "prompt":
        fn = make_custom_prompt(name, obj["prompt"], obj.get("description", ""))
        globals()[name] = fn
        logger.info(f"Created custom prompt: {name}")
    elif obj_type == "cube":
        fn = make_custom_cube_tool(name, obj)
        globals()[name] = fn
        logger.info(f"Created custom cube: {name}")
    elif obj_type == "glossary":
        # Remove the 'type' key to get just the terms
        custom_glossary = {k: v for k, v in obj.items() if k != "type"}
        logger.info(f"Added custom glossary entries for: {name}.")
    else:
        logger.info(f"Type {obj_type if obj_type else ''} for custom object {name} is {'unknown' if obj_type else 'undefined'}.")

    # Look for additional terms to add to the custom glossary (currently only measures and dimensions in cubes)
    for section in ("measures", "dimensions"):
        if section in obj:
            custom_terms.extend((term, details, name) for term, details in obj[section].items())

# Enrich glossary with terms from tools and cubes
for term, details, tool in custom_terms:
    term_key = term.strip()

    if term_key not in custom_glossary:
        # New glossary entry
        custom_glossary[term_key] = {
            "definition": details.get("description"),
            "synonyms": [],
            "tools": [tool]
        }
    else:
        # Existing glossary term → preserve definition, just add tool if missing
        if "tools" not in custom_glossary[term_key]:
            custom_glossary[term_key]["tools"] = []
        if tool not in custom_glossary[term_key]["tools"]:
            custom_glossary[term_key]["tools"].append(tool)

if custom_glossary:
    # Resource returning the entire glossary
    @mcp.resource("glossary://all")
    def get_glossary() -> ResponseType:
        """List all glossary terms."""
        return custom_glossary

    # Resource returning the entire glossary
    @mcp.resource("glossary://definitions")
    def get_glossary_definitions() -> ResponseType:
        """Returns all glossary terms with definitions."""
        return {term: details["definition"] for term, details in custom_glossary.items()}

    # Resource returning all information about a specific glossary term
    @mcp.resource("glossary://term/{term_name}")
    def get_glossary_term(term_name: str)  -> dict:
        """Return the definition, synonyms and associated tools of a specific glossary term."""
        term = custom_glossary.get(term_name)
        if term:
            return term
        else:
            return {"error": f"Glossary term not found: {term_name}"}

#------------------ Custom Tools  ------------------#
# Custom tools are defined as SQL queries in a YAML file and loaded at startup.

if config['cust']['allmodule']:
    query_defs = []
    custom_tool_files = [file for file in os.listdir() if file.endswith("_tools.yaml")]

    for file in custom_tool_files:
        with open(file) as f:
            query_defs.extend(yaml.safe_load(f))  # Concatenate all query definitions


    def make_custom_prompt(prompt: str, prompt_name: str, desc: str):
        async def _dynamic_prompt():
            # SQL is closed over without parameters
            return UserMessage(role="user", content=TextContent(type="text", text=prompt))
        _dynamic_prompt.__name__ = prompt_name
        return mcp.prompt(description=desc)(_dynamic_prompt)

    def make_custom_query_tool(sql_text: str, tool_name: str, desc: str):
        async def _dynamic_tool():
            # SQL is closed over without parameters
            return execute_db_tool( td.handle_base_readQuery, sql=sql_text)
        _dynamic_tool.__name__ = tool_name
        return mcp.tool(description=desc)(_dynamic_tool)

    # Instantiate custom query tools from YAML
    for q in query_defs:
        if q["type"] == "tool":
            fn = make_custom_query_tool(q["sql"], q["name"], q.get("description", ""))
            globals()[q["name"]] = fn
            logger.info(f"Created custom tool: {q["name"]}")
        elif q["type"] == "prompt":
            fn = make_custom_prompt(q["prompt"], q["name"], q.get("description", "") )
            globals()[q["name"]] = fn
            logger.info(f"Created custom prompt: {q["name"]}")
        else:
            logger.info("Custom yaml type is unnkown.")

#------------------ Main ------------------#
# Main function to start the MCP server
#     Description: Initializes the MCP server and sets up signal handling for graceful shutdown.
#         It creates a connection to the Teradata database and starts the server to listen for incoming requests.
#         The function uses asyncio to manage asynchronous operations and handle signals for shutdown.
#         If an error occurs during initialization, it logs a warning message.
async def main():
    global _tdconn
    
    mcp_transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    logger.info(f"MCP_TRANSPORT: {mcp_transport}")

    # Set up proper shutdown handling
    try:
        loop = asyncio.get_running_loop()
        signals = (signal.SIGTERM, signal.SIGINT)
        for s in signals:
            logger.info(f"Registering signal handler for {s.name}")
            loop.add_signal_handler(s, lambda s=s: asyncio.create_task(shutdown(s)))
    except NotImplementedError:
        # Windows doesn't support signals properly
        logger.warning("Signal handling not supported on Windows")
        pass
    
    # Start the MCP server
    if mcp_transport == "sse":
        mcp.settings.host = os.getenv("MCP_HOST")
        mcp.settings.port = int(os.getenv("MCP_PORT"))
        logger.info(f"Starting MCP server on {mcp.settings.host}:{mcp.settings.port}")
        await mcp.run_sse_async()
    elif mcp_transport == "streamable-http":
        mcp.settings.host = os.getenv("MCP_HOST")
        mcp.settings.port = int(os.getenv("MCP_PORT"))
        mcp.settings.streamable_http_path = os.getenv("MCP_PATH", "/mcp/")
        logger.info(f"Starting MCP server on {mcp.settings.host}:{mcp.settings.port} with path {mcp.settings.streamable_http_path}")
        await mcp.run_streamable_http_async()
    else:
        logger.info("Starting MCP server on stdin/stdout")
        await mcp.run_stdio_async()    

#------------------ Shutdown ------------------#
# Shutdown function to handle cleanup and exit
#     Arguments: sig (signal.Signals) - signal received for shutdown
#     Description: Cleans up resources and exits the server gracefully.
#         It sets a flag to indicate that shutdown is in progress and logs the received signal.
#         If the shutdown is already in progress, it forces an immediate exit.
#         The function uses os._exit to terminate the process with a specific exit code.
async def shutdown(sig=None):
    """Clean shutdown of the server."""
    global shutdown_in_progress, _tdconn
    
    logger.info("Shutting down server")
    if shutdown_in_progress:
        logger.info("Forcing immediate exit")
        os._exit(1)  # Use immediate process termination instead of sys.exit
    
    _tdconn.close()
    shutdown_in_progress = True
    if sig:
        logger.info(f"Received exit signal {sig.name}")
    os._exit(128 + sig if sig is not None else 0)


#------------------ Entry Point ------------------#
# Entry point for the script
#     Description: This script is designed to be run as a standalone program.
#         It loads environment variables, initializes logging, and starts the MCP server.
#         The main function is called to start the server and handle incoming requests.
#         If an error occurs during execution, it logs the error and exits with a non-zero status code.
if __name__ == "__main__":
    asyncio.run(main())