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
# Get table SQL tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       user_name (str) - name of the user 
#     Returns: formatted response with list of QueryText and UserIDs or error message    
def handle_get_td_dba_tableSqlList(conn: TeradataConnection, table_name: str, no_days: Optional[int],  *args, **kwargs):
    logger.debug(f"Tool: handle_get_td_dba_tableSqlList: Args: table_name: {table_name}")

    with conn.cursor() as cur:
        if table_name == "":
            logger.debug("No table name provided")
        else:
            logger.debug(f"Table name provided: {table_name}, returning SQL queries for this table.")
            rows = cur.execute(f"""SELECT t1.QueryID, t1.ProcID, t1.CollectTimeStamp, t1.SqlTextInfo, t2.UserName 
            FROM DBC.QryLogSqlV t1 
            JOIN DBC.QryLogV t2 
            ON t1.QueryID = t2.QueryID 
            WHERE t1.CollectTimeStamp >= CURRENT_TIMESTAMP - INTERVAL '{no_days}' DAY
            AND t1.SqlTextInfo LIKE '%{table_name}%'
            ORDER BY t1.CollectTimeStamp DESC;""")

        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "get_td_dba_tableSqlList",
            "table_name": table_name,
            "no_days": no_days,
            "total_queries": len(data)
        }
        return create_response(data, metadata)

#------------------ Tool  ------------------#
# Get user SQL tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       user_name (str) - name of the user 
#     Returns: formatted response with list of QueryText and UserIDs or error message    
def handle_get_td_dba_userSqlList(conn: TeradataConnection, user_name: Optional[str] | None, no_days: Optional[int],  *args, **kwargs):
    logger.debug(f"Tool: handle_get_td_dba_userSqlList: Args: user_name: {user_name}")

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
            "tool_name": "get_td_dba_userSqlList",
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
def handle_get_td_dba_tableSpace(conn: TeradataConnection, db_name: Optional[str] | None , table_name: Optional[str] | None, *args, **kwargs):
    logger.debug(f"Tool: handle_get_td_dba_tableSpace: Args: db_name: {db_name}, table_name: {table_name}")

    with conn.cursor() as cur:
        if (db_name == "") and (table_name == ""):
            logger.debug("No database or table name provided, returning all tables and space information.")
            rows = cur.execute("""SELECT DatabaseName, TableName, SUM(CurrentPerm) AS CurrentPerm1, SUM(PeakPerm) as PeakPerm 
            ,CAST((100-(AVG(CURRENTPERM)/MAX(NULLIFZERO(CURRENTPERM))*100)) AS DECIMAL(5,2)) as SkewPct
            FROM DBC.AllSpaceV 
            GROUP BY DatabaseName, TableName 
            ORDER BY CurrentPerm1 desc;""")
        elif (db_name == ""):
            logger.debug(f"No database name provided, returning all space information for table: {table_name}.")
            rows = cur.execute(f"""SELECT DatabaseName, TableName, SUM(CurrentPerm) AS CurrentPerm1, SUM(PeakPerm) as PeakPerm 
            ,CAST((100-(AVG(CURRENTPERM)/MAX(NULLIFZERO(CURRENTPERM))*100)) AS DECIMAL(5,2)) as SkewPct
            FROM DBC.AllSpaceV 
            WHERE TableName = '{table_name}' 
            GROUP BY DatabaseName, TableName 
            ORDER BY CurrentPerm1 desc;""")
        elif (table_name == ""):
            logger.debug(f"No table name provided, returning all tables and space information for database: {db_name}.")
            rows = cur.execute(f"""SELECT TableName, SUM(CurrentPerm) AS CurrentPerm1, SUM(PeakPerm) as PeakPerm 
            ,CAST((100-(AVG(CURRENTPERM)/MAX(NULLIFZERO(CURRENTPERM))*100)) AS DECIMAL(5,2)) as SkewPct
            FROM DBC.AllSpaceV 
            WHERE DatabaseName = '{db_name}' 
            GROUP BY TableName 
            ORDER BY CurrentPerm1 desc;""")  
        else:
            logger.debug(f"Database name: {db_name}, Table name: {table_name}, returning space information for this table.")
            rows = cur.execute(f"""SELECT DatabaseName, TableName, SUM(CurrentPerm) AS CurrentPerm1, SUM(PeakPerm) as PeakPerm 
            ,CAST((100-(AVG(CURRENTPERM)/MAX(NULLIFZERO(CURRENTPERM))*100)) AS DECIMAL(5,2)) as SkewPct
            FROM DBC.AllSpaceV 
            WHERE DatabaseName = '{db_name}' AND TableName = '{table_name}' 
            GROUP BY DatabaseName, TableName 
            ORDER BY CurrentPerm1 desc;""")

        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "get_td_dba_tableSpace",
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
def handle_get_td_dba_databaseSpace(conn: TeradataConnection, db_name: Optional[str] | None, *args, **kwargs):
    logger.debug(f"Tool: handle_get_td_dba_databaseSpace: Args: db_name: {db_name}")

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
            "tool_name": "get_td_dba_databaseSpace",
            "db_name": db_name,
            "total_databases": len(data)
        }
        return create_response(data, metadata)

#------------------ Tool  ------------------#
# Get database version tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#     Returns: formatted response with database version information or error message    
def handle_get_td_dba_databaseVersion(conn: TeradataConnection, *args, **kwargs):
    logger.debug("Tool: handle_get_td_dba_databaseVersion: Args: ")

    with conn.cursor() as cur:
        logger.debug("Database version information requested.")
        rows = cur.execute("select InfoKey, InfoData FROM DBC.DBCInfoV;")

        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "get_td_dba_databaseVersion",
            "total_rows": len(data)
        }
        return create_response(data, metadata)
    
#------------------ Tool  ------------------#
# Resource usage summary tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       dimensions (List[str]) - list of dimensions to aggregate the resource usage summary. All dimensions are: ["LogDate", "hourOfDay", "dayOfWeek", "workloadType", "workloadComplexity", "UserName", "AppId", "StatementType"]
#     Returns: formatted response with aggregated resource usage summary or error message
def handle_get_td_dba_resusageSummary(conn: TeradataConnection, 
                                 dimensions: Optional[List[str]] = None,
                                 user_name: Optional[str] = None,
                                 date:  Optional[str] = None,
                                 dayOfWeek:  Optional[str] = None,
                                 hourOfDay:  Optional[str] = None,
                                 *args, **kwargs):

    logger.debug(f"Tool: handle_get_td_dba_resusageSummary: Args: dimensions: {dimensions}")

    comment="Total system resource usage summary."

    # If dimensions is not None or empty, filter in the allowed dimensions
    allowed_dimensions = ["LogDate", "hourOfDay", "dayOfWeek", "workloadType", "workloadComplexity","UserName","AppId","StatementType"]    
    unsupported_dimensions = []
    if dimensions is not None:
        unsupported_dimensions = [dim for dim in dimensions if dim not in allowed_dimensions]
        dimensions = [dim for dim in dimensions if dim in allowed_dimensions]
    else:
        dimensions=[]


    # Update comment string based on dimensions used and supported.
    if dimensions:
        comment+="Metrics aggregated by " + ", ".join(dimensions) + "."
    if unsupported_dimensions:
        comment+="The following dimensions are not supported and will be ignored: " + ", ".join(unsupported_dimensions) + "."

    # Dynamically construct the SELECT and GROUP BY clauses based on dimensions
    dim_string = ", ".join(dimensions)
    group_by_clause = ("GROUP BY " if dimensions else "")+dim_string
    dim_string += ("," if dimensions else "")

    filter_clause = ""
    filter_clause += f"AND UserName = '{user_name}' " if user_name else ""
    filter_clause += f"AND LogDate = '{date}' " if date else ""
    filter_clause += f"AND dayOfWeek = '{dayOfWeek}' " if dayOfWeek else ""
    filter_clause += f"AND hourOfDay = '{hourOfDay}' " if hourOfDay else ""

    query = f"""
    SELECT
        {dim_string}
        COUNT(*) AS "Request Count",
        SUM(AMPCPUTime) AS "Total AMPCPUTime",
        SUM(TotalIOCount) AS "Total IOCount",
        SUM(ReqIOKB) AS "Total ReqIOKB",
        SUM(ReqPhysIO) AS "Total ReqPhysIO",
        SUM(ReqPhysIOKB) AS "Total ReqPhysIOKB",
        SUM(SumLogIO_GB) AS "Total ReqIO GB",
        SUM(SumPhysIO_GB) AS "Total ReqPhysIOGB",
        SUM(TotalServerByteCount) AS "Total Server Byte Count"
    FROM
        (
            SELECT
                CAST(QryLog.Starttime as DATE) AS LogDate,
                EXTRACT(HOUR FROM StartTime) AS hourOfDay,
                CASE QryCal.day_of_week
                    WHEN 1 THEN 'Sunday'
                    WHEN 2 THEN 'Monday'
                    WHEN 3 THEN 'Tuesday'
                    WHEN 4 THEN 'Wednesday'
                    WHEN 5 THEN 'Thursday'
                    WHEN 6 THEN 'Friday'
                    WHEN 7 THEN 'Saturday'
                END AS dayOfWeek,
                QryLog.UserName,
                QryLog.AcctString,
                QryLog.AppID ,
                CASE
                    WHEN QryLog.AppID LIKE ANY('TPTLOAD%', 'TPTUPD%', 'FASTLOAD%', 'MULTLOAD%', 'EXECUTOR%', 'JDBCL%') THEN 'LOAD'
                    WHEN QryLog.StatementType IN ('Insert', 'Update', 'Delete', 'Create Table', 'Merge Into')
                        AND QryLog.AppID NOT LIKE ANY('TPTLOAD%', 'TPTUPD%', 'FASTLOAD%', 'MULTLOAD%', 'EXECUTOR%', 'JDBCL%') THEN 'ETL/ELT'
                    WHEN QryLog.StatementType = 'Select' AND (AppID IN ('TPTEXP', 'FASTEXP') OR AppID LIKE 'JDBCE%') THEN 'EXPORT'
                    WHEN QryLog.StatementType = 'Select'
                        AND QryLog.AppID NOT LIKE ANY('TPTLOAD%', 'TPTUPD%', 'FASTLOAD%', 'MULTLOAD%', 'EXECUTOR%', 'JDBCL%') THEN 'QUERY'
                    WHEN QryLog.StatementType IN ('Dump Database', 'Unrecognized type', 'Release Lock', 'Collect Statistics') THEN 'ADMIN'
                    ELSE 'OTHER'
                END AS workloadType,
                CASE
                    WHEN StatementType = 'Merge Into' THEN 'Ingest & Prep'
                    WHEN StatementType = 'Select' THEN 'Answers'
                    ELSE 'System/Procedural'
                END AS workloadComplexity,
                QryLog.AMPCPUTime,
                QryLog.TotalIOCount,
                QryLog.ReqIOKB,
                QryLog.ReqPhysIO,
                QryLog.ReqPhysIOKB,
                QryLog.TotalServerByteCount,
                (QryLog.ReqIOKB / 1024 / 1024) AS SumLogIO_GB,
                (QryLog.ReqPhysIOKB / 1024 / 1024) AS SumPhysIO_GB
            FROM
                DBC.DBQLogTbl QryLog
                INNER JOIN Sys_Calendar.CALENDAR QryCal
                    ON QryCal.calendar_date = CAST(QryLog.Starttime as DATE)
            WHERE
                CAST(QryLog.Starttime as DATE) BETWEEN CURRENT_DATE - 30 AND CURRENT_DATE
                AND StartTime IS NOT NULL
                {filter_clause}
        ) AS QryDetails
        {group_by_clause}
    """
    with conn.cursor() as cur:   
        logger.debug("Resource usage summary requested.")
        rows = cur.execute(query)

        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "get_td_dba_resusageSummary",
            "total_rows": len(data) ,
            "comment": comment
        }
        return create_response(data, metadata)


#------------------ Tool  ------------------#
# Get Flow Control tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#     Returns: formatted response with database flow control information or error message    
def handle_get_td_dba_flowControl(conn: TeradataConnection, *args, **kwargs):
    logger.debug("Tool: handle_get_td_dba_flowControl: Args: ")

    with conn.cursor() as cur:
        logger.debug("Database flow control information requested.")
        rows = cur.execute("""
                SELECT A.THEDATE AS "Date"  
                , A.THETIME (FORMAT '99:99:99') AS "Time"      
                , CASE  
                    WHEN DAY_OF_WEEK = 1 THEN 'Sun'
                    WHEN DAY_OF_WEEK = 2 THEN 'Mon'
                    WHEN DAY_OF_WEEK = 3 THEN 'Tue'
                    WHEN DAY_OF_WEEK = 4 THEN 'Wed'
                    WHEN DAY_OF_WEEK = 5 THEN 'Thr'
                    WHEN DAY_OF_WEEK = 6 THEN 'Fri'
                    WHEN DAY_OF_WEEK = 7 THEN 'Sat'
                    END AS DAY_OF_WEEK
                , A.FLOWCTLTIME AS "Flow Control Time" 
                , (A.FLOWCTLTIME / 1000) / A.SECS AS "FlowControl%" 
                , C.CPUUEXEC + C.CPUUSERV AS "CPUBusy"  
                , CPUIOWAIT AS "CPUWaitForIO"    
                , ((C.CPUUEXEC) / (C.CENTISECS * C.NCPUS)) * 100 AS "CPUEXEC%" 
                , ((C.CPUUSERV) / (C.CENTISECS * C.NCPUS)) * 100 AS "CPUSERV%" 
                , ((C.CPUIOWAIT) / (C.CENTISECS * C.NCPUS)) * 100 AS "WAITIO%"  
                , ((C.CPUIDLE) / (C.CENTISECS * C.NCPUS)) * 100 AS "IDLE%"  
                FROM DBC.RESUSAGESAWT A 
                INNER JOIN DBC.RESUSAGESVPR B   
                    ON A.VPRID = B.VPRID
                    AND A.THETIME = B.THETIME
                INNER JOIN DBC.RESUSAGESPMA C   
                    ON A.NODEID = C.NODEID
                    AND A.THETIME = C.THETIME
                    AND A.THEDATE = C.THEDATE
                INNER JOIN SYS_CALENDAR.CALENDAR D  
                    ON C.THEDATE = D.CALENDAR_DATE
                --WHERE A.THEDATE BETWEEN '2019-03-25' AND '2018-03-31'
                WHERE A.THEDATE > DATE - 7
                GROUP BY 1,2,3,4,5,6,7,8,9,10,11;    
                           """)

        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "get_td_dba_flowControl",
            "total_rows": len(data) 
        }
        return create_response(data, metadata)    

#------------------ Tool  ------------------#
# Get table usage impact tool
#     Arguments:
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       db_name (str) - name of the database
#       user_name (str) - name of the user
def handle_get_td_dba_tableUsageImpact(conn: TeradataConnection, db_name: Optional[str] = None, user_name: Optional[str] = None, *args, **kwargs):
    """
    Measure the usage of a table and views by users, this is helpful to understand what user and tables are driving most resource usage at any point in time.
    """
    logger.debug("Tool: handle_get_td_dba_tableUsageImpact: Args: ")
    if db_name:
        database_name_filter=f"AND objectdatabasename = '{db_name}'"
    else:
        database_name_filter=""

    if user_name:
        user_name_filter=f"AND username = '{user_name}'"
    else:
        user_name_filter=""


    table_usage_sql="""
    LOCKING ROW for ACCESS
    sel 
    DatabaseName
    ,TableName
    ,UserName
    ,Weight as "QueryCount"
    ,100*"Weight" / sum("Weight") over(partition by 1) PercentTotal
    ,case 
        when PercentTotal >=10 then 'High'
        when PercentTotal >=5 then 'Medium'
        else 'Low'
    end (char(6)) usage_freq
    ,FirstQueryDaysAgo
    ,LastQueryDaysAgo
        
    from
    (
        SELECT   TRIM(QTU1.TableName)  AS "TableName"
                , TRIM(QTU1.DatabaseName)  AS "DatabaseName"
                ,UserName as "UserName"
                ,max((current_timestamp - CollectTimeStamp) day(4)) as "FirstQueryDaysAgo"
                ,min((current_timestamp - CollectTimeStamp) day(4)) as "LastQueryDaysAgo"
                , COUNT(DISTINCT QTU1.QueryID) as "Weight"
        FROM    (
                    SELECT   objectdatabasename AS DatabaseName
                        , ObjectTableName AS TableName
                        , ob.QueryId
                    FROM DBC.DBQLObjTbl ob /* uncomment for DBC */
                    WHERE Objecttype in ('Tab', 'Viw')
                    {database_name_filter}
                    AND ObjectTableName IS NOT NULL
                    AND ObjectColumnName IS NULL
                    -- AND LogDate BETWEEN '2017-01-01' AND '2017-08-01' /* uncomment for PDCR */
                    --	AND LogDate BETWEEN current_date - 90 AND current_date - 1 /* uncomment for PDCR */
                    GROUP BY 1,2,3
                        ) AS QTU1
        INNER JOIN DBC.DBQLogTbl QU /* uncomment for DBC */
        ON QTU1.QueryID=QU.QueryID
        AND (QU.AMPCPUTime + QU.ParserCPUTime) > 0 
        {user_name_filter}

        GROUP BY 1,2, 3
    ) a
    order by PercentTotal desc
    qualify PercentTotal>0
    ;
    
    """

    with conn.cursor() as cur:
        logger.debug("Database version information requested.")
        rows = cur.execute(table_usage_sql.format(database_name_filter=database_name_filter, user_name_filter=user_name_filter))
        data = rows_to_json(cur.description, rows.fetchall())
    if len(data):
        info=f'This data contains the list of tables most frequently queried objects in database schema {db_name}'
    else:
        info=f'No tables have recently been queried in the database schema {db_name}.'
    metadata = {
        "tool_name": "handle_get_td_dba_tableUsageImpact",
        "database": db_name,
        "table_count": len(data),
        "comment": info
    }
    return create_response(data, metadata)


#------------------ Tool  ------------------#
# Get Feature Usage tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#     Returns: formatted response with database feature usage information or error message    
def handle_get_td_dba_featureUsage(conn: TeradataConnection, *args, **kwargs):
    logger.debug("Tool: handle_get_td_dba_featureUsage: Args: ")

    with conn.cursor() as cur:
        logger.debug("Database feature usage information requested.")
        rows = cur.execute("""
            SELECT 
                CAST(A.Starttime as Date)  AS LogDate
            ,A.USERNAME as Username
            ,CAST(B.FEATURENAME AS VARCHAR(100)) AS FEATURENAME
            ,SUM(GETBIT(A.FEATUREUSAGE,(2047 - B.FEATUREBITPOS))) AS FeatureUseCount
            ,COUNT(*) AS RequestCount
            ,SUM(AMPCPUTIME) AS AMPCPUTIME

            FROM DBC.DBQLOGTBL A, 
                DBC.QRYLOGFEATURELISTV B 
            WHERE CAST(A.Starttime as Date) > DATE-30
            GROUP BY 
                LogDate,
                USERNAME, 
                FeatureName having FeatureUseCount > 0
                ORDER BY 1,2,3;
                           """)

        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "get_td_dba_featureUsage",
            "total_rows": len(data) 
        }
        return create_response(data, metadata)    


#------------------ Tool  ------------------#
# Get User Delay Experience tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#     Returns: formatted response with database user delay experience information or error message    
def handle_get_td_dba_userDelay(conn: TeradataConnection, *args, **kwargs):
    logger.debug("Tool: handle_get_td_dba_userDelay: Args: ")

    with conn.cursor() as cur:
        logger.debug("Database user delay information requested.")
        rows = cur.execute("""
            Select
                CAST(a.Starttime as DATE) AS "Log Date"
                ,extract(hour from a.starttime) as "Log Hour"
                ,Username
                ,WDName
                ,Starttime
                ,a.firststeptime
                ,a.FirstRespTime
                ,Zeroifnull(DelayTime) as DelayTime
                , (CAST(extract(hour
                    From     ((a.firststeptime - a.StartTime) HOUR(2) TO SECOND(6) ) ) * 3600 + extract(minute
                    From     ((a.firststeptime - a.StartTime) HOUR(2) TO SECOND(6) ) ) * 60 + extract(second
                    From     ((a.firststeptime - a.StartTime) HOUR(2) TO SECOND(6) ) ) AS dec(8,2))) - zeroifnull(cast(delaytime as float)) (float)     as PrsDctnryTime

                , Zeroifnull(CAST(extract(hour
                    From     ((a.firstresptime - a.firststepTime) HOUR(2) TO SECOND(6) ) ) * 3600 + extract(minute
                    From     ((a.firstresptime - a.firststepTime) HOUR(2) TO SECOND(6) ) ) * 60 + extract(second
                    From     ((a.firstresptime - a.firststepTime) HOUR(2) TO SECOND(6) ) ) AS INTEGER) )  as QryRespTime

                , Zeroifnull(CAST(extract(hour
                    From     ((a.firstresptime - a.StartTime) HOUR(2) TO SECOND(6) ) ) * 3600 + extract(minute
                    From     ((a.firstresptime - a.StartTime) HOUR(2) TO SECOND(6) ) ) * 60 + extract(second
                    From     ((a.firstresptime - a.StartTime) HOUR(2) TO SECOND(6) ) ) AS INTEGER) )  as TotalTime
                ,count(*) As NoOfQueries
                from  DBC.DBQLogTbl a
                
                Where  DelayTime > 0
                AND CAST(a.Starttime as DATE) between current_date - 30 and current_date - 1
                Group By 1,2,3,4,5,6,7,8,9,10,11;
                           """)

        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "get_td_dba_userDelay",
            "total_rows": len(data)
        }
        return create_response(data, metadata)    
    