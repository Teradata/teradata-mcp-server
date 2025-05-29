import logging
from teradatasql import TeradataConnection 
from typing import Optional, Any, Dict, List
import json
from datetime import date, datetime
from decimal import Decimal

logger = logging.getLogger("teradata_mcp_server")

def serialize_teradata_types(obj: Any) -> Any:
    """Convert Teradata-specific types to JSON serializable formats"""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)

def rows_to_json(cursor_description: Any, rows: List[Any]) -> List[Dict[str, Any]]:
    """Convert database rows to JSON objects using column names as keys"""
    if not cursor_description or not rows:
        return []
    
    columns = [col[0] for col in cursor_description]
    return [
        {
            col: serialize_teradata_types(value)
            for col, value in zip(columns, row)
        }
        for row in rows
    ]

def create_response(data: Any, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Create a standardized JSON response structure"""
    if metadata:
        response = {
            "status": "success",
            "metadata": metadata,
            "results": data
        }
    else:
        response = {
            "status": "success",
            "results": data
        }

    return json.dumps(response, default=serialize_teradata_types)

#------------------ Do not make changes above  ------------------#


#------------------ Tool  ------------------#
# <Name of Tool> tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       <arguments> - <description of arguments>
#     Returns: <what it does> or error message    
def handle_get_td_tmpl_nameOfTool(conn: TeradataConnection, argument: Optional[str], *args, **kwargs):
    logger.debug(f"Tool: handle_get_td_tmpl_nameOfTool: Args: argument: {argument}")

    with conn.cursor() as cur:
        if argument == "":
            logger.debug("No argument provided")
            rows = cur.execute("Teradata query goes here;")
        else:
            logger.debug(f"Argument provided: {argument}")
            rows = cur.execute(f"Teradata query goes here with argument {argument};")
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "get_td_tmpl_nameOfTool",
            "argument": argument,
        }
        return create_response(data, metadata)