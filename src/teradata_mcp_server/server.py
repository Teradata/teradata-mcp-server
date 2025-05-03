import os
import asyncio
import logging
import signal
from typing import Any
from typing import List
from pydantic import Field
import mcp.types as types
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

from td_connect import TDConn
from td_base_tools import (
    handle_execute_read_query,
    handle_execute_write_query,
    handle_read_table_ddl,
    handle_read_database_list,
    handle_read_table_preview, 
    handle_read_column_description, 
    handle_read_table_list)
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

#global shutdown flag
shutdown_in_progress = False

# Initiate connection to Teradata
_tdconn = TDConn()

#------------------ Tool utilies  ------------------#
ResponseType = List[types.TextContent | types.ImageContent | types.EmbeddedResource]

def format_text_response(text: Any) -> ResponseType:
    """Format a text response."""
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
    
#------------------ Tools  ------------------#

@mcp.tool(description="Executes a SQL query to read from the database.")
async def execute_read_query(
    sql: str = Field(description="SQL that reads from the database to run", default="all"),
    ) -> ResponseType:
    """Executes a SQL query to read from the database."""
    global _tdconn
    return execute_db_tool(_tdconn, handle_execute_read_query, sql) 


@mcp.tool(description="Executes a SQL query to write to the database.")
async def execute_write_query(
    sql: str = Field(description="SQL that writes to the database to run", default="all"),
    ) -> ResponseType:
    """Executes a SQL query to write to the database."""
    global _tdconn
    return execute_db_tool(_tdconn, handle_execute_write_query, sql) 


@mcp.tool(description="Display table DDL definition.")
async def read_table_ddl(
    db_name: str = Field(description="Database name"),
    table_name: str = Field(description="table name"),
    ) -> ResponseType:
    """Display table DDL definition."""
    global _tdconn
    return execute_db_tool(_tdconn, handle_read_table_ddl, db_name, table_name)    
 
    
@mcp.tool(description="List all databases in the Teradata System.")
async def read_database_list() -> ResponseType:
    """List all databases in the Teradata System."""
    global _tdconn
    return execute_db_tool(_tdconn, handle_read_database_list)


@mcp.tool(description="List objects in a database.")
async def read_table_list(
    db_name: str = Field(description="database name"),
    ) -> ResponseType:
    """List objects in a database."""
    global _tdconn
    return execute_db_tool(_tdconn, handle_read_table_list, db_name)


@mcp.tool(description="Show detailed column information about a database table.")
async def read_column_description(
    db_name: str = Field(description="Database name"),
    obj_name: str = Field(description="table name"),
    ) -> ResponseType:
    """Show detailed column information about a database table."""
    global _tdconn
    return execute_db_tool(_tdconn, handle_read_column_description, db_name, obj_name)


@mcp.tool(description="Get data samples and structure overview from a database table.")
async def read_table_preview(
    db_name: str = Field(description="Database name"),
    obj_name: str = Field(description="table name"),
    ) -> ResponseType:
    """Get data samples and structure overview from a database table."""
    global _tdconn
    return execute_db_tool(_tdconn, handle_read_table_preview, obj_name, db_name)



#------------------ Prompt Definitions  ------------------#
@mcp.prompt()
async def sql_prompt() -> str:
    """Create a SQL query against the database"""
    return PROMPT_TEMPL


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
