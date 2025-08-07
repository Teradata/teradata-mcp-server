"""
This file contains the Python implementation of tools for the Teradata MCP server.
If the tool is a simple (parameterized) query or cube, it should it should be defined in the *_objects.yml file in this directory.
"""

import logging

from teradatasql import TeradataConnection

from teradata_mcp_server.tools.utils import create_response, rows_to_json

logger = logging.getLogger("teradata_mcp_server")


#------------------ Do not make changes above  ------------------#


#------------------ Tool  ------------------#
# <Name of Tool> tool
def handle_tmpl_nameOfTool(conn: TeradataConnection, argument: str | None, *args, **kwargs):
    """
    <description of what the tool is for>

    Arguments:
      arguments - arguments to analyze

    Returns:
      ResponseType: formatted response with query results + metadata
    """
    logger.debug(f"Tool: handle_tmpl_nameOfTool: Args: argument: {argument}")

    with conn.cursor() as cur:
        if argument == "":
            logger.debug("No argument provided")
            rows = cur.execute("Teradata query goes here;")
        else:
            logger.debug(f"Argument provided: {argument}")
            rows = cur.execute(f"Teradata query goes here with argument {argument};")
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "tmpl_nameOfTool",
            "argument": argument,
        }
        return create_response(data, metadata)
