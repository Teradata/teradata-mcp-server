import logging
from typing import Any
from typing import List
from pydantic import Field
import mcp.types as types
from teradatasql import TeradataCursor


logger = logging.getLogger("teradata_mcp_server")

class TDBaseTools:
    ResponseType = List[types.TextContent | types.ImageContent | types.EmbeddedResource]

    def format_text_response(self, text: Any) -> ResponseType:
        """Format a text response."""
        return [types.TextContent(type="text", text=str(text))]

    def format_error_response(self, error: str) -> ResponseType:
        """Format an error response."""
        return self.format_text_response(f"Error: {error}")

    #------------------ Tool  ------------------#
    # Read SQL execution tool
    #     Arguments: 
    #       cur (TeradataCursor) - Teradata cursor object for executing SQL queries        
    #       sql (str) - SQL query to execute
    #     Returns: ResponseType - formatted response with query results or error message
    def execute_read_query(self, cur: TeradataCursor ,sql: str):
        try:    
            rows = cur.execute(sql)  # type: ignore
            if rows is None:
                return self.format_text_response("No results")
            return self.format_text_response(list([row for row in rows.fetchall()]))
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return self.format_error_response(str(e))
        
    #------------------ Tool  ------------------#
    # Write SQL execution tool
    #     Arguments: 
    #       cur (TeradataCursor) - Teradata cursor object for executing SQL queries        
    #       sql (str) - SQL query to execute
    #     Returns: ResponseType - formatted response with query results or error message
    def execute_write_query(self, cur: TeradataCursor ,sql: str):
        try:    
            rows = cur.execute(sql)  # type: ignore
            if rows is None:
                return self.format_text_response("No results")
            return self.format_text_response(list([row for row in rows.fetchall()]))
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return self.format_error_response(str(e))    
        
    #------------------ Tool  ------------------#
    # Read SQL execution tool
    #     Arguments: 
    #       cur (TeradataCursor) - Teradata cursor object for executing SQL queries        
    #       db_name (str) - name of the database
    #       table_name (str) - name of the table to get the definition for
    #     Returns: ResponseType - formatted response with ddl results or error message
    def read_table_ddl(self, cur: TeradataCursor, db_name: str, table_name: str):
        try:
            if len(db_name) == 0:
                db_name = "%"
            if len(table_name) == 0:
                table_name = "%"

            rows = cur.execute(f"show table {db_name}.{table_name}")
            return self.format_text_response(list([row for row in rows.fetchall()]))
        except Exception as e:
            logger.error(f"Error evaluating features: {e}")
            return self.format_error_response(str(e))
        

    #------------------ Tool  ------------------#
    # Read database list tool
    #     Arguments: 
    #       cur (TeradataCursor) - Teradata cursor object for executing SQL queries        
    #     Returns: ResponseType - formatted response with list of databases or error message
    def read_database_list(self, cur: TeradataCursor):
        try:
            rows = cur.execute("select DataBaseName, DECODE(DBKind, 'U', 'User', 'D','DataBase') as DBType , CommentString from dbc.DatabasesV dv where OwnerName <> 'PDCRADM'")
            return self.format_text_response(list([row for row in rows.fetchall()]))
        except Exception as e:
            logger.error(f"Error listing schemas: {e}")
            return self.format_error_response(str(e))
        
    #------------------ Tool  ------------------#
    # Read table list tool
    #     Arguments: 
    #       cur (TeradataCursor) - Teradata cursor object for executing SQL queries  
    #       db_name (str) - name of the database to list objects from      
    #     Returns: ResponseType - formatted response with list of tables in database or error message    
    def read_table_list(self, cur: TeradataCursor, db_name: str):
        try:
            if len(db_name) == 0:
                db_name = "%"
            rows = cur.execute("select TableName from dbc.TablesV tv where UPPER(tv.DatabaseName) = UPPER(?) and tv.TableKind in ('T','V', 'O', 'Q');", [db_name])
            return self.format_text_response(list([row for row in rows.fetchall()]))
        except Exception as e:
            logger.error(f"Error listing schemas: {e}")
            return self.format_error_response(str(e))
        
    #------------------ Tool  ------------------#
    # Read column description tool
    #     Arguments: 
    #       cur (TeradataCursor) - Teradata cursor object for executing SQL queries   
    #       db_name (str) - name of the database to list objects from
    #       obj_name (str) - name of the object to list columns from     
    #     Returns: ResponseType - formatted response with list of columns and data types or error message
    def read_column_description(self, cur: TeradataCursor, db_name: str, obj_name: str):
        try:
            if len(db_name) == 0:
                db_name = "%"
            if len(obj_name) == 0:
                obj_name = "%"

            rows = cur.execute(
                """
                sel TableName, ColumnName, CASE ColumnType
                    WHEN '++' THEN 'TD_ANYTYPE'
                    WHEN 'A1' THEN 'UDT'
                    WHEN 'AT' THEN 'TIME'
                    WHEN 'BF' THEN 'BYTE'
                    WHEN 'BO' THEN 'BLOB'
                    WHEN 'BV' THEN 'VARBYTE'
                    WHEN 'CF' THEN 'CHAR'
                    WHEN 'CO' THEN 'CLOB'
                    WHEN 'CV' THEN 'VARCHAR'
                    WHEN 'D' THEN  'DECIMAL'
                    WHEN 'DA' THEN 'DATE'
                    WHEN 'DH' THEN 'INTERVAL DAY TO HOUR'
                    WHEN 'DM' THEN 'INTERVAL DAY TO MINUTE'
                    WHEN 'DS' THEN 'INTERVAL DAY TO SECOND'
                    WHEN 'DY' THEN 'INTERVAL DAY'
                    WHEN 'F' THEN  'FLOAT'
                    WHEN 'HM' THEN 'INTERVAL HOUR TO MINUTE'
                    WHEN 'HR' THEN 'INTERVAL HOUR'
                    WHEN 'HS' THEN 'INTERVAL HOUR TO SECOND'
                    WHEN 'I1' THEN 'BYTEINT'
                    WHEN 'I2' THEN 'SMALLINT'
                    WHEN 'I8' THEN 'BIGINT'
                    WHEN 'I' THEN  'INTEGER'
                    WHEN 'MI' THEN 'INTERVAL MINUTE'
                    WHEN 'MO' THEN 'INTERVAL MONTH'
                    WHEN 'MS' THEN 'INTERVAL MINUTE TO SECOND'
                    WHEN 'N' THEN 'NUMBER'
                    WHEN 'PD' THEN 'PERIOD(DATE)'
                    WHEN 'PM' THEN 'PERIOD(TIMESTAMP WITH TIME ZONE)'
                    WHEN 'PS' THEN 'PERIOD(TIMESTAMP)'
                    WHEN 'PT' THEN 'PERIOD(TIME)'
                    WHEN 'PZ' THEN 'PERIOD(TIME WITH TIME ZONE)'
                    WHEN 'SC' THEN 'INTERVAL SECOND'
                    WHEN 'SZ' THEN 'TIMESTAMP WITH TIME ZONE'
                    WHEN 'TS' THEN 'TIMESTAMP'
                    WHEN 'TZ' THEN 'TIME WITH TIME ZONE'
                    WHEN 'UT' THEN 'UDT'
                    WHEN 'YM' THEN 'INTERVAL YEAR TO MONTH'
                    WHEN 'YR' THEN 'INTERVAL YEAR'
                    WHEN 'AN' THEN 'UDT'
                    WHEN 'XM' THEN 'XML'
                    WHEN 'JN' THEN 'JSON'
                    WHEN 'DT' THEN 'DATASET'
                    WHEN '??' THEN 'STGEOMETRY''ANY_TYPE'
                    END as CType
                from DBC.ColumnsVX where upper(tableName) like upper(?) and upper(DatabaseName) like upper(?)
                """ , [obj_name,db_name])
            return self.format_text_response(list([row for row in rows.fetchall()]))
        except Exception as e:
            logger.error(f"Error listing schemas: {e}")
            return self.format_error_response(str(e))


    #------------------ Tool  ------------------#
    # Read column description tool
    #     Arguments: 
    #       cur (TeradataCursor) - Teradata cursor object for executing SQL queries   
    #       db_name (str) - name of the database to list objects from
    #       obj_name (str) - name of the object to list columns from     
    #     Returns: ResponseType - formatted response with list of columns and data types or error message

    # Place holder for the moment
    # def read_table_usage(self, cur: TeradataCursor, db_name: str, table_name: str):
    #     try:
    #         if len(db_name) == 0:
    #             db_name = "%"
    #         if len(table_name) == 0:
    #             table_name = "%"

    #         rows = cur.execute(f"show table {db_name}.{table_name}")
    #         return self.format_text_response(list([row for row in rows.fetchall()]))
    #     except Exception as e:
    #         logger.error(f"Error evaluating features: {e}")
    #         return self.format_error_response(str(e))
    # Tools
    # Standard methods to implement tool functionalities

from tabulate import tabulate
def peek_table(conn, tablename, databasename=None, *args, **kwargs):
    """
    This function returns data sample and inferred structure from a database table or view.
    """
    if databasename is not None:
        tablename = f"{databasename}.{tablename}"
    with conn.cursor() as cur:
        cur.execute(f'select top 5 * from {tablename}')
        columns=cur.description
        sample=cur.fetchall()

        # Format the column name and descriptions
        columns_desc=""
        for c in columns:
            columns_desc += f"- **{c[0]}**: {c[1].__name__} {f'({c[3]})' if c[3] else ''}\n"

        # Format the data sample as a table
        sample_tab=tabulate(sample, headers=[c[0] for c in columns], tablefmt='pipe')

        # Put the result together as a nicely formatted doc
        return \
f'''
# Database dataset description
Object name: **{tablename}**

## Object structure
Column names, data types and internal representation length if available.
{columns_desc}

## Data sample
This is a data sample:

{sample_tab}
'''    