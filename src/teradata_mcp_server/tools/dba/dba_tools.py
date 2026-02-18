import logging

from teradatasql import TeradataConnection

from teradata_mcp_server.tools.utils import create_response, rows_to_json

logger = logging.getLogger("teradata_mcp_server")

#------------------ Tool  ------------------#
# Get table SQL tool
def handle_dba_tableSqlList(conn: TeradataConnection, table_name: str, no_days: str | int | None = 7,  *args, **kwargs):
    """
    Get a list of SQL run against a table in the last number of days.

    Arguments:
      table_name - table name
      no_days - number of days

    Returns:
      ResponseType: formatted response with query results + metadata
    """
    logger.debug(f"Tool: handle_dba_tableSqlList: Args: table_name: {table_name}, no_days: {no_days}")

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
            "tool_name": "dba_tableSqlList",
            "table_name": table_name,
            "no_days": no_days,
            "total_queries": len(data)
        }
        logger.debug(f"Tool: handle_dba_tableSqlList: metadata: {metadata}")
        return create_response(data, metadata)

#------------------ Tool  ------------------#
# Get user SQL tool
def handle_dba_userSqlList(conn: TeradataConnection, user_name: str = "", no_days: str | int | None = 7,  *args, **kwargs):
    """
    Get a list of SQL run by a user in the last number of days if a user name is provided, otherwise get list of all SQL in the last number of days.

    Arguments:
      user_name - user name
      no_days - number of days

    Returns:
      ResponseType: formatted response with query results + metadata
    """
    logger.debug(f"Tool: handle_dba_userSqlList: Args: user_name: {user_name}")

    # Treat wildcards as "all users" (planner may pass *, %, or "all" instead of omitting)
    if user_name and user_name.strip().lower() in ("*", "%", "all"):
        user_name = ""

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
            "tool_name": "dba_userSqlList",
            "user_name": user_name,
            "no_days": no_days,
            "total_queries": len(data)
        }
        logger.debug(f"Tool: handle_dba_userSqlList: metadata: {metadata}")
        return create_response(data, metadata)


#------------------ Tool  ------------------#
# Get table space tool
def handle_dba_tableSpace(conn: TeradataConnection, database_name: str | None = None, table_name: str | None = None, top_n: int | None = None, exclude_system: bool | None = None, *args, **kwargs):
    """
    Get table space used for a table if table name is provided or get table space for all tables in a database if a database name is provided."

    Arguments:
      database_name - database name
      table_name - table name
      top_n - limit results to top N largest tables (optional)
      exclude_system - exclude system databases, tables named 'All', and tables with dots in names (optional, default false)

    Returns:
      ResponseType: formatted response with query results + metadata
    """
    logger.debug(f"Tool: handle_dba_tableSpace: Args: database_name: {database_name}, table_name: {table_name}, top_n: {top_n}, exclude_system: {exclude_system}")

    # System databases to exclude (same list as base_databaseList)
    _SYSTEM_DBS = (
        "'DBC','SYSLIB','SystemFe','SYSUDTLIB','SYSJDBC','SYSSPATIAL',"
        "'TD_SYSFNLIB','TDQCD','TDStats','TDPUSER','dbcmngr','Crashdumps',"
        "'LockLogShredder','SYSBAR','SysAdmin','Sys_Calendar','EXTUSER',"
        "'DEFAULT','All','PUBLIC','SQLJ','SYSUIF','TD_ANALYTICS_DB',"
        "'TD_SERVER_DB','TD_SYSGPL','TDSYSFLOW','TDMaps','SAS_SYSFNLIB',"
        "'TDBCMgmt','External_AP','PDCRAdmin','PDCRSTG','PDCRDATA',"
        "'PDCRINFO','PDCRTPCD','PDCRADM','TD_DATASHARING_REPO',"
        "'TD_METRIC_SVC','console','tdwm','val'"
    )

    with conn.cursor() as cur:
        if not database_name and not table_name:
            if exclude_system:
                # Join with TablesV to get only actual tables (not SPs, views, macros)
                # Also exclude system databases and TDaaS-prefixed databases
                logger.debug("Returning top user tables only (exclude_system=true).")
                rows = cur.execute(f"""SELECT a.DatabaseName, a.TableName,
                    SUM(a.CurrentPerm) AS CurrentPerm1, SUM(a.PeakPerm) as PeakPerm,
                    CAST((100-(AVG(a.CURRENTPERM)/MAX(NULLIFZERO(a.CURRENTPERM))*100)) AS DECIMAL(5,2)) as SkewPct
                    FROM DBC.AllSpaceV a
                    INNER JOIN DBC.TablesV t ON a.DatabaseName = t.DatabaseName AND a.TableName = t.TableName
                    WHERE t.TableKind = 'T'
                    AND a.DatabaseName NOT IN ({_SYSTEM_DBS})
                    AND a.DatabaseName NOT LIKE 'TDaaS%'
                    AND a.TableName <> 'All'
                    AND a.TableName NOT LIKE 'hist_%'
                    AND a.TableName NOT LIKE '%.%'
                    GROUP BY a.DatabaseName, a.TableName
                    ORDER BY CurrentPerm1 desc;""")
            else:
                logger.debug("No database or table name provided, returning all tables and space information.")
                rows = cur.execute(f"""SELECT DatabaseName, TableName, SUM(CurrentPerm) AS CurrentPerm1, SUM(PeakPerm) as PeakPerm
                ,CAST((100-(AVG(CURRENTPERM)/MAX(NULLIFZERO(CURRENTPERM))*100)) AS DECIMAL(5,2)) as SkewPct
                FROM DBC.AllSpaceV
                GROUP BY DatabaseName, TableName
                ORDER BY CurrentPerm1 desc;""")
        elif not database_name:
            logger.debug(f"No database name provided, returning all space information for table: {table_name}.")
            rows = cur.execute(f"""SELECT DatabaseName, TableName, SUM(CurrentPerm) AS CurrentPerm1, SUM(PeakPerm) as PeakPerm
            ,CAST((100-(AVG(CURRENTPERM)/MAX(NULLIFZERO(CURRENTPERM))*100)) AS DECIMAL(5,2)) as SkewPct
            FROM DBC.AllSpaceV
            WHERE TableName = '{table_name}'
            GROUP BY DatabaseName, TableName
            ORDER BY CurrentPerm1 desc;""")
        elif not table_name:
            logger.debug(f"No table name provided, returning all tables and space information for database: {database_name}.")
            rows = cur.execute(f"""SELECT TableName, SUM(CurrentPerm) AS CurrentPerm1, SUM(PeakPerm) as PeakPerm
            ,CAST((100-(AVG(CURRENTPERM)/MAX(NULLIFZERO(CURRENTPERM))*100)) AS DECIMAL(5,2)) as SkewPct
            FROM DBC.AllSpaceV
            WHERE DatabaseName = '{database_name}'
            GROUP BY TableName
            ORDER BY CurrentPerm1 desc;""")
        else:
            logger.debug(f"Database name: {database_name}, Table name: {table_name}, returning space information for this table.")
            rows = cur.execute(f"""SELECT DatabaseName, TableName, SUM(CurrentPerm) AS CurrentPerm1, SUM(PeakPerm) as PeakPerm
            ,CAST((100-(AVG(CURRENTPERM)/MAX(NULLIFZERO(CURRENTPERM))*100)) AS DECIMAL(5,2)) as SkewPct
            FROM DBC.AllSpaceV
            WHERE DatabaseName = '{database_name}' AND TableName = '{table_name}'
            GROUP BY DatabaseName, TableName
            ORDER BY CurrentPerm1 desc;""")

        data = rows_to_json(cur.description, rows.fetchall())
        # Apply top_n limit after sorting (results already ordered by CurrentPerm1 desc)
        if top_n and len(data) > int(top_n):
            data = data[:int(top_n)]
        metadata = {
            "tool_name": "dba_tableSpace",
            "database_name": database_name,
            "table_name": table_name,
            "top_n": top_n,
            "total_tables": len(data)
        }
        logger.debug(f"Tool: handle_dba_tableSpace: metadata: {metadata}")
        return create_response(data, metadata)


#------------------ Tool  ------------------#
# Get database space tool
def handle_dba_databaseSpace(conn: TeradataConnection, database_name: str | None = None, *args, **kwargs):
    """
    Get database space if database name is provided, otherwise get all databases space allocations.

    Arguments:
      database_name - database name

    Returns:
      ResponseType: formatted response with query results + metadata
    """
    logger.debug(f"Tool: handle_dba_databaseSpace: Args: database_name: {database_name}")

    # Treat wildcards as "all databases" (planner may pass *, %, or "all" instead of omitting)
    if database_name and database_name.strip().lower() in ("*", "%", "all"):
        database_name = None

    database_name_filter = f"AND objectdatabasename = '{database_name}'" if database_name else ""

    with conn.cursor() as cur:
        if not database_name:
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
            logger.debug(f"Database name: {database_name}, returning space information for this database.")
            rows = cur.execute(f"""
                SELECT
                    DatabaseName,
                    CAST(SUM(MaxPerm)/1024/1024/1024 AS DECIMAL(10,2)) AS SpaceAllocated_GB,
                    CAST(SUM(CurrentPerm)/1024/1024/1024 AS DECIMAL(10,2)) AS SpaceUsed_GB,
                    CAST((SUM(MaxPerm) - SUM(CurrentPerm))/1024/1024/1024 AS DECIMAL(10,2)) AS FreeSpace_GB,
                    CAST((SUM(CurrentPerm) * 100.0 / NULLIF(SUM(MaxPerm),0)) AS DECIMAL(10,2)) AS PercentUsed
                FROM DBC.DiskSpaceV
                WHERE MaxPerm > 0
                AND DatabaseName = '{database_name}'
                GROUP BY 1;
            """)

        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "dba_databaseSpace",
            "database_name": database_name,
            "total_databases": len(data)
        }
        logger.debug(f"Tool: handle_dba_databaseSpace: metadata: {metadata}")
        return create_response(data, metadata)

#------------------ Tool  ------------------#
# Resource usage summary tool
def handle_dba_resusageSummary(conn: TeradataConnection,
                                 dimensions: list[str] | None = None,
                                 user_name: str | None = None,
                                 date:  str | None = None,
                                 no_days: str | int | None = 30,
                                 dayOfWeek:  str | None = None,
                                 hourOfDay:  str | None = None,
                                 workloadType: str | None = None,
                                 workloadComplexity: str | None = None,
                                 AppId: str | None = None,
                                 *args, **kwargs):

    """
    Get the Teradata system usage summary metrics by weekday and hour for each workload type and query complexity bucket.

    Arguments:
      dimensions - list of dimensions to aggregate the resource usage summary. All dimensions are: ["LogDate", "hourOfDay", "dayOfWeek", "workloadType", "workloadComplexity", "UserName", "AppId"]
      user_name - user name
      date - Date to analyze, formatted as `YYYY-MM-DD`
      no_days - number of days to look back (default 30)
      dayOfWeek - day of the week to analyze
      hourOfDay - hour of day to analyze
      workloadType - workload type to analyze, example: 'LOAD', 'ETL/ELT', 'EXPORT', 'QUERY', 'ADMIN', 'OTHER'
      workloadComplexity - workload complexity to analyze, example: 'Ingest & Prep', 'Answers', 'System/Procedural'
      AppId - Application ID to analyze, example: 'TPTLOAD%', 'TPTUPD%', 'FASTLOAD%', 'MULTLOAD%', 'EXECUTOR%', 'JDBC%'

    """
    logger.debug(f"Tool: handle_dba_resusageSummary: Args: dimensions: {dimensions}, no_days: {no_days}")

    # Treat wildcards as "all users" (planner may pass *, %, or "all" instead of omitting)
    if user_name and user_name.strip().lower() in ("*", "%", "all"):
        user_name = None

    # Normalize no_days: planner sends str or int inconsistently
    if no_days is not None:
        try:
            no_days = int(no_days)
        except (ValueError, TypeError):
            no_days = 30
        # no_days defines a date range; ignore single-date filter to avoid conflicting constraints
        if date is not None:
            logger.debug(f"Tool: handle_dba_resusageSummary: Ignoring date={date} because no_days={no_days} is set")
            date = None

    comment="Total system resource usage summary."

    # If dimensions is not None or empty, filter in the allowed dimensions
    allowed_dimensions = ["LogDate", "hourOfDay", "dayOfWeek", "workloadType", "workloadComplexity","UserName","AppId"]
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
    filter_clause += f"AND workloadType = '{workloadType}' " if workloadType else ""
    filter_clause += f"AND workloadComplexity = '{workloadComplexity}' " if workloadComplexity else ""
    filter_clause += f"AND AppID LIKE '{AppId}' " if AppId else ""

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
                CAST(QryLog.Starttime as DATE) BETWEEN CURRENT_DATE - {no_days} AND CURRENT_DATE
                AND StartTime IS NOT NULL
                {filter_clause}
        ) AS QryDetails
        {group_by_clause}
    """
    logger.debug(f"Tool: handle_dba_resusageSummary: Query: {query}")
    with conn.cursor() as cur:
        logger.debug("Resource usage summary requested.")
        rows = cur.execute(query)

        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "dba_resusageSummary",
            "total_rows": len(data) ,
            "comment": comment,
            "rows": len(data)
        }
        logger.debug(f"Tool: handle_dba_resusageSummary: metadata: {metadata}")
        return create_response(data, metadata)


#------------------ Tool  ------------------#
# Get table usage impact tool
def handle_dba_tableUsageImpact(conn: TeradataConnection, database_name: str | None = None, user_name: str | None = None, *args, **kwargs):
    """
    Measure the usage of a table and views by users, this is helpful to understand what user and tables are driving most resource usage at any point in time.

    Arguments:
      database_name - database name to analyze
      user_name - user name to analyze

    """
    logger.debug(f"Tool: handle_dba_tableUsageImpact: Args: database_name: {database_name}, user_name: {user_name}")

    # Treat wildcards as "all" (planner may pass * or % instead of omitting)
    if user_name and user_name.strip().lower() in ("*", "%", "all"):
        user_name = None
    if database_name and database_name.strip().lower() in ("*", "%", "all"):
        database_name = None

    database_name_filter = f"AND objectdatabasename = '{database_name}'" if database_name else ""
    user_name_filter = f"AND username = '{user_name}'" if user_name else ""
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
    logger.debug(f"Tool: handle_dba_tableUsageImpact: table_usage_sql: {table_usage_sql}")
    with conn.cursor() as cur:
        logger.debug("Database version information requested.")
        rows = cur.execute(table_usage_sql.format(database_name_filter=database_name_filter, user_name_filter=user_name_filter))
        data = rows_to_json(cur.description, rows.fetchall())
    if len(data):
        info=f'This data contains the list of tables most frequently queried objects in database schema {database_name}'
    else:
        info=f'No tables have recently been queried in the database schema {database_name}.'
    metadata = {
        "tool_name": "handle_dba_tableUsageImpact",
        "database": database_name,
        "table_count": len(data),
        "comment": info,
        "rows": len(data)
    }
    logger.debug(f"Tool: handle_dba_tableUsageImpact: metadata: {metadata}")
    return create_response(data, metadata)
