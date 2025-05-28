import os
import asyncio
import logging
import signal
import json
from typing import Any, List, Optional
from pydantic import Field
import mcp.types as types
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts.base import Message, UserMessage, TextContent
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

def execute_db_tool(conn, tool, *args, **kwargs):
    """Execute a database tool with the given connection and arguments."""
    try:
        return format_text_response(tool(conn, *args, **kwargs))
    except Exception as e:
        logger.error(f"Error sampling object: {e}")
        return format_error_response(str(e))
    
#------------------ Base Tools  ------------------#

@mcp.tool(description="Executes a SQL query to read from the database.")
async def get_td_base_readQuery(
    sql: str = Field(description="SQL that reads from the database to run", default=""),
    ) -> ResponseType:
    """Executes a SQL query to read from the database."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_base_readQuery, sql=sql) 


@mcp.tool(description="Executes a SQL query to write to the database.")
async def write_td_base_writeQuery(
    sql: str = Field(description="SQL that writes to the database to run", default=""),
    ) -> ResponseType:
    """Executes a SQL query to write to the database."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_write_td_base_writeQuery, sql=sql) 


@mcp.tool(description="Display table DDL definition.")
async def get_td_base_tableDDL(
    db_name: str = Field(description="Database name", default=""),
    table_name: str = Field(description="table name", default=""),
    ) -> ResponseType:
    """Display table DDL definition."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_base_tableDDL, db_name=db_name, table_name=table_name)    

@mcp.tool(description="List all databases in the Teradata System.")
async def get_td_base_databaseList() -> ResponseType:
    """List all databases in the Teradata System."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_base_databaseList)


@mcp.tool(description="List objects in a database.")
async def get_td_base_tableList(
    db_name: str = Field(description="database name", default=""),
    ) -> ResponseType:
    """List objects in a database."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_base_tableList, db_name=db_name)


@mcp.tool(description="Show detailed column information about a database table.")
async def get_td_base_columnDescription(
    db_name: str = Field(description="Database name", default=""),
    obj_name: str = Field(description="table name", default=""),
    ) -> ResponseType:
    """Show detailed column information about a database table."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_base_columnDescription, db_name=db_name, obj_name=obj_name)


@mcp.tool(description="Get data samples and structure overview from a database table.")
async def get_td_base_tablePreview(
    db_name: str = Field(description="Database name", default=""),
    table_name: str = Field(description="table name", default=""),
    ) -> ResponseType:
    """Get data samples and structure overview from a database table."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_base_tablePreview, table_name=table_name, db_name=db_name)

@mcp.tool(description="Get tables commonly used together by database users, this is helpful to infer relationships between tables.")
async def get_td_base_tableAffinity(
    db_name: str = Field(description="Database name", default=""),
    obj_name: str = Field(description="Table or view name", default=""),
    ) -> ResponseType:
    """Get tables commonly used together by database users, this is helpful to infer relationships between tables."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_base_tableAffinity, obj_name=obj_name, db_name=db_name)


@mcp.tool(description="Measure the usage of a table and views by users in a given schema, this is helpful to infer what database objects are most actively used or drive most value.")
async def get_td_base_tableUsage(
    db_name: str = Field(description="Database name", default=""),
    ) -> ResponseType:
    """Measure the usage of a table and views by users in a given schema, this is helpful to infer what database objects are most actively used or drive most value."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_base_tableUsage, db_name=db_name)

@mcp.prompt()
async def sql_prompt(qry: str) -> UserMessage:
    """Create a SQL query against the database"""
    return UserMessage(role="user", content=TextContent(type="text", text=td.prompt_general.format(qry=qry)))

@mcp.prompt()
async def table_business_description(database_name: str, table_name: str) -> UserMessage:
    """Create a business description of the table and columns."""
    return UserMessage(role="user", content=TextContent(type="text", text=td.prompt_table_business_description.format(database_name=database_name, table_name=table_name)))

@mcp.prompt()
async def database_business_description(database_name: str) -> UserMessage:
    """Create a business description of the database."""
    return UserMessage(role="user", content=TextContent(type="text", text=td.prompt_database_business_description.format(database_name=database_name)))

#------------------ DBA Tools  ------------------#

@mcp.tool(description="Get a list of SQL run by a user in the last number of days if a user name is provided, otherwise get list of all SQL in the last number of days.")
async def get_td_dba_userSqlList(
    user_name: str = Field(description="user name", default=""),
    no_days: int = Field(description="number of days to look back", default=7),
    ) -> ResponseType:
    """Get a list of SQL run by a user."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_dba_userSqlList, user_name=user_name, no_days=no_days)

@mcp.tool(description="Get a list of SQL run against a table in the last number of days ")
async def get_td_dba_tableSqlList(
    table_name: str = Field(description="table name", default=""),
    no_days: int = Field(description="number of days to look back", default=7),
    ) -> ResponseType:
    """Get a list of SQL run by a user."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_dba_tableSqlList, table_name=table_name, no_days=no_days)

@mcp.tool(description="Get table space used for a table if table name is provided or get table space for all tables in a database if a database name is provided.")
async def get_td_dba_tableSpace(
    db_name: str = Field(description="Database name", default=""),
    table_name: str = Field(description="table name", default=""),
    ) -> ResponseType:
    """Get table space used for a table if table name is provided or get table space for all tables in a database if a database name is provided."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_dba_tableSpace, db_name=db_name, table_name=table_name)

@mcp.tool(description="Get database space if database name is provided, otherwise get all databases space allocations.")
async def get_td_dba_databaseSpace(
    db_name: str = Field(description="Database name", default=""),
    ) -> ResponseType:
    """Get database space if database name is provided, otherwise get all databases space allocations."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_dba_databaseSpace, db_name=db_name)

@mcp.tool(description="Get Teradata database version information.")
async def get_td_dba_databaseVersion() -> ResponseType:
    """Get Teradata database version information."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_dba_databaseVersion)

@mcp.tool(description="Get the Teradata system usage summary metrics by weekday and hour for each workload type and query complexity bucket.")
async def get_td_dba_resusageSummary() -> ResponseType:
    """Get the Teradata system usage summary metrics by weekday and hour."""
    global _tdconn

    return execute_db_tool(_tdconn, td.handle_get_td_dba_resusageSummary, dimensions=["hourOfDay", "dayOfWeek"])

@mcp.tool(description="Get the Teradata system usage summary metrics by user on a specified date, or day of week and hour of day.")
async def get_td_dba_resusageUserSummary(
    user_name: str = Field(description="Database user name", default=""),
    date: str = Field(description="Date to analyze, formatted as `YYYY-MM-DD`", default=""),
    dayOfWeek: str = Field(description="Day of week to analyze", default=""),
    hourOfDay: str = Field(description="Hour of day to analyze", default=""),
    ) -> ResponseType:
    """Get the Teradata system usage summary metrics by user on a specified date, or day of week and hour of day."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_dba_resusageSummary, dimensions=["UserName", "hourOfDay", "dayOfWeek"], user_name=user_name, date=date, dayOfWeek=dayOfWeek, hourOfDay=hourOfDay)

@mcp.tool(description="Get the Teradata flow control metrics.")
async def get_td_dba_flowControl() -> ResponseType:
    """Get the Teradata flow control metrics."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_dba_flowControl)

@mcp.tool(description="Get the user feature usage metrics.")
async def get_td_dba_featureUsage() -> ResponseType:
    """Get the user feature usage metrics.""" 
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_dba_featureUsage)

@mcp.tool(description="Get the Teradata user delay metrics.")
async def get_td_dba_userDelay() -> ResponseType:
    """Get the Teradata user delay metrics."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_dba_userDelay)

@mcp.tool(description="Measure the usage of a table and views by users, this is helpful to understand what user and tables are driving most resource usage at any point in time.")
async def get_td_dba_tableUsageImpact(
    db_name: str = Field(description="Database name", default=""),
    user_name: str = Field(description="User name", default=""),    
    ) -> ResponseType:
    """Measure the usage of a table and views by users, this is helpful to understand what user and tables are driving most resource usage at any point in time."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_dba_tableUsageImpact, db_name=db_name,  user_name=user_name)

@mcp.prompt()
async def table_archive() -> UserMessage:
    """Create a table archive strategy for database tables."""
    return UserMessage(role="user", content=TextContent(type="text", text=td.prompt_table_archive))

@mcp.prompt()
async def database_lineage(database_name: str) -> UserMessage:
    """Create a database lineage map for tables in a database."""
    return UserMessage(role="user", content=TextContent(type="text", text=td.prompt_database_lineage.format(database_name=database_name)))

@mcp.prompt()
async def table_drop_impact(database_name: str, table_name: str) -> UserMessage:
    """Assess the impact of dropping a table."""
    return UserMessage(role="user", content=TextContent(type="text", text=td.prompt_table_drop_impact.format(database_name=database_name, table_name=table_name)))

#------------------ Data Quality Tools  ------------------#

@mcp.tool(description="Get the column names that having missing values in a table.")
async def get_td_qlty_missingValues(
    table_name: str = Field(description="table name", default=""),
    ) -> ResponseType:
    """Get the column names that having missing values in a table."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_qlty_missingValues, table_name=table_name)


@mcp.tool(description="Get the column names that having negative values in a table.")
async def get_td_qlty_negativeValues(
    table_name: str = Field(description="table name", default=""),
    ) -> ResponseType:
    """Get the column names that having negative values in a table."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_qlty_negativeValues, table_name=table_name)

@mcp.tool(description="Get the destinct categories from column in a table.")
async def get_td_qlty_distinctCategories(
    table_name: str = Field(description="table name", default=""),
    col_name: str = Field(description="column name", default=""),
    ) -> ResponseType:
    """Get the destinct categories from column in a table."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_qlty_distinctCategories, table_name=table_name, col_name=col_name)

@mcp.tool(description="Get the standard deviation from column in a table.")
async def get_td_qlty_standardDeviation(
    table_name: str = Field(description="table name", default=""),
    col_name: str = Field(description="column name", default=""),
    ) -> ResponseType:
    """Get the standard deviation from column in a table."""
    global _tdconn
    return execute_db_tool(_tdconn, td.handle_get_td_qlty_standardDeviation, table_name=table_name, col_name=col_name)



#------------------ Custom Tools  ------------------#
# Custom tools are defined as SQL queries in a YAML file and loaded at startup.
import yaml
import glob
import os

query_defs = []
custom_tool_files = [file for file in os.listdir() if file.endswith("_tools.yaml")]

for file in custom_tool_files:
    with open(file) as f:
        query_defs.extend(yaml.safe_load(f))  # Concatenate all query definitions


def make_custom_query_tool(sql_text: str, tool_name: str, desc: str):
    async def _dynamic_tool():
        # SQL is closed over without parameters
        return execute_db_tool(_tdconn, td.handle_execute_read_query, sql=sql_text)
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
    global _tdconn, _tdbasetools
    
    sse = os.getenv("SSE", "false").lower()
    logger.info(f"SSE: {sse}")

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
    # await mcp.run_stdio_async()
    if sse == "true":
        mcp.settings.host = os.getenv("SSE_HOST")
        mcp.settings.port = int(os.getenv("SSE_PORT"))
        logger.info(f"Starting MCP server on {mcp.settings.host}:{mcp.settings.port}")
        await mcp.run_sse_async()
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