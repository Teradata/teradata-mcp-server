# import logging

# from teradatasql import TeradataConnection

# from teradata_mcp_server.tools.utils import create_response, rows_to_json

# logger = logging.getLogger("teradata_mcp_server")


# # ------------------ Tool  ------------------#
# # Resource usage summary tool
# def handle_dba_resusageSummary(
#     conn: TeradataConnection,
#     dimensions: list[str] | None = None,
#     user_name: str | None = None,
#     date: str | None = None,
#     no_days: str | int | None = 30,
#     dayOfWeek: str | None = None,
#     hourOfDay: str | None = None,
#     workloadType: str | None = None,
#     workloadComplexity: str | None = None,
#     AppId: str | None = None,
#     *args,
#     **kwargs,
# ):
#     """
#     Get the Teradata system usage summary metrics by weekday and hour for each workload type and query complexity bucket.

#     Arguments:
#       dimensions - list of dimensions to aggregate the resource usage summary. All dimensions are: ["LogDate", "hourOfDay", "dayOfWeek", "workloadType", "workloadComplexity", "UserName", "AppId"]
#       user_name - user name
#       date - Date to analyze, formatted as `YYYY-MM-DD`
#       no_days - number of days to look back (default 30)
#       dayOfWeek - day of the week to analyze
#       hourOfDay - hour of day to analyze
#       workloadType - workload type to analyze, example: 'LOAD', 'ETL/ELT', 'EXPORT', 'QUERY', 'ADMIN', 'OTHER'
#       workloadComplexity - workload complexity to analyze, example: 'Ingest & Prep', 'Answers', 'System/Procedural'
#       AppId - Application ID to analyze, example: 'TPTLOAD%', 'TPTUPD%', 'FASTLOAD%', 'MULTLOAD%', 'EXECUTOR%', 'JDBC%'

#     """
#     logger.debug(f"Tool: handle_dba_resusageSummary: Args: dimensions: {dimensions}, no_days: {no_days}")

#     # Treat wildcards as "all users" (planner may pass *, %, or "all" instead of omitting)
#     if user_name and user_name.strip().lower() in ("*", "%", "all"):
#         user_name = None

#     # Normalize no_days: planner sends str or int inconsistently
#     if no_days is not None:
#         try:
#             no_days = int(no_days)
#         except (ValueError, TypeError):
#             no_days = 30
#         # no_days defines a date range; ignore single-date filter to avoid conflicting constraints
#         if date is not None:
#             logger.debug(f"Tool: handle_dba_resusageSummary: Ignoring date={date} because no_days={no_days} is set")
#             date = None

#     comment = "Total system resource usage summary."

#     # If dimensions is not None or empty, filter in the allowed dimensions
#     allowed_dimensions = [
#         "LogDate",
#         "hourOfDay",
#         "dayOfWeek",
#         "workloadType",
#         "workloadComplexity",
#         "UserName",
#         "AppId",
#     ]
#     unsupported_dimensions = []
#     if dimensions is not None:
#         unsupported_dimensions = [dim for dim in dimensions if dim not in allowed_dimensions]
#         dimensions = [dim for dim in dimensions if dim in allowed_dimensions]
#     else:
#         dimensions = []

#     # Update comment string based on dimensions used and supported.
#     if dimensions:
#         comment += "Metrics aggregated by " + ", ".join(dimensions) + "."
#     if unsupported_dimensions:
#         comment += (
#             "The following dimensions are not supported and will be ignored: " + ", ".join(unsupported_dimensions) + "."
#         )

#     # Dynamically construct the SELECT and GROUP BY clauses based on dimensions
#     dim_string = ", ".join(dimensions)
#     group_by_clause = ("GROUP BY " if dimensions else "") + dim_string
#     dim_string += "," if dimensions else ""

#     filter_clause = ""
#     filter_clause += f"AND UserName = '{user_name}' " if user_name else ""
#     filter_clause += f"AND LogDate = '{date}' " if date else ""
#     filter_clause += f"AND dayOfWeek = '{dayOfWeek}' " if dayOfWeek else ""
#     filter_clause += f"AND hourOfDay = '{hourOfDay}' " if hourOfDay else ""
#     filter_clause += f"AND workloadType = '{workloadType}' " if workloadType else ""
#     filter_clause += f"AND workloadComplexity = '{workloadComplexity}' " if workloadComplexity else ""
#     filter_clause += f"AND AppID LIKE '{AppId}' " if AppId else ""

#     query = f"""
#     SELECT
#         {dim_string}
#         COUNT(*) AS "Request Count",
#         SUM(AMPCPUTime) AS "Total AMPCPUTime",
#         SUM(TotalIOCount) AS "Total IOCount",
#         SUM(ReqIOKB) AS "Total ReqIOKB",
#         SUM(ReqPhysIO) AS "Total ReqPhysIO",
#         SUM(ReqPhysIOKB) AS "Total ReqPhysIOKB",
#         SUM(SumLogIO_GB) AS "Total ReqIO GB",
#         SUM(SumPhysIO_GB) AS "Total ReqPhysIOGB",
#         SUM(TotalServerByteCount) AS "Total Server Byte Count"
#     FROM
#         (
#             SELECT
#                 CAST(QryLog.Starttime as DATE) AS LogDate,
#                 EXTRACT(HOUR FROM StartTime) AS hourOfDay,
#                 CASE QryCal.day_of_week
#                     WHEN 1 THEN 'Sunday'
#                     WHEN 2 THEN 'Monday'
#                     WHEN 3 THEN 'Tuesday'
#                     WHEN 4 THEN 'Wednesday'
#                     WHEN 5 THEN 'Thursday'
#                     WHEN 6 THEN 'Friday'
#                     WHEN 7 THEN 'Saturday'
#                 END AS dayOfWeek,
#                 QryLog.UserName,
#                 QryLog.AcctString,
#                 QryLog.AppID ,
#                 CASE
#                     WHEN QryLog.AppID LIKE ANY('TPTLOAD%', 'TPTUPD%', 'FASTLOAD%', 'MULTLOAD%', 'EXECUTOR%', 'JDBCL%') THEN 'LOAD'
#                     WHEN QryLog.StatementType IN ('Insert', 'Update', 'Delete', 'Create Table', 'Merge Into')
#                         AND QryLog.AppID NOT LIKE ANY('TPTLOAD%', 'TPTUPD%', 'FASTLOAD%', 'MULTLOAD%', 'EXECUTOR%', 'JDBCL%') THEN 'ETL/ELT'
#                     WHEN QryLog.StatementType = 'Select' AND (AppID IN ('TPTEXP', 'FASTEXP') OR AppID LIKE 'JDBCE%') THEN 'EXPORT'
#                     WHEN QryLog.StatementType = 'Select'
#                         AND QryLog.AppID NOT LIKE ANY('TPTLOAD%', 'TPTUPD%', 'FASTLOAD%', 'MULTLOAD%', 'EXECUTOR%', 'JDBCL%') THEN 'QUERY'
#                     WHEN QryLog.StatementType IN ('Dump Database', 'Unrecognized type', 'Release Lock', 'Collect Statistics') THEN 'ADMIN'
#                     ELSE 'OTHER'
#                 END AS workloadType,
#                 CASE
#                     WHEN StatementType = 'Merge Into' THEN 'Ingest & Prep'
#                     WHEN StatementType = 'Select' THEN 'Answers'
#                     ELSE 'System/Procedural'
#                 END AS workloadComplexity,
#                 QryLog.AMPCPUTime,
#                 QryLog.TotalIOCount,
#                 QryLog.ReqIOKB,
#                 QryLog.ReqPhysIO,
#                 QryLog.ReqPhysIOKB,
#                 QryLog.TotalServerByteCount,
#                 (QryLog.ReqIOKB / 1024 / 1024) AS SumLogIO_GB,
#                 (QryLog.ReqPhysIOKB / 1024 / 1024) AS SumPhysIO_GB
#             FROM
#                 DBC.DBQLogTbl QryLog
#                 INNER JOIN Sys_Calendar.CALENDAR QryCal
#                     ON QryCal.calendar_date = CAST(QryLog.Starttime as DATE)
#             WHERE
#                 CAST(QryLog.Starttime as DATE) BETWEEN CURRENT_DATE - {no_days} AND CURRENT_DATE
#                 AND StartTime IS NOT NULL
#                 {filter_clause}
#         ) AS QryDetails
#         {group_by_clause}
#     """
#     logger.debug(f"Tool: handle_dba_resusageSummary: Query: {query}")
#     with conn.cursor() as cur:
#         logger.debug("Resource usage summary requested.")
#         rows = cur.execute(query)

#         data = rows_to_json(cur.description, rows.fetchall())
#         metadata = {"tool_name": "dba_resusageSummary", "total_rows": len(data), "comment": comment, "rows": len(data)}
#         logger.debug(f"Tool: handle_dba_resusageSummary: metadata: {metadata}")
#         return create_response(data, metadata)
