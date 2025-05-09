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
# Get SQL tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       user_name (str) - name of the user 
#     Returns: formatted response with list of QueryText and UserIDs or error message    
def handle_read_sql_list(conn: TeradataConnection, user_name: Optional[str] | None, no_days: Optional[int],  *args, **kwargs):
    logger.debug(f"Tool: handle_read_sql_list: Args: user_name: {user_name}")
    
    with conn.cursor() as cur:   
        if user_name == "":
            logger.debug("No user name provided, returning all SQL queries.")
            rows = cur.execute(f"""SELECT t1.QueryID, t1.ProcID, t1.CollectTimeStamp, t1.SqlTextInfo, t2.UserName 
            FROM DBC.QryLogSqlV t1 
            JOIN DBC.QryLogV t2 
            ON t1.QueryID = t2.QueryID 
            WHERE t1.CollectTimeStamp >= CURRENT_TIMESTAMP - INTERVAL '{no_days}' DAY
            ORDER BY t1.CollectTimeStamp DESC;""")
        else:
            logger.debug(f"User name provided: {user_name}, returning SQL queries for this user.")
            rows = cur.execute(f"""SELECT t1.QueryID, t1.ProcID, t1.CollectTimeStamp, t1.SqlTextInfo, t2.UserName 
            FROM DBC.QryLogSqlV t1 
            JOIN DBC.QryLogV t2 
            ON t1.QueryID = t2.QueryID 
            WHERE t1.CollectTimeStamp >= CURRENT_TIMESTAMP - INTERVAL '{no_days}' DAY
            AND t2.UserName = '{user_name}'
            ORDER BY t1.CollectTimeStamp DESC;""")
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "read_sql_list",
            "user_name": user_name, 
            "no_days": no_days,
            "total_queries": len(data)
        }
        return create_response(data, metadata)


#------------------ Tool  ------------------#
# Get table space tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       table_name (str) - name of the table
#       db_name (str) - name of the database 
#     Returns: formatted response with list of tables and space information or database and space used or error message    
def handle_read_table_space(conn: TeradataConnection, db_name: Optional[str] | None , table_name: Optional[str] | None, *args, **kwargs):
    logger.debug(f"Tool: handle_read_table_space: Args: db_name: {db_name}, table_name: {table_name}")
    
    with conn.cursor() as cur:   
        if (db_name == "") and (table_name == ""):
            logger.debug("No database or table name provided, returning all tables and space information.")
            rows = cur.execute(f"""SELECT DatabaseName, TableName, SUM(CurrentPerm) AS CurrentPerm1, SUM(PeakPerm) as PeakPerm 
            FROM DBC.AllSpaceV 
            GROUP BY DatabaseName, TableName 
            ORDER BY CurrentPerm1 desc;""")
        elif (db_name == ""):
            logger.debug(f"No database name provided, returning all space information for table: {table_name}.")
            rows = cur.execute(f"""SELECT DatabaseName, TableName, SUM(CurrentPerm) AS CurrentPerm1, SUM(PeakPerm) as PeakPerm 
            FROM DBC.AllSpaceV 
            WHERE TableName = '{table_name}' 
            GROUP BY DatabaseName, TableName 
            ORDER BY CurrentPerm1 desc;""")
        elif (table_name == ""):
            logger.debug(f"No table name provided, returning all tables and space information for database: {db_name}.")
            rows = cur.execute(f"""SELECT TableName, SUM(CurrentPerm) AS CurrentPerm1, SUM(PeakPerm) as PeakPerm 
            FROM DBC.AllSpaceV 
            WHERE DatabaseName = '{db_name}' 
            GROUP BY TableName 
            ORDER BY CurrentPerm1 desc;""")  
        else:
            logger.debug(f"Database name: {db_name}, Table name: {table_name}, returning space information for this table.")
            rows = cur.execute(f"""SELECT DatabaseName, TableName, SUM(CurrentPerm) AS CurrentPerm1, SUM(PeakPerm) as PeakPerm 
            FROM DBC.AllSpaceV 
            WHERE DatabaseName = '{db_name}' AND TableName = '{table_name}' 
            GROUP BY DatabaseName, TableName 
            ORDER BY CurrentPerm1 desc;""")

        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "read_table_space",
            "db_name": db_name,
            "table_name": table_name,
            "total_tables": len(data)
        }
        return create_response(data, metadata)


#------------------ Tool  ------------------#
# Get database space tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       db_name (str) - name of the database 
#     Returns: formatted response with list of databases and space information or error message    
def handle_read_database_space(conn: TeradataConnection, db_name: Optional[str] | None, *args, **kwargs):
    logger.debug(f"Tool: handle_read_database_space: Args: db_name: {db_name}")
    
    with conn.cursor() as cur:   
        if (db_name == ""):
            logger.debug("No database name provided, returning all databases and space information.")
            rows = cur.execute("""
                SELECT 
                    DatabaseName,
                    CAST(SUM(MaxPerm)/1024/1024/1024 AS DECIMAL(10,2)) AS SpaceAllocated_GB,
                    CAST(SUM(CurrentPerm)/1024/1024/1024 AS DECIMAL(10,2)) AS SpaceUsed_GB,
                    CAST((SUM(MaxPerm) - SUM(CurrentPerm))/1024/1024/1024 AS DECIMAL(10,2)) AS FreeSpace_GB,
                    CAST((SUM(CurrentPerm) * 100.0 / NULLIF(SUM(MaxPerm),0)) AS DECIMAL(10,2)) AS PercentUsed
                FROM DBC.DiskSpaceV 
                WHERE MaxPerm > 0 
                GROUP BY 1
                ORDER BY 5 DESC;
            """)
        else:
            logger.debug(f"Database name: {db_name}, returning space information for this database.")
            rows = cur.execute(f"""
                SELECT 
                    DatabaseName,
                    CAST(SUM(MaxPerm)/1024/1024/1024 AS DECIMAL(10,2)) AS SpaceAllocated_GB,
                    CAST(SUM(CurrentPerm)/1024/1024/1024 AS DECIMAL(10,2)) AS SpaceUsed_GB,
                    CAST((SUM(MaxPerm) - SUM(CurrentPerm))/1024/1024/1024 AS DECIMAL(10,2)) AS FreeSpace_GB,
                    CAST((SUM(CurrentPerm) * 100.0 / NULLIF(SUM(MaxPerm),0)) AS DECIMAL(10,2)) AS PercentUsed
                FROM DBC.DiskSpaceV 
                WHERE MaxPerm > 0 
                AND DatabaseName = '{db_name}'
                GROUP BY 1;
            """)

        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "read_database_space",
            "db_name": db_name,
            "total_databases": len(data)
        }
        return create_response(data, metadata)

#------------------ Tool  ------------------#
# Get database version tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#     Returns: formatted response with database version information or error message    
def handle_read_database_version(conn: TeradataConnection, *args, **kwargs):
    logger.debug(f"Tool: handle_read_database_version: Args: ")
    
    with conn.cursor() as cur:   
        logger.debug("Database version information requested.")
        rows = cur.execute(f"select InfoKey, InfoData FROM DBC.DBCInfoV;")

        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "read_database_version",
            "total_rows": len(data) 
        }
        return create_response(data, metadata)