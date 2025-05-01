import logging
from typing import Any
from typing import List
from pydantic import Field
import mcp.types as types
from teradatasql import TeradataConnection 


logger = logging.getLogger("teradata_mcp_server")


#------------------ Tool  ------------------#
# Missing Values tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       table_name (str) - name of the table 
#     Returns: formatted response with list of column names and stats on missing values or error message    
def handle_missing_values(conn: TeradataConnection, table_name: str, *args, **kwargs):
    logger.debug(f"Tool: handle_missing_values: Args: table_name: {table_name}")
    
    with conn.cursor() as cur:   
        rows = cur.execute(f"select ColumnName, NullCount, NullPercentage from TD_ColumnSummary ( on {table_name} as InputTable using TargetColumns ('[:]')) as dt ORDER BY NullCount desc")
        return list([row for row in rows.fetchall()])

    
#------------------ Tool  ------------------#
# negative values tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries  
#       table_name (str) - name of the table 
#     Returns: formatted response with list of column names and stats on negative values or error message    
def handle_negative_values(conn: TeradataConnection, table_name: str, *args, **kwargs):
    logger.debug(f"Tool: handle_negative_values: Args: table_name: {table_name}")
    
    with conn.cursor() as cur:   
        rows = cur.execute(f"select ColumnName, NegativeCount from TD_ColumnSummary ( on {table_name} as InputTable using TargetColumns ('[:]')) as dt ORDER BY NegativeCount desc")
        return list([row for row in rows.fetchall()])

#------------------ Tool  ------------------#
# distinct categories tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries  
#       table_name (str) - name of the table 
#       col_name (str) - name of the column
#     Returns: formatted response with list of column names and stats on categorial values or error message    
def handle_destinct_categories(conn: TeradataConnection, table_name: str, col_name: str, *args, **kwargs):
    logger.debug(f"Tool: handle_distinct_categories: Args: table_name: {table_name}, col_name: {col_name}")

    with conn.cursor() as cur: 
        rows = cur.execute(f"select * from TD_CategoricalSummary ( on {table_name} as InputTable using TargetColumns ('{col_name}')) as dt")
        return list([row for row in rows.fetchall()])      

#------------------ Tool  ------------------#
# stadard deviation tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries 
#       table_name (str) - name of the table 
#       col_name (str) - name of the column
#     Returns: formatted response with list of column names and standard deviation information or error message    
def handle_standard_deviation(conn: TeradataConnection, table_name: str, col_name: str, *args, **kwargs):
    logger.debug(f"Tool: handle_standard_deviations: Args: table_name: {table_name}, col_name: {col_name}")
    
    with conn.cursor() as cur: 
        rows = cur.execute(f"select * from TD_UnivariateStatistics ( on {table_name} as InputTable using TargetColumns ('{col_name}') Stats('MEAN','STD')) as dt ORDER BY 1,2")
        return list([row for row in rows.fetchall()])

