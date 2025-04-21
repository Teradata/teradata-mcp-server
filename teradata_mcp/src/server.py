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



#------------------ Prompt Definitions (this will change) ------------------#
################### Prompt ##########################
@mcp.prompt()
def sql_query() -> str:
    """Create a SQL query against the database"""
    return "Please help me write a Teradata SQL query for the following question:\n\n"


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
    logger.handlers.append(logging.FileHandler(os.path.join("logs", "teradata_mcp.log")))
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
