"""
This file contains the Python implementation of tools for the Teradata MCP server.
If the tool is a simple (parameterized) query or cube, it should it should be defined in the *_objects.yml file in this directory.
"""

import logging
from teradatasql import TeradataConnection 
from typing import Optional, Any, Dict, List
import json
from datetime import date, datetime
from decimal import Decimal

logger = logging.getLogger("teradata_mcp_server")
from teradata_mcp_server.tools.utils import serialize_teradata_types, rows_to_json, create_response

#------------------ Do not make changes above  ------------------#


#------------------ Tool  ------------------#
# <Name of Tool> tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       <arguments> - <description of arguments>
#     Returns: <what it does> or error message    
def handle_tmpl_nameOfTool(conn: TeradataConnection, argument: Optional[str], *args, **kwargs):
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