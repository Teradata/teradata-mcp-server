import asyncio
import argparse
import logging
import os
import signal
from typing import Any
from typing import List
from pydantic import Field
import mcp.types as types
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv


from tdsql.tdsql import TDConn



load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("teradata_mcp")

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

################### Tool ##########################
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

################### Tool ##########################
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

################### Tool ##########################
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

################### Tool ##########################
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



#------------------ Prompt Definitions (this will change) ------------------#

#------------------ Main ------------------#
################### Main ##########################
# Main function to start the MCP server
#     Description: Initializes the MCP server and sets up signal handling for graceful shutdown.
#         It creates a connection to the Teradata database and starts the server to listen for incoming requests.
#         The function uses asyncio to manage asynchronous operations and handle signals for shutdown.
#         If an error occurs during initialization, it logs a warning message.
async def main():
    global _tdconn

    # Setup logging
    os.makedirs("logs", exist_ok=True)
    logger.handlers.append(logging.FileHandler(os.path.join("logs", "teradata_dataquality_mcp.log")))
    logger.info("Starting Teradata MCP server")
    
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

################### Shutdown ##########################
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
