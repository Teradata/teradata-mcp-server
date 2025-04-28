import os
import asyncio
import argparse
import logging
import signal
from typing import Any
from typing import List
from pydantic import Field
import mcp.types as types
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from td_connect import TDConn
from prompt import PROMPT_TEMPL

load_dotenv()

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(),
              logging.FileHandler(os.path.join("logs", "teradata_mcp_server.log"))],
)
logger = logging.getLogger("teradata_mcp_server")    
logger.info("Starting Teradata MCP server")

# Connect to MCP server
mcp = FastMCP("teradata-mcp")
ResponseType = List[types.TextContent | types.ImageContent | types.EmbeddedResource]

#global shutdown flag
shutdown_in_progress = False

# Initiate connection to Teradata
_tdconn = TDConn()

# Formats text responses
def format_text_response(text: Any) -> ResponseType:
    """Format a text response."""
    return [types.TextContent(type="text", text=str(text))]

# Formats error responses
def format_error_response(error: str) -> ResponseType:
    """Format an error response."""
    return format_text_response(f"Error: {error}")


#------------------ Tool  ------------------#
# SQL execution tool
#     Arguments: sql (str) - SQL query to execute
#     Returns: ResponseType - formatted response with query results or error message
#     Description: Executes a SQL query against the Teradata database and returns the results.
#         If the query is successful, it returns the results as a list of text content.
#         If an error occurs, it logs the error and returns an error message.
#         The function uses a global connection object (_tdconn) to interact with the database.
#         The SQL query can be any valid SQL statement supported by Teradata.
@mcp.tool(description=f"Execute any SQL query")
async def execute_sql(
    sql: str = Field(description="SQL to run", default="all"),
    ) -> ResponseType:
    """Executes a SQL query against the database."""
    global _tdconn
    try:
        cur = _tdconn.cursor()
        rows = cur.execute(sql)  # type: ignore
        if rows is None:
            return format_text_response("No results")
        return format_text_response(list([row for row in rows.fetchall()]))
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return format_error_response(str(e))

#------------------ Tool  ------------------#
# Returns the show table definition for a given table
#   Arguments: db_name (str) - name of the database
#   table_name (str) - name of the table to get the definition for
#   Returns: ResponseType - formatted response with table definition or error message
#   Description: Retrieves the show table definition for a specified table in a database.
@mcp.tool(description="What is the show table definition?")
async def show_table_definition(
    db_name: str = Field(description="Database name"),
    table_name: str = Field(description="table name"),
) -> ResponseType:
    """Display table definition."""
    try:
        global _tdconn
        cur = _tdconn.cursor()
        rows = cur.execute(f"show table {db_name}.{table_name}")
        return format_text_response(list([row for row in rows.fetchall()]))
    except Exception as e:
        logger.error(f"Error evaluating features: {e}")
        return format_error_response(str(e))
    
#------------------ Tool  ------------------#
# finds the top features with missing values in a table
#     Arguments: table_name (str) - name of the table to analyze
#     Returns: ResponseType - formatted response with missing value counts or error message
#     Description: Lists the top features (columns) with missing values in a specified table.
@mcp.tool(description="What are the top features with missing values in a table")
async def list_missing_val(
    table_name: str = Field(description="table name"),
) -> ResponseType:
    """List of columns with count of null values."""
    try:
        global _tdconn
        cur = _tdconn.cursor()
        rows = cur.execute(f"select ColumnName, NullCount, NullPercentage from TD_ColumnSummary ( on {table_name} as InputTable using TargetColumns ('[:]')) as dt ORDER BY NullCount desc")
        return format_text_response(list([row for row in rows.fetchall()]))
    except Exception as e:
        logger.error(f"Error evaluating features: {e}")
        return format_error_response(str(e))

#------------------ Tool  ------------------#
# finds the top features with negative values in a table
#   Arguments: table_name (str) - name of the table to analyze
#   Returns: ResponseType - formatted response with negative value counts or error message
#   Description: Lists the top features (columns) with negative values in a specified table.    
@mcp.tool(description="How many features have negative values in a table")
async def list_negative_val(
    table_name: str = Field(description="table name"),
) -> ResponseType:
    """List of columns with count of negative values."""
    try:
        global _tdconn
        cur = _tdconn.cursor()
        rows = cur.execute(f"select ColumnName, NegativeCount from TD_ColumnSummary ( on {table_name} as InputTable using TargetColumns ('[:]')) as dt ORDER BY NegativeCount desc")
        return format_text_response(list([row for row in rows.fetchall()]))
    except Exception as e:
        logger.error(f"Error evaluating features: {e}")
        return format_error_response(str(e))

#------------------ Tool  ------------------#
# finds the top features with distinct categories in a table
#   Arguments: table_name (str) - name of the table to analyze
#   col_name (str) - name of the column to analyze
#   Returns: ResponseType - formatted response with distinct category counts or error message
#   Description: Lists the top features (columns) with distinct categories in a specified table.
#     It uses the TD_CategoricalSummary function to analyze the specified column and returns the results.
@mcp.tool(description="How many distinct categories are there for column in the table")
async def list_dist_cat(
    table_name: str = Field(description="table name"),
    col_name: str = Field(description="column name"),
) -> ResponseType:
    """List distinct categories in the column."""
    try:
        global _tdconn
        cur = _tdconn.cursor()
        rows = cur.execute(f"select * from TD_CategoricalSummary ( on {table_name} as InputTable using TargetColumns ('{col_name}')) as dt")
        return format_text_response(list([row for row in rows.fetchall()]))
    except Exception as e:
        logger.error(f"Error evaluating features: {e}")
        return format_error_response(str(e))

#------------------ Tool  ------------------#
# finds the mean and standard deviation for a column in a table
#   Arguments: table_name (str) - name of the table to analyze
#   col_name (str) - name of the column to analyze
#   Returns: ResponseType - formatted response with mean and standard deviation or error message
#   Description: Calculates the mean and standard deviation for a specified column in a table.
#     It uses the TD_UnivariateStatistics function to perform the analysis and returns the results.
@mcp.tool(description="What is the mean and standard deviation for column in table? Does it follow normal distribution?")
async def stnd_dev(
    table_name: str = Field(description="table name"),
    col_name: str = Field(description="column name"),
) -> ResponseType:
    """Display standard deviation for column."""
    try:
        global _tdconn
        cur = _tdconn.cursor()
        rows = cur.execute(f"select * from TD_UnivariateStatistics ( on {table_name} as InputTable using TargetColumns ('{col_name}') Stats('MEAN','STD')) as dt ORDER BY 1,2")
        return format_text_response(list([row for row in rows.fetchall()]))
    except Exception as e:
        logger.error(f"Error evaluating features: {e}")
        return format_error_response(str(e))

#------------------ Tool  ------------------#
# List all databases in the Teradata system tool
#     Arguments: None
#     Returns: ResponseType - formatted response with database names and types or error message
#     Description: Lists all databases in the Teradata system, excluding certain administrative databases.
#         The function uses a global connection object (_tdconn) to interact with the database.
#         It executes a SQL query to retrieve the database names and types, and formats the results for display.
#         If an error occurs, it logs the error and returns an error message.
@mcp.tool(description="List all databases in the Teradata system")
async def list_db() -> ResponseType:
    """List all databases in the Teradata."""
    try:
        global _tdconn
        cur = _tdconn.cursor()
        rows = cur.execute("select DataBaseName, DECODE(DBKind, 'U', 'User', 'D','DataBase') as DBType , CommentString from dbc.DatabasesV dv where OwnerName <> 'PDCRADM'")
        return format_text_response(list([row for row in rows.fetchall()]))
    except Exception as e:
        logger.error(f"Error listing schemas: {e}")
        return format_error_response(str(e))

#------------------ Tool  ------------------#
# List all objects in a database tool
#     Arguments: db_name (str) - name of the database to list objects from
#     Returns: ResponseType - formatted response with object names and types or error message
#     Description: Lists all objects (tables and views) in a specified database.
#         The function uses a global connection object (_tdconn) to interact with the database.
#         It executes a SQL query to retrieve the object names and types, and formats the results for display.
#         If an error occurs, it logs the error and returns an error message.
@mcp.tool(description="List objects in a database")
async def list_objects(
    db_name: str = Field(description="database name"),
    ) -> ResponseType:
    """List objects of in a database of the given name."""
    try:
        global _tdconn
        cur = _tdconn.cursor()
        rows = cur.execute("select TableName from dbc.TablesV tv where UPPER(tv.DatabaseName) = UPPER(?) and tv.TableKind in ('T','V', 'O', 'Q');", [db_name])
        return format_text_response(list([row for row in rows.fetchall()]))
    except Exception as e:
        logger.error(f"Error listing schemas: {e}")
        return format_error_response(str(e))

#------------------ Tool  ------------------#
# Get detailed information about a database table tool
#     Arguments: db_name (str) - name of the database
#                obj_name (str) - name of the table to get details for
#     Returns: ResponseType - formatted response with table details or error message
#     Description: Retrieves detailed information about a specific table in a database.
#         The function uses a global connection object (_tdconn) to interact with the database.
#         It executes a SQL query to retrieve the table details, including column names and types,
#         and formats the results for display.
#         If an error occurs, it logs the error and returns an error message.
#         The function allows for wildcard matching of database and table names.
@mcp.tool(description="Show detailed information about a database tables")
async def get_object_details(
    db_name: str = Field(description="Database name"),
    obj_name: str = Field(description="table name"),
    ) -> ResponseType:
    """Get detailed information about a database tables."""
    if len(db_name) == 0:
        db_name = "%"
    if len(obj_name) == 0:
        obj_name = "%"
    try:
        global _tdconn
        cur = _tdconn.cursor()
        rows = cur.execute(
            """
            sel TableName, ColumnName, CASE ColumnType
          WHEN '++' THEN 'TD_ANYTYPE'
          WHEN 'A1' THEN 'UDT'
          WHEN 'AT' THEN 'TIME'
          WHEN 'BF' THEN 'BYTE'
          WHEN 'BO' THEN 'BLOB'
          WHEN 'BV' THEN 'VARBYTE'
          WHEN 'CF' THEN 'CHAR'
          WHEN 'CO' THEN 'CLOB'
          WHEN 'CV' THEN 'VARCHAR'
          WHEN 'D' THEN  'DECIMAL'
          WHEN 'DA' THEN 'DATE'
          WHEN 'DH' THEN 'INTERVAL DAY TO HOUR'
          WHEN 'DM' THEN 'INTERVAL DAY TO MINUTE'
          WHEN 'DS' THEN 'INTERVAL DAY TO SECOND'
          WHEN 'DY' THEN 'INTERVAL DAY'
          WHEN 'F' THEN  'FLOAT'
          WHEN 'HM' THEN 'INTERVAL HOUR TO MINUTE'
          WHEN 'HR' THEN 'INTERVAL HOUR'
          WHEN 'HS' THEN 'INTERVAL HOUR TO SECOND'
          WHEN 'I1' THEN 'BYTEINT'
          WHEN 'I2' THEN 'SMALLINT'
          WHEN 'I8' THEN 'BIGINT'
          WHEN 'I' THEN  'INTEGER'
          WHEN 'MI' THEN 'INTERVAL MINUTE'
          WHEN 'MO' THEN 'INTERVAL MONTH'
          WHEN 'MS' THEN 'INTERVAL MINUTE TO SECOND'
          WHEN 'N' THEN 'NUMBER'
          WHEN 'PD' THEN 'PERIOD(DATE)'
          WHEN 'PM' THEN 'PERIOD(TIMESTAMP WITH TIME ZONE)'
          WHEN 'PS' THEN 'PERIOD(TIMESTAMP)'
          WHEN 'PT' THEN 'PERIOD(TIME)'
          WHEN 'PZ' THEN 'PERIOD(TIME WITH TIME ZONE)'
          WHEN 'SC' THEN 'INTERVAL SECOND'
          WHEN 'SZ' THEN 'TIMESTAMP WITH TIME ZONE'
          WHEN 'TS' THEN 'TIMESTAMP'
          WHEN 'TZ' THEN 'TIME WITH TIME ZONE'
          WHEN 'UT' THEN 'UDT'
          WHEN 'YM' THEN 'INTERVAL YEAR TO MONTH'
          WHEN 'YR' THEN 'INTERVAL YEAR'
          WHEN 'AN' THEN 'UDT'
          WHEN 'XM' THEN 'XML'
          WHEN 'JN' THEN 'JSON'
          WHEN 'DT' THEN 'DATASET'
          WHEN '??' THEN 'STGEOMETRY''ANY_TYPE'
          END as CType
      from DBC.ColumnsVX where upper(tableName) like upper(?) and upper(DatabaseName) like upper(?)
            """
                           , [obj_name,db_name])
        return format_text_response(list([row for row in rows.fetchall()]))
    except Exception as e:
        logger.error(f"Error listing schemas: {e}")
        return format_error_response(str(e))

#------------------ Tool  ------------------#
@mcp.tool(description="Get data samples and structure overview from a database table.")
async def get_object_samples(
    db_name: str = Field(description="Database name"),
    obj_name: str = Field(description="table name"),
    ) -> ResponseType:
    """Get data samples and structure overview from a database table."""
    try:
        return format_text_response(_tdconn.peek_table(obj_name, db_name))
    except Exception as e:
        logger.error(f"Error sampling object: {e}")
        return format_error_response(str(e))


#------------------ Prompt Definitions  ------------------#
@mcp.prompt()
def sql_prompt() -> str:
    """Create a SQL query against the database"""
    return PROMPT_TEMPL


#------------------ Main ------------------#
# Main function to start the MCP server
#     Description: Initializes the MCP server and sets up signal handling for graceful shutdown.
#         It creates a connection to the Teradata database and starts the server to listen for incoming requests.
#         The function uses asyncio to manage asynchronous operations and handle signals for shutdown.
#         If an error occurs during initialization, it logs a warning message.
async def main():
    global _tdconn
    
    # Load environment variables
    parser = argparse.ArgumentParser(description="Teradata MCP Server")
    parser.add_argument("database_url", help="Database connection URL", nargs="?")
    args = parser.parse_args()
    connection_url = os.getenv("DATABASE_URI", args.database_url)

    # Initialize database connection pool
    try:
        _tdconn = TDConn(connection_url)
        logger.info("Successfully connected to database and initialized connection")
    except Exception as e:
        logger.warning(
            "The MCP server will start but database operations will fail until a valid connection is established.",
        )

    # Set up proper shutdown handling
    try:
        loop = asyncio.get_running_loop()
        signals = (signal.SIGTERM, signal.SIGINT)
        for s in signals:
            loop.add_signal_handler(s, lambda s=s: asyncio.create_task(shutdown(s)))
    except NotImplementedError:
        # Windows doesn't support signals properly
        logger.warning("Signal handling not supported on Windows")
        pass
    
    # Start the MCP server
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
    global shutdown_in_progress

    if shutdown_in_progress:
        logger.warning("Forcing immediate exit")
        os._exit(1)  # Use immediate process termination instead of sys.exit
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
