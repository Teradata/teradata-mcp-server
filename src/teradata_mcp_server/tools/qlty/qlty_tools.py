import logging
from teradatasql import TeradataConnection 
from typing import Optional, Any, Dict, List
import json
from datetime import date, datetime
from decimal import Decimal

logger = logging.getLogger("teradata_mcp_server")
from teradata_mcp_server.tools.utils import serialize_teradata_types, rows_to_json, create_response

#------------------ Tool  ------------------#
# Missing Values tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       table_name (str) - name of the table 
#     Returns: formatted response with list of column names and stats on missing values or error message    
def handle_qlty_missingValues(conn: TeradataConnection, table_name: str, *args, **kwargs):
    """
    Get the column names that having missing values in a table.

    Arguments:
      table_name - table name to analyze

    Returns:
      ResponseType: formatted response with query results + metadata
    """   
    logger.debug(f"Tool: handle_qlty_missingValues: Args: table_name: {table_name}")

    with conn.cursor() as cur:
        rows = cur.execute(f"select ColumnName, NullCount, NullPercentage from TD_ColumnSummary ( on {table_name} as InputTable using TargetColumns ('[:]')) as dt ORDER BY NullCount desc")
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "qlty_missingValues",
            "table_name": table_name,
        }
        return create_response(data, metadata)

#------------------ Tool  ------------------#
# negative values tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries  
#       table_name (str) - name of the table 
#     Returns: formatted response with list of column names and stats on negative values or error message    
def handle_qlty_negativeValues(conn: TeradataConnection, table_name: str, *args, **kwargs):
    """
    Get the column names that having negative values in a table.

    Arguments:
      table_name - table name to analyze

    Returns:
      ResponseType: formatted response with query results + metadata
    """   
    logger.debug(f"Tool: handle_qlty_negativeValues: Args: table_name: {table_name}")

    with conn.cursor() as cur:
        rows = cur.execute(f"select ColumnName, NegativeCount from TD_ColumnSummary ( on {table_name} as InputTable using TargetColumns ('[:]')) as dt ORDER BY NegativeCount desc")
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "qlty_negativeValues",
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
def handle_qlty_distinctCategories(conn: TeradataConnection, table_name: str, col_name: str, *args, **kwargs):
    """
    Get the destinct categories from column in a table.

    Arguments:
      table_name - table name to analyze
      col_name - column name to analyze

    Returns:
      ResponseType: formatted response with query results + metadata
    """   
    logger.debug(f"Tool: handle_qlty_distinctCategories: Args: table_name: {table_name}, col_name: {col_name}")

    with conn.cursor() as cur: 
        rows = cur.execute(f"select * from TD_CategoricalSummary ( on {table_name} as InputTable using TargetColumns ('{col_name}')) as dt")
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "qlty_distinctCategories",
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
def handle_qlty_standardDeviation(conn: TeradataConnection, table_name: str, col_name: str, *args, **kwargs):
    """
    Get the standard deviation from column in a table.

    Arguments:
      table_name - table name to analyze
      col_name - column name to analyze

    Returns:
      ResponseType: formatted response with query results + metadata
    """   
    logger.debug(f"Tool: handle_qlty_standardDeviation: Args: table_name: {table_name}, col_name: {col_name}")

    with conn.cursor() as cur:
        rows = cur.execute(f"select * from TD_UnivariateStatistics ( on {table_name} as InputTable using TargetColumns ('{col_name}') Stats('MEAN','STD')) as dt ORDER BY 1,2")
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "qlty_standardDeviation",
            "table_name": table_name,
            "col_name": col_name,
            "stats_calculated": ["MEAN", "STD"]
        }
        return create_response(data, metadata)


#------------------ Tool  ------------------#
# column summary tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       table_name (str) - name of the table 
#     Returns: formatted response with list of column names and stats or error message
def handle_qlty_columnSummary(conn: TeradataConnection, table_name: str, *args, **kwargs):
    """
    Get the column summary statistics for a table.

    Arguments:
      table_name - table name to analyze

    Returns:
      ResponseType: formatted response with query results + metadata
    """   
    logger.debug(f"Tool: handle_qlty_columnSummary: Args: table_name: {table_name}")

    with conn.cursor() as cur:
        rows = cur.execute(f"select * from TD_ColumnSummary ( on {table_name} as InputTable using TargetColumns ('[:]')) as dt")
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "qlty_columnSummary",
            "table_name": table_name,
        }
        return create_response(data, metadata)  
    

#------------------ Tool  ------------------#
# Univariate statistics tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       table_name (str) - name of the table 
#       col_name (str) - name of the column
#     Returns: formatted response with list of column names and stats or error message
def handle_qlty_univariateStatistics(conn: TeradataConnection, table_name: str, col_name: str, *args, **kwargs):
    """
    Get the univariate statistics for a table.

    Arguments:
      table_name - table name to analyze
      col_name - column name to analyze

    Returns:
      ResponseType: formatted response with query results + metadata
    """   
    logger.debug(f"Tool: handle_qlty_univariateStatistics: Args: table_name: {table_name}, col_name: {col_name}")

    with conn.cursor() as cur:
        rows = cur.execute(f"select * from TD_UnivariateStatistics ( on {table_name} as InputTable using TargetColumns ('{col_name}') Stats('ALL')) as dt ORDER BY 1,2")
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "qlty_univariateStatistics",
            "table_name": table_name,
            "col_name": col_name,
            "stats_calculated": ["ALL"]
        }
        return create_response(data, metadata)
    

#------------------ Tool  ------------------#
# Get Rows with Miissing Values tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       table_name (str) - name of the table 
#       col_name (str) - name of the column
#     Returns: formatted response with list of rows with missing values or error message
def handle_qlty_rowsWithMissingValues(conn: TeradataConnection, table_name: str, col_name: str, *args, **kwargs):
    """
    Get the rows with missing values in a table.

    Arguments:
      table_name - table name to analyze
      col_name - column name to analyze

    Returns:
      ResponseType: formatted response with query results + metadata
    """   
    logger.debug(f"Tool: handle_qlty_rowsWithMissingValues: Args: table_name: {table_name}, col_name: {col_name}")

    with conn.cursor() as cur:
        rows = cur.execute(f"select * from TD_getRowsWithMissingValues ( ON {table_name} AS InputTable USING TargetColumns ('[{col_name}]')) AS dt;")
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "qlty_rowsWithMissingValues",
            "table_name": table_name,
            "col_name": col_name,
            "rows_with_missing_values": len(data)
        }
        return create_response(data, metadata)