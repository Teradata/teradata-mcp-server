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

    
#------------------ Base Tools  ------------------#

if config['base']['allmodule']:
    if config['base']['tool']['base_readQuery']:
        @mcp.tool(description="Executes a SQL query to read from the database.")
        async def base_readQuery(
            sql: str = Field(description="SQL that reads from the database to run", default=""),
            ) -> ResponseType:
            """Executes a SQL query to read from the database."""
            return execute_db_tool( td.handle_base_readQuery, sql=sql) 

    if config['base']['tool']['base_writeQuery']:
        @mcp.tool(description="Executes a SQL query to write to the database.")
        async def base_writeQuery(
            sql: str = Field(description="SQL that writes to the database to run", default=""),
            ) -> ResponseType:
            """Executes a SQL query to write to the database."""
            return execute_db_tool( td.handle_base_writeQuery, sql=sql) 

    if config['base']['tool']['base_tableDDL']:
        @mcp.tool(description="Display table DDL definition.")
        async def base_tableDDL(
            db_name: str = Field(description="Database name", default=""),
            table_name: str = Field(description="table name", default=""),
            ) -> ResponseType:
            """Display table DDL definition."""
            return execute_db_tool( td.handle_base_tableDDL, db_name=db_name, table_name=table_name)    

    if config['base']['tool']['base_databaseList']:
        @mcp.tool(description="List all databases in the Teradata System.")
        async def base_databaseList() -> ResponseType:
            """List all databases in the Teradata System."""
            return execute_db_tool( td.handle_base_databaseList)

    if config['base']['tool']['base_tableList']:
        @mcp.tool(description="List objects in a database.")
        async def base_tableList(
            db_name: str = Field(description="database name", default=""),
            ) -> ResponseType:
            """List objects in a database."""
            return execute_db_tool( td.handle_base_tableList, db_name=db_name)

    if config['base']['tool']['base_columnDescription']:
        @mcp.tool(description="Show detailed column information about a database table.")
        async def base_columnDescription(
            db_name: str = Field(description="Database name", default=""),
            obj_name: str = Field(description="table name", default=""),
            ) -> ResponseType:
            """Show detailed column information about a database table."""
            return execute_db_tool( td.handle_base_columnDescription, db_name=db_name, obj_name=obj_name)

    if config['base']['tool']['base_tablePreview']:
        @mcp.tool(description="Get data samples and structure overview from a database table.")
        async def base_tablePreview(
            db_name: str = Field(description="Database name", default=""),
            table_name: str = Field(description="table name", default=""),
            ) -> ResponseType:
            """Get data samples and structure overview from a database table."""
            return execute_db_tool( td.handle_base_tablePreview, table_name=table_name, db_name=db_name)

    if config['base']['tool']['base_tableAffinity']:
        @mcp.tool(description="Get tables commonly used together by database users, this is helpful to infer relationships between tables.")
        async def base_tableAffinity(
            db_name: str = Field(description="Database name", default=""),
            obj_name: str = Field(description="Table or view name", default=""),
            ) -> ResponseType:
            """Get tables commonly used together by database users, this is helpful to infer relationships between tables."""
            return execute_db_tool( td.handle_base_tableAffinity, obj_name=obj_name, db_name=db_name)

    if config['base']['tool']['base_tableUsage']:
        @mcp.tool(description="Measure the usage of a table and views by users in a given schema, this is helpful to infer what database objects are most actively used or drive most value.")
        async def base_tableUsage(
            db_name: str = Field(description="Database name", default=""),
            ) -> ResponseType:
            """Measure the usage of a table and views by users in a given schema, this is helpful to infer what database objects are most actively used or drive most value."""
            return execute_db_tool( td.handle_base_tableUsage, db_name=db_name)

    if config['base']['prompt']['base_query']:
        @mcp.prompt()
        async def base_query(qry: str) -> UserMessage:
            """Create a SQL query against the database"""
            return UserMessage(role="user", content=TextContent(type="text", text=td.handle_base_query.format(qry=qry)))

    if config['base']['prompt']['base_tableBusinessDesc']:
        @mcp.prompt()
        async def base_tableBusinessDesc(database_name: str, table_name: str) -> UserMessage:
            """Create a business description of the table and columns."""
            return UserMessage(role="user", content=TextContent(type="text", text=td.handle_base_tableBusinessDesc.format(database_name=database_name, table_name=table_name)))

    if config['base']['prompt']['base_databaseBusinessDesc']:
        @mcp.prompt()
        async def base_databaseBusinessDesc(database_name: str) -> UserMessage:
            """Create a business description of the database."""
            return UserMessage(role="user", content=TextContent(type="text", text=td.handle_base_databaseBusinessDesc.format(database_name=database_name)))

#------------------ DBA Tools  ------------------#
if config['dba']['allmodule']:
    if config['dba']['tool']['dba_userSqlList']:
        @mcp.tool(description="Get a list of SQL run by a user in the last number of days if a user name is provided, otherwise get list of all SQL in the last number of days.")
        async def dba_userSqlList(
            user_name: str = Field(description="user name", default=""),
            no_days: int = Field(description="number of days to look back", default=7),
            ) -> ResponseType:
            """Get a list of SQL run by a user."""
            return execute_db_tool( td.handle_dba_userSqlList, user_name=user_name, no_days=no_days)

    if config['dba']['tool']['dba_tableSqlList']:
        @mcp.tool(description="Get a list of SQL run against a table in the last number of days ")
        async def dba_tableSqlList(
            table_name: str = Field(description="table name", default=""),
            no_days: int = Field(description="number of days to look back", default=7),
            ) -> ResponseType:
            """Get a list of SQL run by a user."""
            return execute_db_tool( td.handle_dba_tableSqlList, table_name=table_name, no_days=no_days)

    if config['dba']['tool']['dba_tableSpace']:
        @mcp.tool(description="Get table space used for a table if table name is provided or get table space for all tables in a database if a database name is provided.")
        async def dba_tableSpace(
            db_name: str = Field(description="Database name", default=""),
            table_name: str = Field(description="table name", default=""),
            ) -> ResponseType:
            """Get table space used for a table if table name is provided or get table space for all tables in a database if a database name is provided."""
            return execute_db_tool( td.handle_dba_tableSpace, db_name=db_name, table_name=table_name)

    if config['dba']['tool']['dba_databaseSpace']:
        @mcp.tool(description="Get database space if database name is provided, otherwise get all databases space allocations.")
        async def dba_databaseSpace(
            db_name: str = Field(description="Database name", default=""),
            ) -> ResponseType:
            """Get database space if database name is provided, otherwise get all databases space allocations."""
            return execute_db_tool( td.handle_dba_databaseSpace, db_name=db_name)

    if config['dba']['tool']['dba_databaseVersion']:
        @mcp.tool(description="Get Teradata database version information.")
        async def dba_databaseVersion() -> ResponseType:
            """Get Teradata database version information."""
            return execute_db_tool( td.handle_dba_databaseVersion)

    if config['dba']['tool']['dba_resusageSummary']:
        @mcp.tool(description="Get the Teradata system usage summary metrics by weekday and hour for each workload type and query complexity bucket.")
        async def dba_resusageSummary() -> ResponseType:
            """Get the Teradata system usage summary metrics by weekday and hour."""
            return execute_db_tool( td.handle_dba_resusageSummary, dimensions=["hourOfDay", "dayOfWeek"])

    if config['dba']['tool']['dba_resusageUserSummary']:
        @mcp.tool(description="Get the Teradata system usage summary metrics by user on a specified date, or day of week and hour of day.")
        async def dba_resusageUserSummary(
            user_name: str = Field(description="Database user name", default=""),
            date: str = Field(description="Date to analyze, formatted as `YYYY-MM-DD`", default=""),
            dayOfWeek: str = Field(description="Day of week to analyze", default=""),
            hourOfDay: str = Field(description="Hour of day to analyze", default=""),
            ) -> ResponseType:
            """Get the Teradata system usage summary metrics by user on a specified date, or day of week and hour of day."""
            return execute_db_tool( td.handle_dba_resusageSummary, dimensions=["UserName", "hourOfDay", "dayOfWeek"], user_name=user_name, date=date, dayOfWeek=dayOfWeek, hourOfDay=hourOfDay)

    if config['dba']['tool']['dba_flowControl']:
        @mcp.tool(description="Get the Teradata flow control metrics.")
        async def dba_flowControl() -> ResponseType:
            """Get the Teradata flow control metrics."""
            return execute_db_tool( td.handle_dba_flowControl)

    if config['dba']['tool']['dba_featureUsage']:
        @mcp.tool(description="Get the user feature usage metrics.")
        async def dba_featureUsage() -> ResponseType:
            """Get the user feature usage metrics.""" 
            return execute_db_tool( td.handle_dba_featureUsage)

    if config['dba']['tool']['dba_userDelay']:
        @mcp.tool(description="Get the Teradata user delay metrics.")
        async def dba_userDelay() -> ResponseType:
            """Get the Teradata user delay metrics."""
            return execute_db_tool( td.handle_dba_userDelay)

    if config['dba']['tool']['dba_tableUsageImpact']:
        @mcp.tool(description="Measure the usage of a table and views by users, this is helpful to understand what user and tables are driving most resource usage at any point in time.")
        async def dba_tableUsageImpact(
            db_name: str = Field(description="Database name", default=""),
            user_name: str = Field(description="User name", default=""),    
            ) -> ResponseType:
            """Measure the usage of a table and views by users, this is helpful to understand what user and tables are driving most resource usage at any point in time."""
            return execute_db_tool( td.handle_dba_tableUsageImpact, db_name=db_name,  user_name=user_name)

    if config['dba']['tool']['dba_sessionInfo']:
        @mcp.tool(description="Get the Teradata session information for user.")
        async def dba_sessionInfo(
            user_name: str = Field(description="User name", default=""),
            ) -> ResponseType:
            """Get the Teradata session information for user."""
            return execute_db_tool( td.handle_dba_sessionInfo, user_name=user_name)

    if config['dba']['prompt']['dba_databaseHealthAssessment']:
        @mcp.prompt()
        async def dba_databaseHealthAssessment() -> UserMessage:
            """Create a database health assessment for a Teradata system."""
            return UserMessage(role="user", content=TextContent(type="text", text=td.handle_dba_databaseHealthAssessment))

    if config['dba']['prompt']['dba_userActivityAnalysis']:
        @mcp.prompt()
        async def dba_userActivityAnalysis() -> UserMessage:
            """Create a user activity analysis for a Teradata system."""
            return UserMessage(role="user", content=TextContent(type="text", text=td.handle_dba_userActivityAnalysis))

    if config['dba']['prompt']['dba_tableArchive']:
        @mcp.prompt()
        async def dba_tableArchive() -> UserMessage:
            """Create a table archive strategy for database tables."""
            return UserMessage(role="user", content=TextContent(type="text", text=td.handle_dba_tableArchive))

    if config['dba']['prompt']['dba_databaseLineage']:
        @mcp.prompt()
        async def dba_databaseLineage(database_name: str, number_days: int) -> UserMessage:
            """Create a database lineage map for tables in a database."""
            return UserMessage(role="user", content=TextContent(type="text", text=td.handle_dba_databaseLineage.format(database_name=database_name, number_days=number_days)))

    if config['dba']['prompt']['dba_tableDropImpact']:
        @mcp.prompt()
        async def dba_tableDropImpact(database_name: str, table_name: str, number_days: int) -> UserMessage:
            """Assess the impact of dropping a table."""
            return UserMessage(role="user", content=TextContent(type="text", text=td.handle_dba_tableDropImpact.format(database_name=database_name, table_name=table_name, number_days=number_days)))

#------------------ Data Quality Tools  ------------------#

if config['qlty']['allmodule']:
    if config['qlty']['tool']['qlty_missingValues']:
        @mcp.tool(description="Get the column names that having missing values in a table.")
        async def qlty_missingValues(
            table_name: str = Field(description="table name", default=""),
            ) -> ResponseType:
            """Get the column names that having missing values in a table."""
            return execute_db_tool( td.handle_qlty_missingValues, table_name=table_name)

    if config['qlty']['tool']['qlty_negativeValues']:
        @mcp.tool(description="Get the column names that having negative values in a table.")
        async def qlty_negativeValues(
            table_name: str = Field(description="table name", default=""),
            ) -> ResponseType:
            """Get the column names that having negative values in a table."""
            return execute_db_tool( td.handle_qlty_negativeValues, table_name=table_name)

    if config['qlty']['tool']['qlty_distinctCategories']:
        @mcp.tool(description="Get the destinct categories from column in a table.")
        async def qlty_distinctCategories(
            table_name: str = Field(description="table name", default=""),
            col_name: str = Field(description="column name", default=""),
            ) -> ResponseType:
            """Get the destinct categories from column in a table."""
            return execute_db_tool( td.handle_qlty_distinctCategories, table_name=table_name, col_name=col_name)

    if config['qlty']['tool']['qlty_standardDeviation']:
        @mcp.tool(description="Get the standard deviation from column in a table.")
        async def qlty_standardDeviation(
            table_name: str = Field(description="table name", default=""),
            col_name: str = Field(description="column name", default=""),
            ) -> ResponseType:
            """Get the standard deviation from column in a table."""
            return execute_db_tool( td.handle_qlty_standardDeviation, table_name=table_name, col_name=col_name)

    if config['qlty']['tool']['qlty_columnSummary']:
        @mcp.tool(description="Get the column summary statistics for a table.")
        async def qlty_columnSummary(
            table_name: str = Field(description="table name", default=""),
            ) -> ResponseType:
            """Get the column summary statistics for a table."""
            return execute_db_tool( td.handle_qlty_columnSummary, table_name=table_name)

    if config['qlty']['tool']['qlty_univariateStatistics']:
        @mcp.tool(description="Get the univariate statistics for a table.")
        async def qlty_univariateStatistics(
            table_name: str = Field(description="table name", default=""),
            col_name: str = Field(description="column name", default=""),
            ) -> ResponseType:
            """Get the univariate statistics for a table."""
            return execute_db_tool( td.handle_qlty_univariateStatistics, table_name=table_name, col_name=col_name)

    if config['qlty']['tool']['qlty_rowsWithMissingValues']:
        @mcp.tool(description="Get the rows with missing values in a table.")
        async def qlty_rowsWithMissingValues(
            table_name: str = Field(description="table name", default=""),
            col_name: str = Field(description="column name", default=""),
            ) -> ResponseType:
            """Get the rows with missing values in a table."""
            return execute_db_tool( td.handle_qlty_rowsWithMissingValues, table_name=table_name, col_name=col_name)

    if config['qlty']['prompt']['qlty_databaseQuality']:
        @mcp.prompt()
        async def qlty_databaseQuality(database_name: str) -> UserMessage:
            """Assess the data quality of a database."""
            return UserMessage(role="user", content=TextContent(type="text", text=td.handle_qlty_databaseQuality.format(database_name=database_name)))

# ------------------ RAG Tools ------------------ #

if config['rag']['allmodule']:
    if config['rag']['tool']['rag_executeWorkflow']:
        
        # Get the RAG version from config
        rag_version = config['rag'].get('version', 'byom')  # Default to 'byom'
        
        if rag_version == 'byom':
            @mcp.tool(description="""
            Execute complete RAG workflow to answer user questions based on document context.
            This tool handles the entire RAG pipeline in a single step when a user query is tagged with /rag.

            WORKFLOW STEPS (executed automatically using ONNXEmbeddings):
            1. Configuration setup using hardcoded values
            2. Store user query with '/rag ' prefix stripping  
            3. Generate query embeddings (tokenization + embedding using mldb.ONNXEmbeddings)
            4. Perform semantic search against precomputed chunk embeddings
            5. Return context chunks for answer generation

            HARDCODED CONFIGURATION VALUES:
            - query_table = 'user_query'
            - query_embedding_store = 'user_query_embeddings'
            - model_id = 'bge-small-en-v1.5'
            - query_db = 'demo_db'
            - vector_db = 'demo_db'
            - model_db = 'demo_db'
            - vector_table = 'pdf_embeddings_store'
            - model_table = 'embeddings_models'
            - tokenizer_table = 'embeddings_tokenizers'

            TECHNICAL DETAILS:
            - Strips the '/rag ' prefix if present from user questions
            - Creates query table if it does not exist (columns: id, txt, created_ts)
            - Retrieves the most recent user question from the configured table
            - Uses the tokenizer and embedding model selected via model_id configuration
            - Runs tokenization and embedding using mldb.ONNXEmbeddings UDF
            - Stores resulting embeddings and metadata in the configured output table
            - Uses cosine similarity via TD_VECTORDISTANCE to compare embedded query against precomputed chunk embeddings
            - Returns the top-k matching chunks from the configured vector store
            - Each result includes chunk text, similarity score, chunk number, page number, and document name

            CRITICAL ANSWERING RULES:
            - Answer ONLY using retrieved chunks - no external knowledge, speculation, or inference
            - Quote source content directly without paraphrasing, summarizing, or rewriting
            - If no relevant context found: "Not enough information found in the provided context"
            - If partial context: "The available context does not fully answer the question"
            - Include document/page references when available (e.g., "On page 2 of 'demo_policy.pdf'...")
            - Execute entire workflow silently without showing function calls to user - only show final answer

            LANGUAGE RESTRICTIONS:
            - Do not say "According to the context" or "The context says" - just quote directly
            - Do not say "It can be inferred that..." - no inference allowed
            - Use exact or near-verbatim quotes only
            - No paraphrasing, summarizing, or adding transitions between quotes
            - Copy content precisely - no expansion or interpretation

            BEHAVIORAL REQUIREMENTS:
            - Execute all RAG workflow steps silently without showing tool calls to users
            - Only display final answers based strictly on retrieved context chunks
            - Do not use external knowledge or speculation - only quote retrieved content directly
            - RAG mode only triggers with explicit /rag prefix - do not enter RAG mode implicitly
            - Hide all tool execution steps from user
            - Provide clean, direct response with only the answer based on retrieved chunks
            - This is a complete end-to-end RAG workflow - no additional tools needed

            EXECUTION: Run completely silently - user only sees their question and the final context-grounded answer.
            """)
            async def rag_executeWorkflow(
                question: str = Field(..., description="User's natural language question, optionally prefixed with '/rag '"),
                k: int = Field(10, description="Number of top matching chunks to retrieve for context"),
            ) -> ResponseType:
                return execute_db_tool(td.handle_rag_executeWorkflow, question=question, k=k)
                
        elif rag_version == 'ivsm':
            @mcp.tool(description="""
            Execute complete RAG workflow to answer user questions based on document context.
            This tool handles the entire RAG pipeline in a single step when a user query is tagged with /rag.

            WORKFLOW STEPS (executed automatically using IVSM functions):
            1. Configuration setup using hardcoded values
            2. Store user query with '/rag ' prefix stripping  
            3. Tokenize query using ivsm.tokenizer_encode
            4. Create embedding view using ivsm.IVSM_score
            5. Convert embeddings to vector columns using ivsm.vector_to_columns
            6. Perform semantic search against precomputed chunk embeddings

            HARDCODED CONFIGURATION VALUES:
            - query_table = 'user_query'
            - query_embedding_store = 'user_query_embeddings'
            - model_id = 'bge-small-en-v1.5'
            - query_db = 'demo_db'
            - vector_db = 'demo_db'
            - model_db = 'demo_db'
            - vector_table = 'pdf_embeddings_store'
            - model_table = 'embeddings_models'
            - tokenizer_table = 'embeddings_tokenizers'

            TECHNICAL DETAILS:
            - Strips the '/rag ' prefix if present from user questions
            - Creates query table if it does not exist (columns: id, txt, created_ts)
            - Selects the most recent row from the query table, runs it through the ONNX tokenizer
            - Creates temporary view v_topics_tokenized containing 'id', 'txt', 'input_ids', and 'attention_mask'
            - Reads from the tokenized view and applies the ONNX model to create embeddings
            - Creates or replaces embedding view v_topics_embeddings which includes the original input and sentence_embedding column
            - Converts the sentence embedding from the embedding view into vector columns for similarity search
            - Creates or replaces a physical table to store the latest query embeddings for use in similarity search
            - Uses cosine similarity via TD_VECTORDISTANCE to compare embedded query against precomputed chunk embeddings
            - Returns the top-k matching chunks from the configured vector store
            - Each result includes chunk text, similarity score, chunk number, page number, and document name

            CRITICAL ANSWERING RULES:
            - Answer ONLY using retrieved chunks - no external knowledge, speculation, or inference
            - Quote source content directly without paraphrasing, summarizing, or rewriting
            - If no relevant context found: "Not enough information found in the provided context"
            - If partial context: "The available context does not fully answer the question"
            - Include document/page references when available (e.g., "On page 2 of 'demo_policy.pdf'...")
            - Execute entire workflow silently without showing function calls to user - only show final answer

            LANGUAGE RESTRICTIONS:
            - Do not say "According to the context" or "The context says" - just quote directly
            - Do not say "It can be inferred that..." - no inference allowed
            - Use exact or near-verbatim quotes only
            - No paraphrasing, summarizing, or adding transitions between quotes
            - Copy content precisely - no expansion or interpretation

            BEHAVIORAL REQUIREMENTS:
            - Execute all RAG workflow steps silently without showing tool calls to users
            - Only display final answers based strictly on retrieved context chunks
            - Do not use external knowledge or speculation - only quote retrieved content directly
            - RAG mode only triggers with explicit /rag prefix - do not enter RAG mode implicitly
            - Hide all tool execution steps from user
            - Provide clean, direct response with only the answer based on retrieved chunks
            - This is a complete end-to-end RAG workflow using IVSM functions - no additional tools needed

            EXECUTION: Run completely silently - user only sees their question and the final context-grounded answer.
            """)
            async def rag_executeWorkflow(
                question: str = Field(..., description="User's natural language question, optionally prefixed with '/rag '"),
                k: int = Field(10, description="Number of top matching chunks to retrieve for context"),
            ) -> ResponseType:
                return execute_db_tool(td.handle_rag_executeWorkflow_ivsm, question=question, k=k)
        
        else:
            raise ValueError(f"Invalid RAG version: {rag_version}. Must be 'byom' or 'ivsm'")

    if config['rag']['prompt']['rag_guidelines']:
        @mcp.prompt()
        async def rag_guidelines() -> UserMessage:
            return UserMessage(
                role="user",
                content=TextContent(type="text", text=td.rag_guidelines)
            )
        
#------------------ Security Tools  ------------------#

if config['sec']['allmodule']:
    if config['sec']['tool']['sec_userDbPermissions']:
        @mcp.tool(description="Get permissions for a user.")
        async def sec_userDbPermissions(
            user_name: str = Field(description="User name", default=""),
            ) -> ResponseType:
            """Get permissions for a user."""
            return execute_db_tool( td.handle_sec_userDbPermissions, user_name=user_name)

    if config['sec']['tool']['sec_rolePermissions']:
        @mcp.tool(description="Get permissions for a role.")
        async def sec_rolePermissions(
            role_name: str = Field(description="Role name", default=""),
            ) -> ResponseType:
            """Get permissions for a role."""
            return execute_db_tool( td.handle_sec_rolePermissions, role_name=role_name)

    if config['sec']['tool']['sec_userRoles']:
        @mcp.tool(description="Get roles assigned to a user.")
        async def sec_userRoles(
            user_name: str = Field(description="User name", default=""),
            ) -> ResponseType:
            """Get roles assigned to a user."""
            return execute_db_tool( td.handle_sec_userRoles, user_name=user_name)


#------------------ Enterprise Vectore Store Tools  ------------------#

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