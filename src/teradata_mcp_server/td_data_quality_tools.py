import logging
from typing import Any
from typing import List
from pydantic import Field
import mcp.types as types
from teradatasql import TeradataCursor


logger = logging.getLogger("teradata_mcp_server")

class TDDataQualityTools:

    ResponseType = List[types.TextContent | types.ImageContent | types.EmbeddedResource]

    def format_text_response(self, text: Any) -> ResponseType:
        """Format a text response."""
        return [types.TextContent(type="text", text=str(text))]

    def format_error_response(self, error: str) -> ResponseType:
        """Format an error response."""
        return self.format_text_response(f"Error: {error}")

    #------------------ Tool  ------------------#
    # Missing Values tool
    #     Arguments: 
    #       cur (TeradataCursor) - Teradata cursor object for executing SQL queries  
    #       table_name (str) - name of the table 
    #     Returns: ResponseType - formatted response with list of column names and stats on missing values or error message    
    def missing_values(self, cur: TeradataCursor ,table_name: str):
        try:    
            rows = cur.execute(f"select ColumnName, NullCount, NullPercentage from TD_ColumnSummary ( on {table_name} as InputTable using TargetColumns ('[:]')) as dt ORDER BY NullCount desc")
            return self.format_text_response(list([row for row in rows.fetchall()]))
        except Exception as e:
            logger.error(f"Error evaluating features: {e}")
            return self.format_error_response(str(e))
        
    #------------------ Tool  ------------------#
    # negative values tool
    #     Arguments: 
    #       cur (TeradataCursor) - Teradata cursor object for executing SQL queries  
    #       table_name (str) - name of the table 
    #     Returns: ResponseType - formatted response with list of column names and stats on negative values or error message    
    def negative_values(self, cur: TeradataCursor ,table_name: str):
        try:
            rows = cur.execute(f"select ColumnName, NegativeCount from TD_ColumnSummary ( on {table_name} as InputTable using TargetColumns ('[:]')) as dt ORDER BY NegativeCount desc")
            return self.format_text_response(list([row for row in rows.fetchall()]))
        except Exception as e:
            logger.error(f"Error evaluating features: {e}")
            return self.format_error_response(str(e))

    #------------------ Tool  ------------------#
    # distinct categories tool
    #     Arguments: 
    #       cur (TeradataCursor) - Teradata cursor object for executing SQL queries  
    #       table_name (str) - name of the table 
    #       col_name (str) - name of the column
    #     Returns: ResponseType - formatted response with list of column names and stats on categorial values or error message    
    def destinct_categories(self, cur: TeradataCursor ,table_name: str, col_name: str):
        try:
            rows = cur.execute(f"select * from TD_CategoricalSummary ( on {table_name} as InputTable using TargetColumns ('{col_name}')) as dt")
            return self.format_text_response(list([row for row in rows.fetchall()]))
        except Exception as e:
            logger.error(f"Error evaluating features: {e}")
            return self.format_error_response(str(e))           

    #------------------ Tool  ------------------#
    # stadard deviation tool
    #     Arguments: 
    #       cur (TeradataCursor) - Teradata cursor object for executing SQL queries  
    #       table_name (str) - name of the table 
    #       col_name (str) - name of the column
    #     Returns: ResponseType - formatted response with list of column names and standard deviation information or error message    
    def standard_deviation(self, cur: TeradataCursor ,table_name: str, col_name: str):
        try:    
            rows = cur.execute(f"select * from TD_UnivariateStatistics ( on {table_name} as InputTable using TargetColumns ('{col_name}') Stats('MEAN','STD')) as dt ORDER BY 1,2")
            return self.format_text_response(list([row for row in rows.fetchall()]))
        except Exception as e:
            logger.error(f"Error evaluating features: {e}")
            return self.format_error_response(str(e))

