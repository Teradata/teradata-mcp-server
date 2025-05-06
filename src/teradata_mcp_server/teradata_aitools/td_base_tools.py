import logging
from typing import Optional, Any, Dict, List
from teradatasql import TeradataConnection
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
    response = {
        "status": "success",
        "results": data
    }
    if metadata:
        response["metadata"] = metadata
    return json.dumps(response, default=serialize_teradata_types)


#------------------ Tool  ------------------#
# Read SQL execution tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries         
#       sql (str) - SQL query to execute
#     Returns: ResponseType - formatted response with query results or error message
def handle_execute_read_query(conn: TeradataConnection, sql: str, *args, **kwargs):
    logger.debug(f"Tool: handle_execute_read_query: Args: sql: {sql}")

    with conn.cursor() as cur:    
        rows = cur.execute(sql)  # type: ignore
        if rows is None:
            return create_response([])
            
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "sql": sql,
            "columns": [
                {"name": col[0], "type": col[1].__name__ if hasattr(col[1], '__name__') else str(col[1])}
                for col in cur.description
            ] if cur.description else [],
            "row_count": len(data)
        }
        return create_response(data, metadata)

        
#------------------ Tool  ------------------#
# Write SQL execution tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries         
#       sql (str) - SQL query to execute
#     Returns: ResponseType - formatted response with query results or error message
def handle_execute_write_query(conn: TeradataConnection, sql: str, *args, **kwargs):
    logger.debug(f"Tool: handle_execute_write_query: Args: sql: {sql}")

    with conn.cursor() as cur:   
        rows = cur.execute(sql)  # type: ignore
        if rows is None:
            return create_response([])
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "sql": sql,
            "affected_rows": cur.rowcount if hasattr(cur, 'rowcount') else None,
            "row_count": len(data)
        }
        return create_response(data, metadata)

        
#------------------ Tool  ------------------#
# Read SQL execution tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries         
#       db_name (str) - name of the database
#       table_name (str) - name of the table to get the definition for
#     Returns: ResponseType - formatted response with ddl results or error message
def handle_read_table_ddl(conn: TeradataConnection, db_name: str, table_name: str, *args, **kwargs):
    logger.debug(f"Tool: handle_read_table_ddl: Args: db_name: {db_name}, table_name: {table_name}")

    if len(db_name) == 0:
        db_name = "%"
    if len(table_name) == 0:
        table_name = "%"
    with conn.cursor() as cur:
        rows = cur.execute(f"show table {db_name}.{table_name}")
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "database": db_name,
            "table": table_name
        }
        return create_response(data, metadata)
        

#------------------ Tool  ------------------#
# Read database list tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries        
#     Returns: ResponseType - formatted response with list of databases or error message
def handle_read_database_list(conn: TeradataConnection, *args, **kwargs):
    logger.debug(f"Tool: handle_read_database_list: Args:")

    with conn.cursor() as cur:
        rows = cur.execute("select DataBaseName, DECODE(DBKind, 'U', 'User', 'D','DataBase') as DBType, CommentString from dbc.DatabasesV dv where OwnerName <> 'PDCRADM'")
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "total_count": len(data),
            "databases": len([d for d in data if d.get("DBType") == "DataBase"]),
            "users": len([d for d in data if d.get("DBType") == "User"])
        }
        return create_response(data, metadata)

        
#------------------ Tool  ------------------#
# Read table list tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries   
#       db_name (str) - name of the database to list objects from      
#     Returns: formatted response with list of tables in database or error message    
def handle_read_table_list(conn: TeradataConnection, db_name: str, *args, **kwargs):
    logger.debug(f"Tool: handle_read_table_list: Args: db_name: {db_name}")

    if len(db_name) == 0:
        db_name = "%"
    with conn.cursor() as cur:
        rows = cur.execute("select TableName from dbc.TablesV tv where UPPER(tv.DatabaseName) = UPPER(?) and tv.TableKind in ('T','V', 'O', 'Q');", [db_name])
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "database": db_name,
            "table_count": len(data)
        }
        return create_response(data, metadata)
        
#------------------ Tool  ------------------#
# Read column description tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries   
#       db_name (str) - name of the database to list objects from
#       obj_name (str) - name of the object to list columns from     
#     Returns: formatted response with list of columns and data types or error message
def handle_read_column_description(conn: TeradataConnection, db_name: str, obj_name: str, *args, **kwargs):
    logger.debug(f"Tool: handle_read_column_description: Args: db_name: {db_name}, obj_name: {obj_name}")

    if len(db_name) == 0:
        db_name = "%"
    if len(obj_name) == 0:
        obj_name = "%"
    with conn.cursor() as cur:
        query = """
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
        """
        rows = cur.execute(query, [obj_name, db_name])
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "database": db_name,
            "object": obj_name,
            "column_count": len(data)
        }
        return create_response(data, metadata)


#------------------ Tool  ------------------#
# Read table preview tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries   
#       db_name (str) - name of the database to list objects from
#       table_name (str) - name of the table to list columns from     
#     Returns: formatted response string or error message
def handle_read_table_preview(conn: TeradataConnection, table_name: str, db_name: Optional[str] = None, *args, **kwargs):
    """
    This function returns data sample and inferred structure from a database table or view.
    """
    logger.debug(f"Tool: handle_read_table_preview: Args: tablename: {table_name}, databasename: {db_name}")

    if db_name is not None:
        table_name = f"{db_name}.{table_name}"
    with conn.cursor() as cur:
        cur.execute(f'select top 5 * from {table_name}')
        columns = cur.description
        sample = rows_to_json(cur.description, cur.fetchall())

        metadata = {
            "tablename": table_name,
            "columns": [
                {
                    "name": c[0],
                    "type": c[1].__name__ if hasattr(c[1], '__name__') else str(c[1]),
                    "length": c[3]
                }
                for c in columns
            ],
            "sample_size": len(sample)
        }
        return create_response(sample, metadata)