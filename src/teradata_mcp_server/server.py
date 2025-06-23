import os
import asyncio
import logging
import signal
import json
import yaml
from typing import Any, List
from pydantic import Field
import mcp.types as types
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts.base import UserMessage, TextContent
from dotenv import load_dotenv


# Import the ai_tools module, clone-and-run friendly
try:
    from teradata_mcp_server import tools as td
except ImportError:
    import tools as td

load_dotenv()

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.ERROR,
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
    """Execute a database tool with the given connection and arguments."""
    global _tdconn
    try:
        if not _tdconn.conn:
            logger.info("Reinitializing TDConn")
            _tdconn = td.TDConn()  # Reinitialize connection if not connected
        return format_text_response(tool(_tdconn, *args, **kwargs))
    except Exception as e:
        logger.error(f"Error sampling object: {e}")
        return format_error_response(str(e))
    
#------------------ Base Tools  ------------------#

@mcp.tool(description="Executes a SQL query to read from the database.")
async def get_base_readQuery(
    sql: str = Field(description="SQL that reads from the database to run", default=""),
    ) -> ResponseType:
    """Executes a SQL query to read from the database."""
    return execute_db_tool( td.handle_get_base_readQuery, sql=sql) 


@mcp.tool(description="Executes a SQL query to write to the database.")
async def write_base_writeQuery(
    sql: str = Field(description="SQL that writes to the database to run", default=""),
    ) -> ResponseType:
    """Executes a SQL query to write to the database."""
    return execute_db_tool( td.handle_write_base_writeQuery, sql=sql) 


@mcp.tool(description="Display table DDL definition.")
async def get_base_tableDDL(
    db_name: str = Field(description="Database name", default=""),
    table_name: str = Field(description="table name", default=""),
    ) -> ResponseType:
    """Display table DDL definition."""
    return execute_db_tool( td.handle_get_base_tableDDL, db_name=db_name, table_name=table_name)    

@mcp.tool(description="List all databases in the Teradata System.")
async def get_base_databaseList() -> ResponseType:
    """List all databases in the Teradata System."""
    return execute_db_tool( td.handle_get_base_databaseList)


@mcp.tool(description="List objects in a database.")
async def get_base_tableList(
    db_name: str = Field(description="database name", default=""),
    ) -> ResponseType:
    """List objects in a database."""
    return execute_db_tool( td.handle_get_base_tableList, db_name=db_name)


@mcp.tool(description="Show detailed column information about a database table.")
async def get_base_columnDescription(
    db_name: str = Field(description="Database name", default=""),
    obj_name: str = Field(description="table name", default=""),
    ) -> ResponseType:
    """Show detailed column information about a database table."""
    return execute_db_tool( td.handle_get_base_columnDescription, db_name=db_name, obj_name=obj_name)


@mcp.tool(description="Get data samples and structure overview from a database table.")
async def get_base_tablePreview(
    db_name: str = Field(description="Database name", default=""),
    table_name: str = Field(description="table name", default=""),
    ) -> ResponseType:
    """Get data samples and structure overview from a database table."""
    return execute_db_tool( td.handle_get_base_tablePreview, table_name=table_name, db_name=db_name)

@mcp.tool(description="Get tables commonly used together by database users, this is helpful to infer relationships between tables.")
async def get_base_tableAffinity(
    db_name: str = Field(description="Database name", default=""),
    obj_name: str = Field(description="Table or view name", default=""),
    ) -> ResponseType:
    """Get tables commonly used together by database users, this is helpful to infer relationships between tables."""
    return execute_db_tool( td.handle_get_base_tableAffinity, obj_name=obj_name, db_name=db_name)


@mcp.tool(description="Measure the usage of a table and views by users in a given schema, this is helpful to infer what database objects are most actively used or drive most value.")
async def get_base_tableUsage(
    db_name: str = Field(description="Database name", default=""),
    ) -> ResponseType:
    """Measure the usage of a table and views by users in a given schema, this is helpful to infer what database objects are most actively used or drive most value."""
    return execute_db_tool( td.handle_get_base_tableUsage, db_name=db_name)

@mcp.prompt()
async def base_query(qry: str) -> UserMessage:
    """Create a SQL query against the database"""
    return UserMessage(role="user", content=TextContent(type="text", text=td.handle_base_query.format(qry=qry)))

@mcp.prompt()
async def base_tableBusinessDesc(database_name: str, table_name: str) -> UserMessage:
    """Create a business description of the table and columns."""
    return UserMessage(role="user", content=TextContent(type="text", text=td.handle_base_tableBusinessDesc.format(database_name=database_name, table_name=table_name)))

@mcp.prompt()
async def base_databaseBusinessDesc(database_name: str) -> UserMessage:
    """Create a business description of the database."""
    return UserMessage(role="user", content=TextContent(type="text", text=td.handle_base_databaseBusinessDesc.format(database_name=database_name)))

#------------------ DBA Tools  ------------------#

@mcp.tool(description="Get a list of SQL run by a user in the last number of days if a user name is provided, otherwise get list of all SQL in the last number of days.")
async def get_dba_userSqlList(
    user_name: str = Field(description="user name", default=""),
    no_days: int = Field(description="number of days to look back", default=7),
    ) -> ResponseType:
    """Get a list of SQL run by a user."""
    return execute_db_tool( td.handle_get_dba_userSqlList, user_name=user_name, no_days=no_days)

@mcp.tool(description="Get a list of SQL run against a table in the last number of days ")
async def get_dba_tableSqlList(
    table_name: str = Field(description="table name", default=""),
    no_days: int = Field(description="number of days to look back", default=7),
    ) -> ResponseType:
    """Get a list of SQL run by a user."""
    return execute_db_tool( td.handle_get_dba_tableSqlList, table_name=table_name, no_days=no_days)

@mcp.tool(description="Get table space used for a table if table name is provided or get table space for all tables in a database if a database name is provided.")
async def get_dba_tableSpace(
    db_name: str = Field(description="Database name", default=""),
    table_name: str = Field(description="table name", default=""),
    ) -> ResponseType:
    """Get table space used for a table if table name is provided or get table space for all tables in a database if a database name is provided."""
    return execute_db_tool( td.handle_get_dba_tableSpace, db_name=db_name, table_name=table_name)

@mcp.tool(description="Get database space if database name is provided, otherwise get all databases space allocations.")
async def get_dba_databaseSpace(
    db_name: str = Field(description="Database name", default=""),
    ) -> ResponseType:
    """Get database space if database name is provided, otherwise get all databases space allocations."""
    return execute_db_tool( td.handle_get_dba_databaseSpace, db_name=db_name)

@mcp.tool(description="Get Teradata database version information.")
async def get_dba_databaseVersion() -> ResponseType:
    """Get Teradata database version information."""
    return execute_db_tool( td.handle_get_dba_databaseVersion)

@mcp.tool(description="Get the Teradata system usage summary metrics by weekday and hour for each workload type and query complexity bucket.")
async def get_dba_resusageSummary() -> ResponseType:
    """Get the Teradata system usage summary metrics by weekday and hour."""
    return execute_db_tool( td.handle_get_dba_resusageSummary, dimensions=["hourOfDay", "dayOfWeek"])

@mcp.tool(description="Get the Teradata system usage summary metrics by user on a specified date, or day of week and hour of day.")
async def get_dba_resusageUserSummary(
    user_name: str = Field(description="Database user name", default=""),
    date: str = Field(description="Date to analyze, formatted as `YYYY-MM-DD`", default=""),
    dayOfWeek: str = Field(description="Day of week to analyze", default=""),
    hourOfDay: str = Field(description="Hour of day to analyze", default=""),
    ) -> ResponseType:
    """Get the Teradata system usage summary metrics by user on a specified date, or day of week and hour of day."""
    return execute_db_tool( td.handle_get_dba_resusageSummary, dimensions=["UserName", "hourOfDay", "dayOfWeek"], user_name=user_name, date=date, dayOfWeek=dayOfWeek, hourOfDay=hourOfDay)

@mcp.tool(description="Get the Teradata flow control metrics.")
async def get_dba_flowControl() -> ResponseType:
    """Get the Teradata flow control metrics."""
    return execute_db_tool( td.handle_get_dba_flowControl)

@mcp.tool(description="Get the user feature usage metrics.")
async def get_dba_featureUsage() -> ResponseType:
    """Get the user feature usage metrics.""" 
    return execute_db_tool( td.handle_get_dba_featureUsage)

@mcp.tool(description="Get the Teradata user delay metrics.")
async def get_dba_userDelay() -> ResponseType:
    """Get the Teradata user delay metrics."""
    return execute_db_tool( td.handle_get_dba_userDelay)

@mcp.tool(description="Measure the usage of a table and views by users, this is helpful to understand what user and tables are driving most resource usage at any point in time.")
async def get_dba_tableUsageImpact(
    db_name: str = Field(description="Database name", default=""),
    user_name: str = Field(description="User name", default=""),    
    ) -> ResponseType:
    """Measure the usage of a table and views by users, this is helpful to understand what user and tables are driving most resource usage at any point in time."""
    return execute_db_tool( td.handle_get_dba_tableUsageImpact, db_name=db_name,  user_name=user_name)

@mcp.tool(description="Get the Teradata session information for user.")
async def get_dba_sessionInfo(
    user_name: str = Field(description="User name", default=""),
    ) -> ResponseType:
    """Get the Teradata session information for user."""
    return execute_db_tool( td.handle_get_dba_sessionInfo, user_name=user_name)


@mcp.prompt()
async def dba_databaseHealthAssessment() -> UserMessage:
    """Create a database health assessment for a Teradata system."""
    return UserMessage(role="user", content=TextContent(type="text", text=td.handle_dba_databaseHealthAssessment))

@mcp.prompt()
async def dba_userActivityAnalysis() -> UserMessage:
    """Create a user activity analysis for a Teradata system."""
    return UserMessage(role="user", content=TextContent(type="text", text=td.handle_dba_userActivityAnalysis))

@mcp.prompt()
async def dba_tableArchive() -> UserMessage:
    """Create a table archive strategy for database tables."""
    return UserMessage(role="user", content=TextContent(type="text", text=td.handle_dba_tableArchive))

@mcp.prompt()
async def dba_databaseLineage(database_name: str, number_days: int) -> UserMessage:
    """Create a database lineage map for tables in a database."""
    return UserMessage(role="user", content=TextContent(type="text", text=td.handle_dba_databaseLineage.format(database_name=database_name, number_days=number_days)))

@mcp.prompt()
async def dba_tableDropImpact(database_name: str, table_name: str, number_days: int) -> UserMessage:
    """Assess the impact of dropping a table."""
    return UserMessage(role="user", content=TextContent(type="text", text=td.handle_dba_tableDropImpact.format(database_name=database_name, table_name=table_name, number_days=number_days)))

#------------------ Data Quality Tools  ------------------#

@mcp.tool(description="Get the column names that having missing values in a table.")
async def get_qlty_missingValues(
    table_name: str = Field(description="table name", default=""),
    ) -> ResponseType:
    """Get the column names that having missing values in a table."""
    return execute_db_tool( td.handle_get_qlty_missingValues, table_name=table_name)


@mcp.tool(description="Get the column names that having negative values in a table.")
async def get_qlty_negativeValues(
    table_name: str = Field(description="table name", default=""),
    ) -> ResponseType:
    """Get the column names that having negative values in a table."""
    return execute_db_tool( td.handle_get_qlty_negativeValues, table_name=table_name)

@mcp.tool(description="Get the destinct categories from column in a table.")
async def get_qlty_distinctCategories(
    table_name: str = Field(description="table name", default=""),
    col_name: str = Field(description="column name", default=""),
    ) -> ResponseType:
    """Get the destinct categories from column in a table."""
    return execute_db_tool( td.handle_get_qlty_distinctCategories, table_name=table_name, col_name=col_name)

@mcp.tool(description="Get the standard deviation from column in a table.")
async def get_qlty_standardDeviation(
    table_name: str = Field(description="table name", default=""),
    col_name: str = Field(description="column name", default=""),
    ) -> ResponseType:
    """Get the standard deviation from column in a table."""
    return execute_db_tool( td.handle_get_qlty_standardDeviation, table_name=table_name, col_name=col_name)


@mcp.prompt()
async def qlty_databaseQuality(database_name: str) -> UserMessage:
    """Assess the data quality of a database."""
    return UserMessage(role="user", content=TextContent(type="text", text=td.handle_qlty_databaseQuality.format(database_name=database_name)))

# ------------------ RAG Tools ------------------ #

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
async def rag_set_config(
    query_db: str = Field(description="Database to store user questions and query embeddings"),
    model_db: str = Field(description="Database where the embedding model is stored"),
    vector_db: str = Field(description="Database containing the chunk vector store"),
    vector_table: str = Field(description="Table containing chunk embeddings for similarity search"),
) -> ResponseType:
    return execute_db_tool( _tdconn, td.handle_set_rag_config, query_db=query_db, model_db=model_db, vector_db=vector_db, vector_table=vector_table,)

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
async def store_user_query(
    db_name: str = Field(..., description="Name of the Teradata database where the question will be stored."),
    table_name: str = Field(..., description="Name of the table to store user questions (e.g., 'pdf_user_queries')."),
    question: str = Field(..., description="Natural language question from the user. Can optionally start with '/rag '."),
) -> ResponseType:
    return execute_db_tool( td.handle_store_user_query, db_name=db_name, table_name=table_name, question=question)

@mcp.tool(
    description=(
        "Tokenizes the latest user-submitted question using the tokenizer specified in the current RAG configuration. "
        "This tool must be used *after* calling 'configure_rag' (to initialize the config) and 'store_user_query' (to capture a user question). "
        "It selects the most recent row from the query table (e.g., 'pdf_topics_of_interest'), runs it through the ONNX tokenizer, "
        "and creates a temporary view '<query_db>.v_topics_tokenized' containing 'id', 'txt', 'input_ids', and 'attention_mask'. "
        "This view is used downstream to generate vector embeddings for similarity search."
    )
)
async def tokenize_query() -> ResponseType:
    return execute_db_tool( td.create_tokenized_view)

@mcp.tool(
    description=(
        "Generates sentence embeddings for the most recent tokenized user query using the model specified in the RAG configuration. "
        "Reads from the view `<db>.v_topics_tokenized` and applies the ONNX model from `<model_db>.embeddings_models`. "
        "Creates or replaces the view `<db>.v_topics_embeddings` which includes the original input and a `sentence_embedding` column. "
        "This must be run *after* create_tokenized_view and before vector_to_columns()."
    )
)
async def create_embedding_view() -> ResponseType:
    return execute_db_tool( td.create_embedding_view)

@mcp.tool(
    description=(
        "Converts the sentence embedding from the view `v_topics_embeddings` into 384 vector columns using `ivsm.vector_to_columns`. "
        "Creates or replaces a physical table to store the latest query embeddings for use in similarity search. "
        "The table location is defined via `rag_set_config`. "
        "This tool must be run *after* `create_embedding_view` and before `semantic_search_chunks`."
    )
)
async def create_query_embedding_table() -> ResponseType:
    return execute_db_tool( td.handle_create_query_embeddings)

@mcp.tool(
    description=(
        "Retrieve top-k most relevant PDF chunks for the user's latest embedded query. "
        "This tool is part of the RAG workflow and should be called after the query has been embedded. "
        "If the RAG config has not been set, use `rag_set_config` first to define where queries, models, and chunk embeddings are stored. "
        "Uses cosine similarity via `TD_VECTORDISTANCE` to compare embeddings. "
        "Each result includes similarity score, chunk text, page number, chunk number, and document name."
    )
)
async def semantic_search_chunks(
    k: int = Field(10, description="Number of top matching chunks to retrieve."),
) -> ResponseType:
    return execute_db_tool( td.handle_semantic_search, topk=k)

#------------------ Security Tools  ------------------#


@mcp.tool(description="Get permissions for a user.")
async def get_sec_userDbPermissions(
    user_name: str = Field(description="User name", default=""),
    ) -> ResponseType:
    """Get permissions for a user."""
    return execute_db_tool( td.handle_get_sec_userDbPermissions, user_name=user_name)


@mcp.tool(description="Get permissions for a role.")
async def get_sec_rolePermissions(
    role_name: str = Field(description="Role name", default=""),
    ) -> ResponseType:
    """Get permissions for a role."""
    return execute_db_tool( td.handle_get_sec_rolePermissions, role_name=role_name)


@mcp.tool(description="Get roles assigned to a user.")
async def get_sec_userRoles(
    user_name: str = Field(description="User name", default=""),
    ) -> ResponseType:
    """Get roles assigned to a user."""
    return execute_db_tool( td.handle_get_sec_userRoles, user_name=user_name)


@mcp.prompt()
async def rag_guidelines() -> UserMessage:
    return UserMessage(role="user", content=TextContent(type="text", text=td.rag_guidelines))

#------------------ Custom Tools  ------------------#
# Custom tools are defined as SQL queries in a YAML file and loaded at startup.


query_defs = []
custom_tool_files = [file for file in os.listdir() if file.endswith("_tools.yaml")]

for file in custom_tool_files:
    with open(file) as f:
        query_defs.extend(yaml.safe_load(f))  # Concatenate all query definitions


def make_custom_query_tool(sql_text: str, tool_name: str, desc: str):
    async def _dynamic_tool():
        # SQL is closed over without parameters
        return execute_db_tool( td.handle_execute_read_query, sql=sql_text)
    _dynamic_tool.__name__ = tool_name
    return mcp.tool(description=desc)(_dynamic_tool)

# Instantiate custom query tools from YAML
for q in query_defs:
    fn = make_custom_query_tool(q["sql"], q["name"], q.get("description", ""))
    globals()[q["name"]] = fn
    logger.info(f"Created custom tool: {q["name"]}")

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