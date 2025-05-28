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

#------------------ Tool  ------------------#
# Missing Values tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       table_name (str) - name of the table 
#     Returns: formatted response with list of column names and stats on missing values or error message    
def handle_get_td_qlty_missingValues(conn: TeradataConnection, table_name: str, *args, **kwargs):
    logger.debug(f"Tool: handle_get_td_qlty_missingValues: Args: table_name: {table_name}")

    with conn.cursor() as cur:
        rows = cur.execute(f"select ColumnName, NullCount, NullPercentage from TD_ColumnSummary ( on {table_name} as InputTable using TargetColumns ('[:]')) as dt ORDER BY NullCount desc")
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "get_td_qlty_missingValues",
            "table_name": table_name,
        }
        return create_response(data, metadata)

#------------------ Tool  ------------------#
# negative values tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries  
#       table_name (str) - name of the table 
#     Returns: formatted response with list of column names and stats on negative values or error message    
def handle_get_td_qlty_negativeValues(conn: TeradataConnection, table_name: str, *args, **kwargs):
    logger.debug(f"Tool: handle_get_td_qlty_negativeValues: Args: table_name: {table_name}")

    with conn.cursor() as cur:
        rows = cur.execute(f"select ColumnName, NegativeCount from TD_ColumnSummary ( on {table_name} as InputTable using TargetColumns ('[:]')) as dt ORDER BY NegativeCount desc")
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "get_td_qlty_negativeValues",
            "table_name": table_name,
        }
        return create_response(data, metadata)

#------------------ Tool  ------------------#
# distinct categories tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries  
#       table_name (str) - name of the table 
#       col_name (str) - name of the column
#     Returns: formatted response with list of column names and stats on categorial values or error message    
def handle_get_td_qlty_distinctCategories(conn: TeradataConnection, table_name: str, col_name: str, *args, **kwargs):
    logger.debug(f"Tool: handle_get_td_qlty_distinctCategories: Args: table_name: {table_name}, col_name: {col_name}")

    with conn.cursor() as cur: 
        rows = cur.execute(f"select * from TD_CategoricalSummary ( on {table_name} as InputTable using TargetColumns ('{col_name}')) as dt")
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "get_td_qlty_distinctCategories",
            "table_name": table_name,
            "col_name": col_name,
            "distinct_categories": len(data)
        }
        return create_response(data, metadata)

#------------------ Tool  ------------------#
# stadard deviation tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries 
#       table_name (str) - name of the table 
#       col_name (str) - name of the column
#     Returns: formatted response with list of column names and standard deviation information or error message    
def handle_get_td_qlty_standardDeviation(conn: TeradataConnection, table_name: str, col_name: str, *args, **kwargs):
    logger.debug(f"Tool: handle_get_td_qlty_standardDeviation: Args: table_name: {table_name}, col_name: {col_name}")

    with conn.cursor() as cur:
        rows = cur.execute(f"select * from TD_UnivariateStatistics ( on {table_name} as InputTable using TargetColumns ('{col_name}') Stats('MEAN','STD')) as dt ORDER BY 1,2")
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "get_td_qlty_standardDeviation",
            "table_name": table_name,
            "col_name": col_name,
            "stats_calculated": ["MEAN", "STD"]
        }
        return create_response(data, metadata)

