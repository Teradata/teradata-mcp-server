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
    
#------------------ Tool  ------------------#
# Resource usage summary tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#     Returns: formatted response with hourly resource usage version information or error message    
def handle_read_resusage_summary(conn: TeradataConnection, *args, **kwargs):
    logger.debug(f"Tool: handle_read_resusage_summary: Args: ")
    
    query="""
    SELECT
        LogHour					
        ,DayOfWeek as "Day Of Week"					
        ,WorkLoadType as "Workload Type"					
        ,CASE  				
            WHEN COMPLEXITY_Effect_Step BETWEEN 0  and 1 THEN '1. Simple'			
            WHEN COMPLEXITY_Effect_Step >1 and COMPLEXITY_Effect_Step <=2 THEN '2. Medium'			
            WHEN COMPLEXITY_Effect_Step >2 and COMPLEXITY_Effect_Step <=3 THEN '3. Complex'			
            WHEN COMPLEXITY_Effect_Step >3 THEN '4. Very Complex'			
        END as COMPLEXITY				
        ,COUNT(*) AS "Request Count" 					
        ,SUM(AMPCPUTime) AS "Total AMPCPUTime"					
        ,SUM(TotalIOCount) AS "Total IOCount"					
        ,SUM(ReqIOKB) AS "Total ReqIOKB"					
        ,SUM(ReqPhysIO) AS "Total ReqPhysIO"					
        ,SUM(ReqPhysIOKB) AS "Total ReqPhysIOKB"
        ,SUM(SumLogIO_GB) as "Total ReqIO GB"  
        ,SUM(SumPhysIO_GB) AS "Total ReqPhysIOGB"
        ,SUM(TotalServerByteCount) AS "Total Server Byte Count"					
    FROM
        (
            SELECT
                CAST(QryLog.Starttime as DATE) AS LogDate
                ,EXTRACT(HOUR FROM StartTime) AS LogHour
                ,
                CASE QryCal.day_of_week
                    WHEN 1
                        THEN 'Sunday'
                    WHEN 2
                        THEN 'Monday'
                    WHEN 3
                        THEN 'Tuesday'
                    WHEN 4
                        THEN 'Wednesday'
                    WHEN 5
                        THEN 'Thursday'
                    WHEN 6
                        THEN 'Friday'
                    WHEN 7
                        THEN 'Saturday'
                END AS DayOfWeek
                ,QryLog.UserName
                ,QryLog.AcctString
                ,QryLog.AppID
                ,QryLog.NumSteps
                ,QryLog.NumStepswPar 
                ,QryLog.MaxStepsInPar
                ,HASHAMP() + 1 AS Total_AMPs
                ,QryLog.QueryID
                ,QryLog.StatementType
                ,CASE					
                    WHEN QryLog.AppID LIKE ANY('TPTLOAD%', 'TPTUPD%', 'FASTLOAD%', 'MULTLOAD%', 'EXECUTOR%', 'JDBCL%')        THEN 'LOAD'					
                    WHEN QryLog.StatementType IN ('Insert', 'Update', 'Delete', 'Create Table', 'Merge Into') 					
                    AND QryLog.AppID NOT LIKE ANY('TPTLOAD%', 'TPTUPD%', 'FASTLOAD%', 'MULTLOAD%', 'EXECUTOR%', 'JDBCL%')    THEN 'ETL/ELT'					
                    WHEN QryLog.StatementType = 'Select' AND (AppID IN ('TPTEXP', 'FASTEXP') or appid like  'JDBCE%')         THEN 'EXPORT'					
                    WHEN QryLog.StatementType = 'Select'					
                        AND QryLog.AppID NOT LIKE ANY('TPTLOAD%', 'TPTUPD%', 'FASTLOAD%', 'MULTLOAD%', 'EXECUTOR%', 'JDBCL%') THEN 'QUERY'					
                    WHEN QryLog.StatementType in ('Dump Database','Unrecognized type','Release Lock','Collect Statistics')    THEN 'ADMIN'                  					
                                                                                                                            ELSE 'OTHER'					
                END AS WorkLoadType					
                ,CASE WHEN StatementType = 'Merge Into' THEN 'Ingest & Prep'		
                    WHEN StatementType = 'Begin Loading' THEN 'Ingest & Prep'	
                    WHEN StatementType = 'Mload' THEN 'Ingest & Prep'	
                    WHEN StatementType = 'Collect Statistics' THEN 'Data Maintenance'	
                    WHEN StatementType = 'Delete' THEN 'Ingest & Prep'	
                    WHEN StatementType = 'End Loading' THEN 'Ingest & Prep'	
                    WHEN StatementType = 'Begin Delete Mload' THEN 'Ingest & Prep'	
                    WHEN StatementType = 'Update' THEN 'Ingest & Prep'	
                    WHEN StatementType = 'Select' THEN 'Answers'	
                    WHEN StatementType = 'Exec' THEN 'Ingest & Prep'	
                    WHEN StatementType = 'Release Mload' THEN 'Ingest & Prep'	
                    WHEN StatementType = 'Insert' THEN 'Ingest & Prep'	
                    WHEN StatementType = 'Begin Mload' THEN 'Ingest & Prep'	
                    WHEN StatementType = 'Execute Mload' THEN 'Ingest & Prep'	
                    WHEN StatementType = 'Commit Work' THEN 'Ingest & Prep'	
                    ELSE 'System/Procedural' 	
                END AS StatementOutcome		
                ,					
                CASE					
                    WHEN StatementType = 'Select'					
                        AND AppID NOT IN ('TPTEXP', 'FASTEXP')					
                        AND Execution_Time_Secs < 1					
                        AND NumOfActiveAMPs < Total_AMPs					
                        THEN 'Tactical'					
                    ELSE					
                        'Non-Tactical'					
                END AS QueryType					
                ,					
                CASE					
                    WHEN TotalServerByteCount > 0					
                        THEN 'QueryGrid'					
                    ELSE					
                        'Local'					
                END AS QueryOrigin					
                ,QryLog.NumOfActiveAMPs					
                ,QryLog.AMPCPUTime					
                        
                ,QryLog.TotalIOCount					
                ,QryLog.ReqIOKB 		
                ,QryLog.ReqPhysIO 					
                ,QryLog.ReqPhysIOKB 					
                ,QryLog.ParserCPUTime		
                ,QryLog.CacheFlag		
                ,QryLog.DelayTime		
                ,QryLog.TotalServerByteCount		
                ,(select MAX(QryLog.AMPCPUTime) FROM DBC.DBQLogTbl QryLog WHERE CAST(QryLog.Starttime as DATE) BETWEEN current_date - 30  AND current_date - 1 AND StartTime IS NOT NULL) as MAXCPU   --Observed CPU Cieling		
                ,(select MAX(QryLog.TotalIOCount) FROM DBC.DBQLogTbl QryLog WHERE CAST(QryLog.Starttime as DATE) BETWEEN current_date - 30  AND current_date - 1 AND StartTime IS NOT NULL) as MAXIO  --Observed I/O Ceiling		
                ,(select MAX(QryLog.NumSteps) FROM DBC.DBQLogTbl QryLog WHERE CAST(QryLog.Starttime as DATE) BETWEEN current_date - 30  AND current_date - 1 AND StartTime IS NOT NULL) as MAXSTEPS --Observed NumSteps Ceiling		
                        
                ,		
                CASE  		
                    WHEN QryLog.AMPCPUTime BETWEEN ((MAXCPU/10)*0)  and ((MAXCPU/10)*1) THEN 0		
                    WHEN QryLog.AMPCPUTime BETWEEN ((MAXCPU/10)*1)  and ((MAXCPU/10)*2) THEN 1	
                    WHEN QryLog.AMPCPUTime BETWEEN ((MAXCPU/10)*2)  and ((MAXCPU/10)*3) THEN 2	
                    WHEN QryLog.AMPCPUTime BETWEEN ((MAXCPU/10)*3)  and ((MAXCPU/10)*4) THEN 3	
                    WHEN QryLog.AMPCPUTime BETWEEN ((MAXCPU/10)*4)  and ((MAXCPU/10)*5) THEN 4	
                    WHEN QryLog.AMPCPUTime BETWEEN ((MAXCPU/10)*5)  and ((MAXCPU/10)*6) THEN 5	
                    WHEN QryLog.AMPCPUTime BETWEEN ((MAXCPU/10)*6)  and ((MAXCPU/10)*7) THEN 6	
                    WHEN QryLog.AMPCPUTime BETWEEN ((MAXCPU/10)*7)  and ((MAXCPU/10)*8) THEN 7	
                    WHEN QryLog.AMPCPUTime BETWEEN ((MAXCPU/10)*8)  and ((MAXCPU/10)*9) THEN 8	
                    WHEN QryLog.AMPCPUTime BETWEEN ((MAXCPU/10)*9)  and ((MAXCPU/10)*10) THEN 9	
                    WHEN QryLog.AMPCPUTime > ((MAXCPU/10)*10) THEN 10	
                END as COMPLEXITY_CPU		
                ,		
                CASE  		
                    WHEN QryLog.TotalIOCount BETWEEN ((MAXIO/10)*0)  and ((MAXIO/10)*1) THEN 0		
                    WHEN QryLog.TotalIOCount BETWEEN ((MAXIO/10)*1)  and ((MAXIO/10)*2) THEN 1	
                    WHEN QryLog.TotalIOCount BETWEEN ((MAXIO/10)*2)  and ((MAXIO/10)*3) THEN 2	
                    WHEN QryLog.TotalIOCount BETWEEN ((MAXIO/10)*3)  and ((MAXIO/10)*4) THEN 3	
                    WHEN QryLog.TotalIOCount BETWEEN ((MAXIO/10)*4)  and ((MAXIO/10)*5) THEN 4	
                    WHEN QryLog.TotalIOCount BETWEEN ((MAXIO/10)*5)  and ((MAXIO/10)*6) THEN 5	
                    WHEN QryLog.TotalIOCount BETWEEN ((MAXIO/10)*6)  and ((MAXIO/10)*7) THEN 6	
                    WHEN QryLog.TotalIOCount BETWEEN ((MAXIO/10)*7)  and ((MAXIO/10)*8) THEN 7	
                    WHEN QryLog.TotalIOCount BETWEEN ((MAXIO/10)*8)  and ((MAXIO/10)*9) THEN 8	
                    WHEN QryLog.TotalIOCount BETWEEN ((MAXIO/10)*9)  and ((MAXIO/10)*10) THEN 9	
                    WHEN QryLog.TotalIOCount > ((MAXIO/10)*10) THEN 10	
                END as COMPLEXITY_IO		
                ,		
                CASE  		
                    WHEN QryLog.NumSteps BETWEEN ((MAXSTEPS/10)*0)  and ((MAXSTEPS/10)*1) THEN 0		
                    WHEN QryLog.NumSteps BETWEEN ((MAXSTEPS/10)*1)  and ((MAXSTEPS/10)*2) THEN 1	
                    WHEN QryLog.NumSteps BETWEEN ((MAXSTEPS/10)*2)  and ((MAXSTEPS/10)*3) THEN 2	
                    WHEN QryLog.NumSteps BETWEEN ((MAXSTEPS/10)*3)  and ((MAXSTEPS/10)*4) THEN 3	
                    WHEN QryLog.NumSteps BETWEEN ((MAXSTEPS/10)*4)  and ((MAXSTEPS/10)*5) THEN 4	
                    WHEN QryLog.NumSteps BETWEEN ((MAXSTEPS/10)*5)  and ((MAXSTEPS/10)*6) THEN 5	
                    WHEN QryLog.NumSteps BETWEEN ((MAXSTEPS/10)*6)  and ((MAXSTEPS/10)*7) THEN 6	
                    WHEN QryLog.NumSteps BETWEEN ((MAXSTEPS/10)*7)  and ((MAXSTEPS/10)*8) THEN 7	
                    WHEN QryLog.NumSteps BETWEEN ((MAXSTEPS/10)*8)  and ((MAXSTEPS/10)*9) THEN 8	
                    WHEN QryLog.NumSteps BETWEEN ((MAXSTEPS/10)*9)  and ((MAXSTEPS/10)*10) THEN 9	
                    WHEN QryLog.NumSteps > ((MAXSTEPS/10)*10) THEN 10	
                END as COMPLEXITY_NUMSTEPS		
                        
                ,(((COMPLEXITY_CPU + COMPLEXITY_IO + COMPLEXITY_NUMSTEPS + 0.7)/3)(DECIMAL(6,0))) as COMPLEXITY_Effect_Step		
                ,(((COMPLEXITY_CPU + COMPLEXITY_IO + 0.5)/2) (DECIMAL(6,0))) as COMPLEXITY_Effect	
                ,		
                CASE					
                    WHEN DelayTime is NULL					
                        THEN '0000 - 0000'					
                    WHEN DelayTime < 1.0 or DelayTime is NULL	
                        THEN '0000 - 0001'					
                    WHEN DelayTime BETWEEN 1.0 AND 5.0					
                        THEN '0001 - 0005'					
                    WHEN DelayTime BETWEEN 5.0 AND 10.0					
                        THEN '0005 - 0010'					
                    WHEN DelayTime BETWEEN 10.0 AND 30.0					
                        THEN '0010 - 0030'					
                    WHEN DelayTime BETWEEN 30.0 AND 60.0					
                        THEN '0030 - 0060'					
                    WHEN DelayTime BETWEEN 60.0 AND 300.0					
                        THEN '0060 - 0300'					
                    WHEN DelayTime BETWEEN 300.0 AND 600.0					
                        THEN '0300 - 0600'					
                    WHEN DelayTime BETWEEN 600.0 AND 1800.0					
                        THEN '0600 - 1800'					
                    WHEN DelayTime BETWEEN 1800.0 AND 3600.0					
                        THEN '1800 - 3600'					
                    WHEN DelayTime > 3600.0					
                        THEN '3600+'					
                END AS DelaySeconds_Class					
                ,((FirstRespTime - StartTime) HOUR(3) TO SECOND(6)) AS Execution_Time					
                ,((FirstStepTime - StartTime) HOUR(3) TO SECOND(6)) AS Parse_Time					
                ,((COALESCE(LastRespTime,FirstRespTime) - FirstRespTime) HOUR(3) TO SECOND(6)) AS Transfer_Time					
                ,ZEROIFNULL(CAST(EXTRACT(HOUR FROM Execution_Time) * 3600 + EXTRACT(MINUTE FROM Execution_Time) * 60 + EXTRACT(SECOND FROM Execution_Time) AS FLOAT)) AS Execution_Time_Secs					
                ,ZEROIFNULL(CAST(EXTRACT(HOUR FROM Transfer_Time) * 3600 + EXTRACT(MINUTE FROM Transfer_Time) * 60 + EXTRACT(SECOND FROM Transfer_Time) AS FLOAT)) AS Transfer_Time_Secs					
                ,ZEROIFNULL(CAST(EXTRACT(HOUR FROM Parse_Time) * 3600 + EXTRACT(MINUTE FROM Parse_Time) * 60 + EXTRACT(SECOND FROM Parse_Time) AS FLOAT)) AS Parse_Time_Secs					
                ,		
                CASE					
                    WHEN Parse_Time_Secs IS NULL					
                        THEN '0000 - 0000'					
                    WHEN Parse_Time_Secs < 1.0	
                        THEN '0000 - 0001'					
                    WHEN Parse_Time_Secs BETWEEN 1.0 AND 5.0					
                        THEN '0001 - 0005'					
                    WHEN Parse_Time_Secs BETWEEN 5.0 AND 10.0					
                        THEN '0005 - 0010'					
                    WHEN Parse_Time_Secs BETWEEN 10.0 AND 30.0					
                        THEN '0010 - 0030'					
                    WHEN Parse_Time_Secs BETWEEN 30.0 AND 60.0					
                        THEN '0030 - 0060'					
                    WHEN Parse_Time_Secs BETWEEN 60.0 AND 300.0					
                        THEN '0060 - 0300'					
                    WHEN Parse_Time_Secs BETWEEN 300.0 AND 600.0					
                        THEN '0300 - 0600'					
                    WHEN Parse_Time_Secs BETWEEN 600.0 AND 1800.0					
                        THEN '0600 - 1800'					
                    WHEN Parse_Time_Secs BETWEEN 1800.0 AND 3600.0					
                        THEN '1800 - 3600'					
                    WHEN Parse_Time_Secs > 3600.0					
                        THEN '3600+'					
                END AS Parse_Time_Class					
                ,		
                CASE					
                    WHEN AMPCPUTime IS NULL					
                        THEN '00000 - 000000'					
                    WHEN AMPCPUTime < 1.0	
                        THEN '00000 - 000001'					
                    WHEN AMPCPUTime BETWEEN 1.0 AND 10.0					
                        THEN '00001 - 000010'					
                    WHEN AMPCPUTime BETWEEN 10.0 AND 100.0					
                        THEN '00010 - 000100'					
                    WHEN AMPCPUTime BETWEEN 100.0 AND 1000.0					
                        THEN '00100 - 001000'					
                    WHEN AMPCPUTime BETWEEN 1000.0 AND 10000.0					
                        THEN '01000 - 010000'					
                    WHEN AMPCPUTime BETWEEN 10000.0 AND 100000.0					
                        THEN '10000 - 100000'					
                    WHEN AMPCPUTime > 100000.0					
                        THEN '100000+'					
                END AS AMPCPUTime_Class					
                ,		
                CASE					
                    WHEN ParserCPUTime IS NULL					
                        THEN '00000 - 00000'					
                    WHEN ParserCPUTime < 1.0	
                        THEN '00000 - 00001'					
                    WHEN ParserCPUTime BETWEEN 1.0 AND 5.0					
                        THEN '00001 - 00005'					
                    WHEN ParserCPUTime BETWEEN 5.0 AND 10.0					
                        THEN '00005 - 00010'					
                    WHEN ParserCPUTime BETWEEN 10.0 AND 50.0					
                        THEN '00010 - 00050'					
                    WHEN ParserCPUTime BETWEEN 50.0 AND 100.0					
                        THEN '00050 - 00100'					
                    WHEN ParserCPUTime BETWEEN 100.0 AND 500.0					
                        THEN '00100 - 00500'					
                    WHEN ParserCPUTime BETWEEN 500.0 AND 1000.0					
                        THEN '00500 - 01000'					
                    WHEN ParserCPUTime BETWEEN 1000.0 AND 5000.0					
                        THEN '01000 - 05000'					
                    WHEN ParserCPUTime BETWEEN 5000.0 AND 10000.0					
                        THEN '05000 - 10000'					
                    WHEN ParserCPUTime > 10000.0					
                        THEN '10000+'					
                END AS ParserCPUTime_Class					
                ,		
                CASE					
                    WHEN TotalIOCount IS NULL					
                        THEN '1e0-1e0'					
                    WHEN TotalIOCount < 1e4	
                        THEN '1e0-1e4'					
                    WHEN TotalIOCount BETWEEN 1e4 AND 1e6					
                        THEN '1e4-1e6'					
                    WHEN TotalIOCount BETWEEN 1e6 AND 1e8					
                        THEN '1e6-1e8'					
                    WHEN TotalIOCount BETWEEN 1e8 AND 1e10					
                        THEN '1e8-1e10'					
                    WHEN TotalIOCount > 1e10					
                        THEN '1e10+'					
                END AS TotalIOCount_Class					
                ,					
                CASE					
                    WHEN Execution_Time_Secs IS NULL					
                        THEN '00000 - 000000'					
                    WHEN Execution_Time_Secs < 1.0	
                        THEN '00000 - 000001'					
                    WHEN Execution_Time_Secs BETWEEN 1.0 AND 1e1					
                        THEN '00001 - 000010'					
                    WHEN Execution_Time_Secs BETWEEN 1e1 AND 1e2					
                        THEN '00010 - 000100'					
                    WHEN Execution_Time_Secs BETWEEN 1e2 AND 1e3					
                        THEN '00100 - 001000'					
                    WHEN Execution_Time_Secs BETWEEN 1e3 AND 1e4					
                        THEN '01000 - 010000'					
                    WHEN Execution_Time_Secs > 1e4					
                        THEN '10000+'					
                END AS Execution_Time_Class					
                ,					
                CASE					
                    WHEN TotalIOCount = 0					
                        THEN 'No I/O'					
                    WHEN TotalIOCount > 0 AND ReqPhysIO = 0	
                        THEN 'In Memory'					
                    WHEN TotalIOCount > 0 AND ReqPhysIO > 0					
                        THEN 'Physical I/O'					
                END AS IO_Optimization					
                        
                        
    /*   IOPS  Metrics  */					
    , (totaliocount)/1000 SumKio					
    , (ReqPhysIO)/1000  SumPhysKioCnt					
    , zeroifnull( SumPhysKioCnt/nullifzero(SumKio) )  CacheMissPctIOPS					
                                            
    /*  IO Bytes Metrics  */					
    , (ReqIOKB)/1e6 SumLogIO_GB					
    , (ReqPhysIOKB)/1e6 SumPhysIO_GB					
    , zeroifnull(SumPhysIO_GB/nullifzero(SumLogIO_GB))  CacheMissPctGB					
                        
    /* METRIC:   Cache Miss Rate IOPS.  normal cache miss rate <20%,   set score = 0  for  miss rate < 20%,  increments of 10%, range 0 -80 */  					
                ,		
                case		
                    when  SumPhysKioCnt = 0 then 0   	
                    when   zeroifnull(SumPhysKioCnt/ nullifzero(SumKio)) <= 0.20 then 0                         /* set score = 0 when less than industry average 20% */					
                    when   SumPhysKioCnt > SumKio then 80                                                       /* sometimes get Physical > Logical, set ceiling at 80*/					
                    else (cast( 100 * zeroifnull (SumPhysKioCnt/ nullifzero(SumKio)) /10 as  integer) * 10) - 20  /* only count above 20%, round to bin size 10*/					
                end as CacheMissIOPSScore                    					
                                            
    /* METRIC:   Cache Miss Rate KB.  normal cache miss rate <20%,   set score = 0  for  miss rate < 20%,  increments of 10%, range 0 -80 */  					
                ,  		
                case 		
                    when  SumPhysIO_GB = 0 then 0   	
                    when   zeroifnull(SumPhysIO_GB/ nullifzero(SumLogIO_GB)) <= 0.20 then 0                   /* set score = 0 when less than industry average 20% */					
                    when   SumPhysIO_GB > SumLogIO_GB then 80                                  /* sometimes get Physical > Logical, set ceiling at 80*/					
                    else  (cast( 100 * zeroifnull (SumPhysIO_GB/ nullifzero(SumLogIO_GB)) /10 as  integer) * 10) - 20   /* only count above 20%, round to bin size 10*/					
                end as CacheMissKBScore   					
                ,					
                CASE					
                    WHEN Transfer_Time_Secs IS NULL 					
                        THEN '0000 - 0000'					
                    WHEN Transfer_Time_Secs < 1.0	
                        THEN '0000 - 0001'					
                    WHEN Transfer_Time_Secs BETWEEN 1.0 AND 5.0					
                        THEN '0001 - 0005'					
                    WHEN Transfer_Time_Secs BETWEEN 5.0 AND 10.0					
                        THEN '0005 - 0010'					
                    WHEN Transfer_Time_Secs BETWEEN 10.0 AND 30.0					
                        THEN '0010 - 0030'					
                    WHEN Transfer_Time_Secs BETWEEN 30.0 AND 60.0					
                        THEN '0030 - 0060'					
                    WHEN Transfer_Time_Secs BETWEEN 60.0 AND 300.0					
                        THEN '0060 - 0300'					
                    WHEN Transfer_Time_Secs BETWEEN 300.0 AND 600.0					
                        THEN '0300 - 0600'					
                    WHEN Transfer_Time_Secs BETWEEN 600.0 AND 1800.0					
                        THEN '0600 - 1800'					
                    WHEN Transfer_Time_Secs BETWEEN 1800.0 AND 3600.0					
                        THEN '1800 - 3600'					
                    WHEN Transfer_Time_Secs > 3600.0					
                        THEN '3600+'					
                END AS Transfer_Time_Class					
            FROM		
                DBC.DBQLogTbl QryLog					
                INNER JOIN					
                Sys_Calendar.CALENDAR QryCal					
                    ON QryCal.calendar_date = CAST(QryLog.Starttime as DATE)					
            WHERE					
                LogDate BETWEEN current_date - 30  AND current_date - 1					
                AND StartTime IS NOT NULL					
        ) AS QryDetails					
    GROUP BY					
        1  --X					
        ,2					
        ,3					
        ,4				
    """
    with conn.cursor() as cur:   
        logger.debug("Resource usage summary requested.")
        rows = cur.execute(query)

        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "read_resusage_summary",
            "total_rows": len(data) ,
            "comment": "Total system resource usage summary by type of workload and query complexity bucket. Metrics are computed aggregated at the hour and day of week level."
        }
        return create_response(data, metadata)



    