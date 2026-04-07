"""
base_tools.py - Teradata MCP Server Base Tools
================================================
Core database exploration and metadata tools for the Teradata MCP Server.

All tool handler functions receive a ``conn: TeradataConnection`` instance
injected by the MCP server framework and use the native ``conn.cursor()``
pattern with positional ``?`` bind parameters.

Author:  Paul Dancer
Version: 1.4.2 - Fixed Primary? flag check (P/S not Y/N) in IndexTypeString
"""

import fnmatch
import logging
import re
<<<<<<< Updated upstream
from collections.abc import Callable
=======
import inspect
import time
>>>>>>> Stashed changes

from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import text
from sqlalchemy.engine import Connection, default
from teradatasql import TeradataConnection

from teradata_mcp_server.tools.utils import create_response, rows_to_json

logger = logging.getLogger("teradata_mcp_server")


<<<<<<< Updated upstream
# ------------------ Tool  ------------------#
# Read query tool
=======
# ============================================================================
# Tool: base_readQuery
# ============================================================================
>>>>>>> Stashed changes
def handle_base_readQuery(
    conn: Connection, sql: str | None = None, tool_name: str | None = None, persist: bool = False, *args, **kwargs
):
    """
    Execute a SQL query via SQLAlchemy, bind parameters if provided
    (prepared SQL), and return the fully rendered SQL (with literals)
    in metadata.

    Arguments:
      sql     - SQL text, with optional bind-parameter placeholders
      persist - Set to True to persist the results as a table and reuse it later. Recommended for large result sets.

    Returns:
      ResponseType: formatted response with query results + metadata
                   (includes 'volatile_table' field in metadata if persist=True)
    """
<<<<<<< Updated upstream
    logger.debug(f"Tool: handle_base_readQuery: Args: sql: {sql}, persist: {persist}, args={args!r}, kwargs={kwargs!r}")

    # Generate volatile table name if persisting
    volatile_table_name = None
    if persist:
        import uuid

        unique_id = str(uuid.uuid4()).replace("-", "_")[:16]
        volatile_table_name = f"vt_{unique_id}"

        # Strip trailing semicolons from the SQL
        sql_clean = (sql or "").rstrip().rstrip(";")

        # Remove the final ORDER BY clause if present
        sql_clean = re.sub(r"ORDER BY [\w\W\s\S]*$", "", sql_clean, flags=re.IGNORECASE).strip()

        # Wrap in CREATE VOLATILE TABLE statement
        sql = f"CREATE VOLATILE TABLE {volatile_table_name} AS ({sql_clean}) WITH DATA ON COMMIT PRESERVE ROWS"
        logger.info(f"Persisting query results to volatile table: {volatile_table_name}")
=======
    logger.debug(
        f"Tool: handle_base_readQuery: Args: sql: {sql}, args={args!r}, kwargs={kwargs!r}")
>>>>>>> Stashed changes

    # 1. Build a textual SQL statement
    if not sql:
        return create_response([], {"tool_name": tool_name or "base_readQuery", "error": "No SQL provided"})
    stmt = text(sql)

    # 2. Bind parameters to the statement if provided.
    #    We use bindparams() instead of passing a dict to conn.execute() because
    #    the teradatasql driver uses qmark paramstyle and SQLAlchemy's parameter
    #    binding via conn.execute(stmt, dict) does not reliably translate named
    #    parameters for this dialect. Binding directly to the text object ensures
    #    correct compilation and also renders correct values in literal_binds metadata.
    if kwargs:
        stmt = stmt.bindparams(**kwargs)

    result = conn.execute(stmt)

    # 3. Fetch rows & column metadata

    # If we persisted in a volatile table, we won't get any rows back, we sample the resulting voltile table instead
    if volatile_table_name:
        result = conn.execute(text(f"select top 10 * from {volatile_table_name}"))

    cursor = result.cursor  # underlying DB-API cursor
    raw_rows = cursor.fetchall() or []

<<<<<<< Updated upstream
    # 4. Check if this is a SHOW command (DDL extraction)
    is_show_command = sql and sql.strip().upper().startswith("SHOW ")

    if is_show_command and raw_rows and len(raw_rows[0]) == 1:
        # This is a SHOW command - concatenate all rows into single DDL
        ddl_parts = [row[0] for row in raw_rows if row and row[0]]
        ddl_complete = "".join(ddl_parts)

        data = [{"RequestText": ddl_complete, "DDL_Size_Chars": len(ddl_complete), "Original_Row_Count": len(raw_rows)}]

        columns = [
            {"name": "RequestText", "type": "str"},
            {"name": "DDL_Size_Chars", "type": "int"},
            {"name": "Original_Row_Count", "type": "int"},
        ]
        logger.info(f"SHOW command detected: concatenated {len(raw_rows)} rows into {len(ddl_complete)} chars")
    else:
        data = rows_to_json(cursor.description, list(raw_rows))
        columns = [
            {"name": col[0], "type": getattr(col[1], "__name__", str(col[1]))} for col in (cursor.description or [])
        ]

    # 5. Compile the statement with literal binds for "final SQL"
    #    Fallback to DefaultDialect if conn has no `.dialect`
=======
    # 4. Compile the statement with literal binds for "final SQL"
    #    Fallback to DefaultDialect if conn has no ``.dialect``
>>>>>>> Stashed changes
    dialect = getattr(conn, "dialect", default.DefaultDialect())
    compiled = stmt.compile(dialect=dialect, compile_kwargs={"literal_binds": True})
    final_sql = str(compiled)

    # 5. Build metadata using the rendered SQL
    metadata = {
        "tool_name": tool_name if tool_name else "base_readQuery",
        "sql": final_sql,
        "columns": columns,
        "row_count": len(data),
    }

    # Add volatile table name if persisted
    if volatile_table_name:
        metadata["row_count"] = None
        metadata["sample_size"] = 10
        metadata["volatile_table"] = volatile_table_name
        metadata["persist"] = True
        logger.info(f"Query results persisted to volatile table: {volatile_table_name}")

    if is_show_command and "ddl_complete" in locals():
        metadata["ddl_size"] = len(ddl_complete)
        metadata["rows_concatenated"] = len(raw_rows)

    logger.debug(f"Tool: handle_base_readQuery: metadata: {metadata}")
    return create_response(data, metadata)


<<<<<<< Updated upstream
# ------------------ Tool  ------------------#
# List databases tool
def handle_base_databaseList(conn: TeradataConnection, scope: str | None = None, *args, **kwargs):
=======
# ============================================================================
# Tool: base_databaseList
# ============================================================================
def handle_base_databaseList(conn: TeradataConnection, *args, **kwargs):
>>>>>>> Stashed changes
    """
    Lists databases in the Teradata System.

    Arguments:
      scope - Filter scope: 'user' returns only user-created databases (excludes system databases), 'all' returns every database. Defaults to 'user' if not specified.

    Returns:
      ResponseType: formatted response with query results + metadata
    """
    scope = (scope or "user").strip().lower()
    logger.debug(f"Tool: handle_base_databaseList: Args: scope={scope}")

    # System databases to exclude when scope is 'user'
    system_dbs = (
        "'DBC','SYSLIB','SystemFe','SYSUDTLIB','SYSJDBC','SYSSPATIAL',"
        "'TD_SYSFNLIB','TDQCD','TDStats','TDPUSER','dbcmngr','Crashdumps',"
        "'LockLogShredder','SYSBAR','SysAdmin','Sys_Calendar','EXTUSER',"
        "'DEFAULT','All','PUBLIC','SQLJ','SYSUIF','TD_ANALYTICS_DB',"
        "'TD_SERVER_DB','TD_SYSGPL','TDSYSFLOW','TDMaps','SAS_SYSFNLIB',"
        "'TDBCMgmt','External_AP','PDCRAdmin','PDCRSTG','PDCRDATA',"
        "'PDCRINFO','PDCRTPCD','PDCRADM','TD_DATASHARING_REPO',"
        "'TD_METRIC_SVC','console','tdwm','val'"
    )

    if scope == "all":
        sql = "SELECT DataBaseName, DECODE(DBKind, 'U', 'User', 'D', 'DataBase') AS DBType, CommentString FROM dbc.DatabasesV dv WHERE OwnerName <> 'PDCRADM'"
    else:
        sql = f"SELECT DataBaseName, DECODE(DBKind, 'U', 'User', 'D', 'DataBase') AS DBType, CommentString FROM dbc.DatabasesV dv WHERE OwnerName <> 'PDCRADM' AND DataBaseName NOT IN ({system_dbs}) AND DataBaseName NOT LIKE 'TDaaS%'"

    with conn.cursor() as cur:
        rows = cur.execute(sql)
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "base_databaseList",
            "scope": scope,
            "sql": sql,
            "columns": [
<<<<<<< Updated upstream
                {"name": col[0], "type": col[1].__name__ if hasattr(col[1], "__name__") else str(col[1])}
=======
                {"name": col[0], "type": col[1].__name__ if hasattr(
                    col[1], '__name__') else str(col[1])}
>>>>>>> Stashed changes
                for col in cur.description
            ]
            if cur.description
            else [],
            "row_count": len(data),
        }
        logger.debug(f"Tool: handle_base_databaseList: metadata: {metadata}")
        return create_response(data, metadata)


<<<<<<< Updated upstream
# ------------------ Tool  ------------------#
# List tables tool
=======
# ============================================================================
# Tool: base_tableList
# ============================================================================
>>>>>>> Stashed changes
def handle_base_tableList(conn: TeradataConnection, database_name: str | None = None, *args, **kwargs):
    """
    Lists all tables in a database.

    Arguments:
      database_name - Database name

    Returns:
      ResponseType: formatted response with query results + metadata
    """
    logger.debug(
        f"Tool: handle_base_tableList: Args: database_name: {database_name}")

    # Treat wildcards as "all" (planner may pass *, %, or "all" instead of omitting)
    if database_name and database_name.strip().lower() in ("*", "%", "all"):
        database_name = None

    sql = "select TableName from dbc.TablesV tv where tv.TableKind in ('T','V', 'O', 'Q')"
    params = []

    if database_name:
        sql += " and UPPER(tv.DatabaseName) = UPPER(?)"
        params.append(database_name)

    with conn.cursor() as cur:
        rows = cur.execute(sql, params)
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "base_tableList",
            "sql": sql.replace("?", f"'{database_name}'"),
            "columns": [
<<<<<<< Updated upstream
                {"name": col[0], "type": col[1].__name__ if hasattr(col[1], "__name__") else str(col[1])}
=======
                {"name": col[0], "type": col[1].__name__ if hasattr(
                    col[1], '__name__') else str(col[1])}
>>>>>>> Stashed changes
                for col in cur.description
            ]
            if cur.description
            else [],
            "row_count": len(data),
        }
        logger.debug(f"Tool: handle_base_tableList: metadata: {metadata}")
        return create_response(data, metadata)


<<<<<<< Updated upstream
# ------------------ Tool  ------------------#
# get DDL tool
=======
# ============================================================================
# Tool: base_tableDDL
# ============================================================================
>>>>>>> Stashed changes
def handle_base_tableDDL(conn: TeradataConnection, database_name: str | None, table_name: str, *args, **kwargs):
    """
    Displays the DDL definition of a table via SQLAlchemy, bind parameters
    if provided (prepared SQL), and return the fully rendered SQL (with
    literals) in metadata.

    Arguments:
      database_name - Database name
      table_name - table name

    Returns:
      ResponseType: formatted response with query results + metadata
    """
    logger.debug(
        f"Tool: handle_base_tableDDL: Args: database_name: {database_name}, table_name: {table_name}")

    if database_name is not None:
        table_name = f"{database_name}.{table_name}"
    with conn.cursor() as cur:
        rows = cur.execute(f"show table {table_name}")
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {"tool_name": "base_tableDDL", "database": database_name, "table": table_name, "rows": len(data)}
        logger.debug(f"Tool: handle_base_tableDDL: metadata: {metadata}")
        return create_response(data, metadata)


<<<<<<< Updated upstream
# ------------------ Tool  ------------------#
# Read column description tool
=======
# ============================================================================
# Tool: base_columnDescription
# ============================================================================
>>>>>>> Stashed changes
def handle_base_columnDescription(conn: TeradataConnection, database_name: str | None, obj_name: str, *args, **kwargs):
    """
    Shows detailed column information about a database table via SQLAlchemy,
    bind parameters if provided (prepared SQL), and return the fully rendered
    SQL (with literals) in metadata.

    Arguments:
      database_name - Database name
      obj_name - table or view name

    Returns:
      ResponseType: formatted response with query results + metadata
    """
    logger.debug(
        f"Tool: handle_base_columnDescription: Args: database_name: {database_name}, obj_name: {obj_name}")

    if not database_name:
        database_name = "%"
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
        rows = cur.execute(query, [obj_name, database_name])
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "base_columnDescription",
            "database": database_name,
            "object": obj_name,
            "column_count": len(data),
        }
        logger.debug(
            f"Tool: handle_base_columnDescription: metadata: {metadata}")
        return create_response(data, metadata)


<<<<<<< Updated upstream
# ------------------ Tool  ------------------#
# Read table preview tool
def handle_base_tablePreview(
    conn: TeradataConnection, table_name: str, database_name: str | None = None, *args, **kwargs
):
=======
# ============================================================================
# Tool: base_tablePreview
# ============================================================================
def handle_base_tablePreview(conn: TeradataConnection, table_name: str, database_name: str | None = None, *args, **kwargs):
>>>>>>> Stashed changes
    """
    This function returns data sample and inferred structure from a database
    table or view via SQLAlchemy, bind parameters if provided (prepared SQL),
    and return the fully rendered SQL (with literals) in metadata.

    Arguments:
      table_name - table or view name
      database_name - Database name

    Returns:
      ResponseType: formatted response with query results + metadata
    """
    logger.debug(
        f"Tool: handle_base_tablePreview: Args: tablename: {table_name}, databasename: {database_name}")

    if database_name is not None:
        table_name = f"{database_name}.{table_name}"
    with conn.cursor() as cur:
        cur.execute(f"select top 5 * from {table_name}")
        columns = cur.description
        sample = rows_to_json(cur.description, cur.fetchall())

        metadata = {
            "tool_name": "base_tablePreview",
            "database": database_name,
            "table_name": table_name,
            "columns": [
                {"name": c[0], "type": c[1].__name__ if hasattr(c[1], "__name__") else str(c[1]), "length": c[3]}
                for c in columns
            ],
            "sample_size": len(sample),
        }
        logger.debug(f"Tool: handle_base_tablePreview: metadata: {metadata}")
        return create_response(sample, metadata)


<<<<<<< Updated upstream
# ------------------ Tool  ------------------#
# Read table affinity tool
=======
# ============================================================================
# Tool: base_tableAffinity
# ============================================================================
>>>>>>> Stashed changes
def handle_base_tableAffinity(conn: TeradataConnection, database_name: str, obj_name: str, *args, **kwargs):
    """
    Get tables commonly used together by database users, this is helpful to
    infer relationships between tables via SQLAlchemy, bind parameters if
    provided (prepared SQL), and return the fully rendered SQL (with literals)
    in metadata.

    Arguments:
      database_name - Database name
      object_name - table or view name

    Returns:
      ResponseType: formatted response with query results + metadata
    """
<<<<<<< Updated upstream
    logger.debug(f"Tool: handle_base_tableAffinity: Args: database_name: {database_name}, obj_name: {obj_name}")
=======
    logger.debug(
        f"Tool: handle_base_tableAffinity: Args: database_name: {database_name}, obj_name: {obj_name}")
>>>>>>> Stashed changes
    table_affiity_sql = """
    LOCKING ROW for ACCESS
    SELECT   TRIM(QTU2.DatabaseName)  AS "DatabaseName"
            , TRIM(QTU2.TableName)  AS "TableName"
            , COUNT(DISTINCT QTU1.QueryID) AS "QueryCount"
            , (current_timestamp - min(QTU2.CollectTimeStamp)) day(4) as "FirstQueryDaysAgo"
            , (current_timestamp - max(QTU2.CollectTimeStamp)) day(4) as "LastQueryDaysAgo"
    FROM    (
                        SELECT   objectdatabasename AS DatabaseName
                            , ObjectTableName AS TableName
                            , QueryId
                        FROM DBC.DBQLObjTbl /* for DBC */
                        WHERE Objecttype in ('Tab', 'Viw')
                        AND ObjectTableName = '{table_name}'
                        AND objectdatabasename = '{database_name}'
                        AND ObjectTableName IS NOT NULL
                        AND ObjectColumnName IS NULL
                        -- AND LogDate BETWEEN '2017-01-01' AND '2017-08-01' /* uncomment for PDCR */
                        --	AND LogDate BETWEEN current_date - 90 AND current_date - 1 /* uncomment for PDCR */
                        GROUP BY 1,2,3
                    ) AS QTU1
                    INNER JOIN
                    (
                        SELECT   objectdatabasename AS DatabaseName
                            , ObjectTableName AS TableName
                            , QueryId
                            , CollectTimeStamp
                        FROM DBC.DBQLObjTbl /* for DBC */
                        WHERE Objecttype in ('Tab', 'Viw')
                        AND ObjectTableName IS NOT NULL
                        AND ObjectColumnName IS NULL
                        GROUP BY 1,2,3, 4
                    ) AS QTU2
                    ON QTU1.QueryID=QTU2.QueryID
                    INNER JOIN DBC.DBQLogTbl QU /* uncomment for DBC */
                    -- INNER JOIN DBC.DBQLogTbl QU /* uncomment for PDCR */
                    ON QTU1.QueryID=QU.QueryID
    WHERE (TRIM(QTU2.TableName) <> TRIM(QTU1.TableName) OR  TRIM(QTU2.DatabaseName) <> TRIM(QTU1.DatabaseName))
    AND (QU.AMPCPUTime + QU.ParserCPUTime) > 0
    GROUP BY 1,2
    ORDER BY 3 DESC, 5 DESC
--    having "QueryCount">10
    ;

    """
    with conn.cursor() as cur:
        rows = cur.execute(table_affiity_sql.format(
            table_name=obj_name, database_name=database_name))
        data = rows_to_json(cur.description, rows.fetchall())
    if len(data):
<<<<<<< Updated upstream
        affinity_info = (
            f"This data contains the list of tables most commonly queried alongside object {database_name}.{obj_name}"
        )
    else:
        affinity_info = f"Object {database_name}.{obj_name} is not often queried with any other table or queried at all, try other ways to infer its relationships."
=======
        affinity_info = f'This data contains the list of tables most commonly queried alongside object {database_name}.{obj_name}'
    else:
        affinity_info = f'Object {database_name}.{obj_name} is not often queried with any other table or queried at all, try other ways to infer its relationships.'
>>>>>>> Stashed changes
    metadata = {
        "tool_name": "handle_base_tableAffinity",
        "database": database_name,
        "object": obj_name,
        "table_count": len(data),
        "comment": affinity_info,
    }
    logger.debug(f"Tool: handle_base_tableAffinity: metadata: {metadata}")
    return create_response(data, metadata)


<<<<<<< Updated upstream
# ------------------ Tool  ------------------#
# Read table usage tool
=======
# ============================================================================
# Tool: base_tableUsage
# ============================================================================
>>>>>>> Stashed changes
def handle_base_tableUsage(conn: TeradataConnection, database_name: str | None = None, *args, **kwargs):
    """
    Measure the usage of a table and views by users in a given schema, this
    is helpful to infer what database objects are most actively used or drive
    most value via SQLAlchemy, bind parameters if provided (prepared SQL),
    and return the fully rendered SQL (with literals) in metadata.

    Arguments:
      database_name - Database name

    Returns:
      ResponseType: formatted response with query results + metadata
    """

    logger.debug("Tool: handle_base_tableUsage: Args: database_name:")

    # Treat wildcards as "all" (planner may pass *, %, or "all" instead of omitting)
    if database_name and database_name.strip().lower() in ("*", "%", "all"):
        database_name = None

    database_name_filter = f"AND objectdatabasename = '{database_name}'" if database_name else ""

    table_usage_sql = """
    LOCKING ROW for ACCESS
    sel
    DatabaseName
    ,TableName
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
                ,max((current_timestamp - CollectTimeStamp) day(4)) as "FirstQueryDaysAgo"
                ,min((current_timestamp - CollectTimeStamp) day(4)) as "LastQueryDaysAgo"
                , COUNT(DISTINCT QTU1.QueryID) as "Weight"
        FROM    (
                            SELECT   objectdatabasename AS DatabaseName
                                , ObjectTableName AS TableName
                                , QueryId
                            FROM DBC.DBQLObjTbl /* uncomment for DBC */
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

        GROUP BY 1,2
    ) a
    order by PercentTotal desc
    qualify PercentTotal>0
    ;

    """

    with conn.cursor() as cur:
        rows = cur.execute(table_usage_sql.format(
            database_name_filter=database_name_filter))
        data = rows_to_json(cur.description, rows.fetchall())
    if len(data):
<<<<<<< Updated upstream
        info = (
            f"This data contains the list of tables most frequently queried objects in database schema {database_name}"
        )
    else:
        info = f"No tables have recently been queried in the database schema {database_name}."
=======
        info = f'This data contains the list of tables most frequently queried objects in database schema {database_name}'
    else:
        info = f'No tables have recently been queried in the database schema {database_name}.'
>>>>>>> Stashed changes
    metadata = {
        "tool_name": "handle_base_tableUsage",
        "database": database_name,
        "table_count": len(data),
        "comment": info,
    }
    logger.debug(f"Tool: handle_base_tableUsage: metadata: {metadata}")
    return create_response(data, metadata)


<<<<<<< Updated upstream
# ------------------ Tool  ------------------#
# Dynamic SQL execution tool
def util_base_dynamicQuery(conn: TeradataConnection, sql_generator: Callable[..., str], *args, **kwargs):
=======
# ============================================================================
# Utility: Dynamic SQL execution
# ============================================================================
def util_base_dynamicQuery(conn: TeradataConnection, sql_generator: callable, *args, **kwargs):
>>>>>>> Stashed changes
    """
    This tool is used to execute dynamic SQL queries that are generated at
    runtime by a generator function.

    Arguments:
      sql_generator (callable) - a generator function that returns a SQL
                                 query string

    Returns:
      ResponseType: formatted response with query results + metadata
    """
    logger.debug(f"Tool: util_base_dynamicQuery: Args: sql: {sql_generator}")

    sql = sql_generator(*args, **kwargs)
    with conn.cursor() as cur:
        rows = cur.execute(sql)  # type: ignore
        if rows is None:
            return create_response([])

        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": sql_generator.__name__,
            "sql": sql,
            "columns": [
<<<<<<< Updated upstream
                {"name": col[0], "type": col[1].__name__ if hasattr(col[1], "__name__") else str(col[1])}
=======
                {"name": col[0], "type": col[1].__name__ if hasattr(
                    col[1], '__name__') else str(col[1])}
>>>>>>> Stashed changes
                for col in cur.description
            ]
            if cur.description
            else [],
            "row_count": len(data),
        }
        logger.debug(f"Tool: util_base_dynamicQuery: metadata: {metadata}")
        return create_response(data, metadata)


<<<<<<< Updated upstream
# ------------------ Tool  ------------------#
# Extract and save DDL tool
def handle_base_saveDDL(
    conn: TeradataConnection,
    database_name: str,
    object_name: str,
    object_type: str = "PROCEDURE",
    output_dir: str = "./ddls_extracted",
=======
# ============================================================================
#
# base_columnMetadata - Teradata MCP Server Tool
# ================================================
# Retrieves detailed column metadata for Teradata objects including
# data types, character sets, case specificity, and format strings.
#
# REFACTORED (v1.1.0): All functions now use TeradataConnection with
# the native conn.cursor() pattern and positional ? bind parameters,
# matching every other tool in this module. The previous version used
# SQLAlchemy Connection with text() and :named parameters, which was
# incompatible with the TeradataConnection injected by the MCP server
# framework - causing the tool to hang until the 4-minute MCP timeout.
#
# Author:  Paul Dancer
# Version: 1.4.2 - Fixed Primary? flag (P/S not Y/N)
#
# ============================================================================

# ---------------------------------------------------------------------------
# Constants: Teradata type-code to human-readable type mappings
# Rule 40: "Always use defined and descriptively named constants"
# ---------------------------------------------------------------------------

# Character set identifiers used by HELP COLUMN CharType field
CHARSET_MAP = {
    1: "LATIN",
    2: "UNICODE",
    3: "KANJI1",
    4: "GRAPHIC",
    5: "KANJISJIS",
}

# Teradata internal type codes to SQL type names
# Reference: DBC.Columns ColumnType / HELP COLUMN Type field
TYPE_CODE_MAP = {
    # -- Character types --
    "CF": "CHAR",
    "CV": "VARCHAR",
    "CO": "VARCHAR",          # VARCHAR variant returned by some HELP COLUMN versions
    "LF": "LONG VARCHAR",
    "BF": "BYTE",
    "BV": "VARBYTE",
    "BO": "BLOB",
    # -- Numeric types --
    "I1": "BYTEINT",
    "I2": "SMALLINT",
    "I":  "INTEGER",
    "I8": "BIGINT",
    "F":  "FLOAT",
    "D":  "DOUBLE PRECISION",
    "DC": "DECIMAL",
    "N":  "NUMBER",
    # -- Date/Time types --
    "DA": "DATE",
    "AT": "TIME",
    "TS": "TIMESTAMP",
    "TZ": "TIME WITH TIME ZONE",
    "SZ": "TIMESTAMP WITH TIME ZONE",
    # -- Interval types --
    "YR": "INTERVAL YEAR",
    "YM": "INTERVAL YEAR TO MONTH",
    "MO": "INTERVAL MONTH",
    "DY": "INTERVAL DAY",
    "DH": "INTERVAL DAY TO HOUR",
    "DM": "INTERVAL DAY TO MINUTE",
    "DS": "INTERVAL DAY TO SECOND",
    "HR": "INTERVAL HOUR",
    "HM": "INTERVAL HOUR TO MINUTE",
    "HS": "INTERVAL HOUR TO SECOND",
    "MI": "INTERVAL MINUTE",
    "MS": "INTERVAL MINUTE TO SECOND",
    "SC": "INTERVAL SECOND",
    # -- Period types --
    "PD": "PERIOD(DATE)",
    "PT": "PERIOD(TIME)",
    "PS": "PERIOD(TIMESTAMP)",
    "PM": "PERIOD(TIME WITH TIME ZONE)",
    "PZ": "PERIOD(TIMESTAMP WITH TIME ZONE)",
    # -- Complex/Structured types --
    "A1": "ARRAY",
    "AN": "ARRAY",
    "JN": "JSON",
    "XM": "XML",
    "UT": "UDT",
    # -- LOB types --
    "CL": "CLOB",
}

# Types that include precision/scale in their definition
DECIMAL_TYPES = {"DC", "N"}

# Types that include length and optional charset in their definition
CHARACTER_TYPES = {"CF", "CV", "CO", "LF"}

# Module-level constant for tracing
C_MODULE = "base_columnMetadata"


# ============================================================================
# Tool: base_columnMetadata
# ============================================================================
def handle_base_columnMetadata(
    conn: TeradataConnection,
    db_name: str,
    object_name: Optional[str] = None,
    table_kind: Optional[str] = None,
    max_workers: Optional[int] = None,
    fields: Optional[str] = None,
    exclude_objects: Optional[str] = None,
    max_payload_kb: Optional[int] = None,
    max_execution_seconds: Optional[int] = None,
>>>>>>> Stashed changes
    *args,
    **kwargs,
):
    """
<<<<<<< Updated upstream
    Extracts the complete DDL of a Teradata object and saves it to a .sql file.

    This tool solves the token limit problem by executing the extraction and file save
    operation directly on the server side, without needing to pass large DDL content
    through the response.

    Arguments:
      database_name - Database name (e.g., 'MKTG_USR')
      object_name - Object name (e.g., 'SP_LOAD_VARIABLES_ARGUMENTARIO_IAG_FICHA_CLIENTE')
      object_type - Type of object: 'PROCEDURE', 'TABLE', 'VIEW' (default: 'PROCEDURE')
      output_dir - Directory where to save the DDL file (default: './ddls_extracted')

    Returns:
      ResponseType: formatted response with file path, size, and metadata
    """
    import os
    from datetime import datetime
    from pathlib import Path

    logger.debug(
        f"Tool: handle_base_saveDDL: Args: database_name={database_name}, "
        f"object_name={object_name}, object_type={object_type}, output_dir={output_dir}"
    )

    # Validate object type
    valid_types = ["PROCEDURE", "TABLE", "VIEW", "MACRO", "FUNCTION"]
    object_type_upper = object_type.upper()
    if object_type_upper not in valid_types:
        error_msg = f"Invalid object_type '{object_type}'. Must be one of: {', '.join(valid_types)}"
        logger.error(error_msg)
        return create_response([{"error": error_msg}], {"tool_name": "base_saveDDL", "status": "error"})

    # Build the SHOW command
    show_commands = {
        "PROCEDURE": f"SHOW PROCEDURE {database_name}.{object_name}",
        "TABLE": f"SHOW TABLE {database_name}.{object_name}",
        "VIEW": f"SHOW VIEW {database_name}.{object_name}",
        "MACRO": f"SHOW MACRO {database_name}.{object_name}",
        "FUNCTION": f"SHOW FUNCTION {database_name}.{object_name}",
    }

    sql = show_commands[object_type_upper]
    logger.info(f"Executing: {sql}")

    try:
        # Execute the SHOW command
        with conn.cursor() as cur:
            rows = cur.execute(sql)
            raw_rows = rows.fetchall()

            if not raw_rows:
                error_msg = f"No DDL found for {object_type} {database_name}.{object_name}"
                logger.warning(error_msg)
                return create_response([{"error": error_msg}], {"tool_name": "base_saveDDL", "status": "not_found"})

            # Concatenate all rows to get complete DDL
            ddl_parts = [row[0] for row in raw_rows if row and row[0]]
            ddl_raw = "".join(ddl_parts)

            # Format DDL: Replace \r with newlines and \t with spaces
            # This fixes the single-line output issue
            ddl_complete = ddl_raw.replace("\r", "\n").replace("\t", "    ")

            ddl_size = len(ddl_complete)

            logger.info(f"DDL extracted: {ddl_size} chars from {len(raw_rows)} rows (formatted)")

            # Create output directory if it doesn't exist
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{object_name}_DDL.sql"
            filepath = output_path / filename

            # Prepare file header with metadata
            header = f"""/*
 * File: {filename}
 * Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
 * Type: {object_type_upper}
 * Database: {database_name}
 * Object: {object_name}
 * Size: {ddl_size} characters
 */

"""

            # Write DDL to file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(header)
                f.write(ddl_complete)

            file_size_bytes = filepath.stat().st_size

            logger.info(f"DDL saved successfully to: {filepath} ({file_size_bytes} bytes)")

            # Return success response
            data = [
                {
                    "status": "success",
                    "filepath": str(filepath.absolute()),
                    "filename": filename,
                    "ddl_size_chars": ddl_size,
                    "file_size_bytes": file_size_bytes,
                    "rows_concatenated": len(raw_rows),
                    "object_type": object_type_upper,
                    "database": database_name,
                    "object": object_name,
                }
            ]

            metadata = {
                "tool_name": "base_saveDDL",
                "sql": sql,
                "output_dir": str(output_path.absolute()),
                "timestamp": timestamp,
                "success": True,
            }

            return create_response(data, metadata)

    except Exception as e:
        error_msg = f"Error extracting/saving DDL: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return create_response(
            [{"error": error_msg, "exception_type": type(e).__name__}],
            {"tool_name": "base_saveDDL", "status": "error", "sql": sql},
        )
=======
    Retrieves detailed column metadata for Teradata tables, views, and
    functions using HELP COLUMN. Returns data types, character sets, case
    specificity, precision, scale, and format strings for each column.

    Uses the native TeradataConnection cursor pattern, consistent with all
    other tools in this module.

    Use this tool instead of base_columnDescription when you need:
    - Exact Teradata type codes and their SQL type string equivalents
    - Character set information (LATIN, UNICODE, etc.)
    - Decimal precision and scale
    - Detection of broken/invalid views
    - Column-level metadata for all objects in a database at once

    LARGE-SCALE USAGE GUIDANCE:
    ---------------------------
    When retrieving metadata for many objects (e.g. all views in DBC),
    both the response payload and the execution time can exceed limits.
    Use these strategies to control both:

    1. FILTER FIELDS: Pass only the columns you need via the ``fields``
       parameter. Each HELP COLUMN row returns ~49 fields by default;
       trimming to 6-8 fields can reduce payload by 80%+.
       Three computed fields (ColumnTypeString, IndexTypeString,
       CharSetString) are always included automatically.
       Example: fields='ColumnName,ColumnType,ColumnLength,CharType,
                        UpperCase,Nullable,Indexed?,Primary?,Unique?'

    2. EXCLUDE OBJECTS: Use ``exclude_objects`` to skip objects you do
       not need. Accepts SQL LIKE patterns (% wildcard) as a CSV.
       Applied BEFORE any HELP COLUMN execution, so excluded objects
       consume zero time and zero payload.
       Example: exclude_objects='ResUsage%,%ResUsage%,Res%View'

    3. INCREASE PARALLELISM: Set ``max_workers`` to 12-16 for large
       databases. Each worker gets its own Teradata session via
       conn.cursor(). Default is 8.

    4. FILTER BY KIND: Use ``table_kind`` to limit to just the object
       types you need (e.g. 'V' for views only, 'T' for tables only).

    5. PAYLOAD BUDGET: Use ``max_payload_kb`` (default 900) to set the
       maximum response payload size in kilobytes. When the accumulated
       result data approaches this limit, the tool stops collecting and
       returns what it has, plus a ``remaining_objects`` CSV in metadata
       listing the unprocessed objects. Pass that CSV straight into
       ``object_name`` on the next call for automatic continuation.
       This self-adapts to object sizes: small-column views fit more
       per call, large-column views page earlier.

    6. TIME BUDGET: Use ``max_execution_seconds`` (default 180) to set
       the maximum wall-clock execution time. The tool monitors elapsed
       time as each object completes, and self-interrupts BEFORE the
       MCP transport timeout (typically 240s) kills the session without
       returning any data. When the time budget is reached, the tool
       returns all data collected so far plus ``remaining_objects`` for
       continuation — exactly the same pattern as payload budget.
       This is the key difference from an MCP timeout: a timeout
       returns NOTHING; a time budget returns EVERYTHING collected so
       far, plus a continuation token.

    CONTINUATION PATTERN (automatic pagination):
        # Call 1 — starts processing, time or payload budget fills up
        result1 = base_columnMetadata(db_name='DBC', table_kind='V', ...)
        # metadata contains: remaining_objects='ViewX,ViewY,...'

        # Call 2 — pass remaining_objects as object_name
        result2 = base_columnMetadata(
            db_name='DBC',
            object_name='ViewX,ViewY,...',  # from result1 metadata
            ...
        )
        # Repeat until metadata has no remaining_objects key.

    Typical call for a large database:
        base_columnMetadata(
            db_name='DBC',
            table_kind='V',
            exclude_objects='ResUsage%,%ResUsage%',
            fields='ColumnName,ColumnType,ColumnLength,CharType,
                    UpperCase,Nullable,Indexed?,Primary?,Unique?',
            max_workers=16,
            max_payload_kb=900,
            max_execution_seconds=180
        )

    Arguments:
        conn                 - TeradataConnection (injected by MCP server)
        db_name              - Name of the Teradata database to inspect
        object_name          - Optional: specific object name, or a CSV of
                               names.
                               Single: 'ColumnsV'
                               CSV:    'AllRights,AllSpace,ColumnsV'
                               Also used for continuation: pass the
                               ``remaining_objects`` value from a previous
                               truncated call to resume from where it left
                               off.
                               If omitted, all objects matching table_kind
                               are processed.
        table_kind           - Optional: CSV of TableKind codes to filter by.
                               Examples: 'V' (views only), 'T,O' (tables +
                               NoPI), 'T,V' (tables and views). If omitted,
                               all qualifying object types (T, O, V, F) are
                               processed.
        max_workers          - Optional: number of parallel threads for HELP
                               COLUMN execution. Each thread uses its own
                               Teradata cursor (session). Default: 8. Set to
                               1 for sequential mode.
        fields               - Optional: CSV of field names to include in the
                               response. Dramatically reduces payload size by
                               stripping unused HELP COLUMN fields. Four
                               computed fields (ObjectName, ColumnTypeString,
                               IndexTypeString, CharSetString) plus status
                               fields are always included automatically.
                               Example: 'ColumnName,ColumnType,ColumnLength,
                                         CharType,UpperCase,Nullable,
                                         Indexed?,Primary?,Unique?'
                               If omitted, all fields are returned (~49 per
                               column plus the 3 computed fields).
        exclude_objects      - Optional: CSV of object name patterns to
                               exclude. Uses SQL LIKE-style wildcards (% for
                               any characters). Patterns are matched case-
                               insensitively against each object name BEFORE
                               HELP COLUMN is executed, so excluded objects
                               incur no query cost.
                               Example: 'ResUsage%,%ResUsage%' excludes all
                               ResUsage views from DBC.
                               Default: None (no exclusions).
        max_payload_kb       - Optional: maximum response payload budget in
                               KB. When accumulated result data reaches this
                               limit, the tool stops collecting and returns
                               what it has, plus ``remaining_objects`` in
                               metadata for continuation. Default: 900
                               (safely under the 1 MB MCP transport limit).
                               Set to 0 to disable payload budget enforcement
                               (not recommended for large databases).
        max_execution_seconds - Optional: maximum wall-clock execution time
                               in seconds. The timer starts when the function
                               is entered and is checked after each object
                               completes. When the elapsed time exceeds this
                               limit, the tool stops collecting, cancels
                               pending futures, and returns all data collected
                               so far plus ``remaining_objects`` for
                               continuation. Default: 180 (3 minutes — safely
                               under the typical 240s MCP transport timeout,
                               leaving headroom for serialisation and
                               transport). Set to 0 to disable time budget
                               enforcement (not recommended).
        *args                - Positional bind parameters (reserved)
        **kwargs             - Named bind parameters (reserved)

    Returns:
        MCP-compliant response via create_response() containing a list
        of column metadata records with normalised keys and three
        computed string fields per column:

            ColumnTypeString - Human-readable SQL type (e.g. "VARCHAR(200)
                               UNICODE", "DECIMAL(18,2)", "INTEGER")
            IndexTypeString  - Index classification: 'UPI', 'NUPI', 'USI',
                               'NUSI', or None if the column is not
                               indexed. Derived from Indexed?, Primary?,
                               Unique? flags.
                               NOTE: HELP COLUMN only reports that a
                               column participates in an index, not which
                               columns are grouped together in a composite
                               index. For composite index membership, query
                               DBC.IndicesV (IndexNumber + ColumnPosition).
            CharSetString    - Character set name: 'LATIN', 'UNICODE',
                               'KANJI1', 'GRAPHIC', 'KANJISJIS', or None
                               for non-character columns.

        When truncated, metadata will include:
            remaining_objects  - CSV of unprocessed object names (pass
                                 as object_name to continue)
            truncated          - True
            truncation_reason  - 'time_budget_exceeded' or
                                 'payload_budget_exceeded'
            elapsed_seconds    - Wall-clock time consumed (always present)
    """

    method_name = inspect.currentframe().f_code.co_name
    logger = logging.getLogger(method_name)
    v_step_no = "000"

    # Start the wall-clock timer — used for time budget enforcement.
    # Uses monotonic clock to be immune to system clock adjustments.
    t_start = time.monotonic()

    try:
        # ------------------------------------------------------------------
        # Step 010: Resolve target objects
        # ------------------------------------------------------------------
        v_step_no = "010"
        logger.debug(
            f"{C_MODULE}:{v_step_no} Resolving objects for db_name={db_name}, "
            f"object_name={object_name}, exclude_objects={exclude_objects}")

        if object_name:
            # Support CSV of object names for batch processing
            # e.g. "AllRights,AllSpace,ColumnsV" processes all three
            names = [n.strip() for n in object_name.split(",") if n.strip()]
            obj_infos = []
            for name in names:
                kind = _get_table_kind(conn, db_name, name)
                if kind:
                    obj_infos.append({"ObjectName": name, "TableKind": kind})
                else:
                    logger.warning(
                        f"{C_MODULE}:{v_step_no} Object '{name}' not found "
                        f"in database '{db_name}' — skipping"
                    )
            if not obj_infos:
                raise ValueError(
                    f"None of the specified objects found in '{db_name}'"
                )
        else:
            # Retrieve all qualifying objects in the database
            obj_infos = _get_objects(conn, db_name, table_kind=table_kind)

        logger.debug(
            f"{C_MODULE}:{v_step_no} Found {len(obj_infos)} object(s) to process")

        # ------------------------------------------------------------------
        # Step 015: Apply exclude_objects filter
        # ------------------------------------------------------------------
        # Removes objects matching any exclusion pattern BEFORE HELP COLUMN
        # is executed, so excluded objects incur zero query cost and zero
        # payload. Patterns use SQL LIKE-style % wildcards, converted to
        # fnmatch * wildcards for matching.
        v_step_no = "015"
        if exclude_objects:
            # Parse CSV of exclusion patterns, convert SQL % → fnmatch *
            patterns = [
                p.strip().replace("%", "*")
                for p in exclude_objects.split(",")
                if p.strip()
            ]
            pre_count = len(obj_infos)
            obj_infos = [
                info for info in obj_infos
                if not any(
                    fnmatch.fnmatch(info["ObjectName"].upper(), pat.upper())
                    for pat in patterns
                )
            ]
            excluded_count = pre_count - len(obj_infos)
            logger.debug(
                f"{C_MODULE}:{v_step_no} Excluded {excluded_count} object(s) "
                f"matching patterns: {exclude_objects}  "
                f"({len(obj_infos)} remaining)"
            )

        # ------------------------------------------------------------------
        # Step 020: Collect column metadata (parallel, budget-aware)
        # ------------------------------------------------------------------
        v_step_no = "020"
        data = []
        workers = max_workers if max_workers and max_workers > 0 else 8

        # Pre-compute field filter set — applied per-object during
        # collection so the budget check measures the ACTUAL payload
        # that will be returned, not the unfiltered version.
        keep = None
        if fields:
            keep = {f.strip() for f in fields.split(",") if f.strip()}
            # Always include ObjectName, computed string fields, and status
            keep.update({"ObjectName", "ColumnTypeString",
                         "IndexTypeString", "CharSetString",
                         "status", "error_message"})

        # Payload budget — default 900 KB (safely under 1 MB MCP limit).
        # Set to 0 or None to disable (not recommended for large dbs).
        budget_bytes = (
            (max_payload_kb if max_payload_kb and max_payload_kb > 0 else 900)
            * 1024
        )
        budget_enabled = (max_payload_kb is None or max_payload_kb != 0)
        accumulated_bytes = 0
        processed_objects = set()
        budget_exceeded = False

        # Time budget — default 180s (safely under the typical 240s MCP
        # transport timeout). Leaves headroom for object resolution,
        # exclusion filtering, metadata serialisation, and transport.
        # Set to 0 to disable (not recommended — risks MCP timeout).
        time_limit = (
            max_execution_seconds
            if max_execution_seconds is not None and max_execution_seconds > 0
            else 180
        )
        time_budget_enabled = (
            max_execution_seconds is None or max_execution_seconds != 0
        )
        time_exceeded = False
        truncation_reason = None

        def _process_one(obj_info: dict) -> list:
            """Worker function: process a single object, return column rows."""
            obj = obj_info["ObjectName"]
            kind = obj_info["TableKind"]
            results = []
            try:
                if kind == "V":
                    cols = _help_column_view(conn, db_name, obj, logger)
                else:
                    cols = _help_column_table(conn, db_name, obj)

                for col in cols:
                    if col.get("status") == "BROKEN_VIEW":
                        results.append(col)
                        continue
                    col["ColumnTypeString"] = _build_type_string(col)
                    col["IndexTypeString"] = _build_index_type_string(col)
                    col["CharSetString"] = _build_charset_string(col)
                    col["ObjectName"] = obj
                    results.append(col)

            except Exception as obj_ex:
                logger.warning(
                    f"{C_MODULE}:{v_step_no} Skipping {db_name}.\"{obj}\" "
                    f"(TableKind={kind}): {obj_ex}"
                )
                results.append({
                    "ObjectName": obj,
                    "status": "ERROR",
                    "error_message": str(obj_ex),
                })
            return results

        # Execute in parallel — each thread gets its own Teradata cursor
        # (session) via conn.cursor() inside the helper functions
        logger.debug(
            f"{C_MODULE}:{v_step_no} Processing {len(obj_infos)} object(s) "
            f"with {workers} parallel workers  "
            f"(payload_budget={budget_bytes // 1024} KB, "
            f"time_budget={time_limit}s)")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_process_one, info): info["ObjectName"]
                for info in obj_infos
            }
            for future in as_completed(futures):
                obj_name_key = futures[future]
                try:
                    result_rows = future.result()

                    # Apply field filtering immediately so the budget
                    # check measures the actual final payload size
                    if keep:
                        result_rows = [
                            {k: v for k, v in rec.items() if k in keep}
                            for rec in result_rows
                        ]

                    # Estimate payload contribution of this chunk
                    chunk_size = len(str(result_rows))

                    # --- TIME BUDGET CHECK (checked first) ---
                    # If elapsed time exceeds the limit, accept this
                    # chunk (it's already done) but stop after it.
                    elapsed = time.monotonic() - t_start
                    if time_budget_enabled and elapsed >= time_limit:
                        # Accept the current chunk before stopping —
                        # the work is already done, no point wasting it
                        data.extend(result_rows)
                        accumulated_bytes += chunk_size
                        processed_objects.add(obj_name_key)
                        time_exceeded = True
                        truncation_reason = "time_budget_exceeded"
                        logger.info(
                            f"{C_MODULE}:{v_step_no} Time budget "
                            f"({time_limit}s) exceeded after "
                            f"{elapsed:.1f}s. Collected "
                            f"{len(processed_objects)} object(s). "
                            f"Stopping collection."
                        )
                        # Cancel futures that haven't started yet
                        for f in futures:
                            f.cancel()
                        break

                    # --- PAYLOAD BUDGET CHECK ---
                    if budget_enabled and accumulated_bytes + chunk_size > budget_bytes:
                        budget_exceeded = True
                        truncation_reason = "payload_budget_exceeded"
                        logger.info(
                            f"{C_MODULE}:{v_step_no} Payload budget "
                            f"({budget_bytes // 1024} KB) would be exceeded "
                            f"by '{obj_name_key}' (+{chunk_size // 1024} KB). "
                            f"Stopping collection."
                        )
                        # Cancel futures that haven't started yet
                        for f in futures:
                            f.cancel()
                        break

                    data.extend(result_rows)
                    accumulated_bytes += chunk_size
                    processed_objects.add(obj_name_key)

                except Exception as ex:
                    logger.error(
                        f"{C_MODULE}:{v_step_no} Future failed for "
                        f"{obj_name_key}: {ex}"
                    )
                    data.append({
                        "ObjectName": obj_name_key,
                        "status": "ERROR",
                        "error_message": str(ex),
                    })
                    processed_objects.add(obj_name_key)

        # ------------------------------------------------------------------
        # Step 030: Build metadata and return
        # ------------------------------------------------------------------
        # NOTE: Field filtering was already applied per-chunk during
        # collection (step 020) so the budget check was accurate.
        # No need to re-filter here.
        v_step_no = "030"

        elapsed_total = time.monotonic() - t_start

        logger.debug(
            f"{C_MODULE}:{v_step_no} Returning {len(data)} column record(s) "
            f"from {len(processed_objects)} object(s)  "
            f"(payload ~{accumulated_bytes // 1024} KB, "
            f"elapsed {elapsed_total:.1f}s)")

        metadata = {
            "tool_name": C_MODULE,
            "database": db_name,
            "object_count": len(processed_objects),
            "column_count": len(data),
            "payload_kb": accumulated_bytes // 1024,
            "elapsed_seconds": round(elapsed_total, 1),
        }
        if object_name:
            metadata["object_name"] = object_name
        if exclude_objects:
            metadata["exclude_objects"] = exclude_objects

        # Continuation support — list unprocessed objects so the caller
        # can pass them straight into object_name on the next call.
        # Triggered by whichever budget (time or payload) was hit first.
        truncated = time_exceeded or budget_exceeded
        if truncated:
            remaining = [
                info["ObjectName"]
                for info in obj_infos
                if info["ObjectName"] not in processed_objects
            ]
            metadata["truncated"] = True
            metadata["truncation_reason"] = truncation_reason
            metadata["remaining_objects"] = ",".join(remaining)
            metadata["remaining_count"] = len(remaining)
            logger.info(
                f"{C_MODULE}:{v_step_no} Truncated ({truncation_reason}): "
                f"{len(remaining)} object(s) remaining for continuation  "
                f"(elapsed {elapsed_total:.1f}s, "
                f"payload {accumulated_bytes // 1024} KB)"
            )

        return create_response(data, metadata)
        
    except Exception as e:
        logger.error(f"{C_MODULE}:{v_step_no} Error: {e}")
        return create_response(
            [{"error": str(e)}],
            {"tool_name": C_MODULE, "database": db_name},
        )


# ===========================================================================
# Private helper functions for base_columnMetadata
# ===========================================================================


def _standardise_helpcol_row(row: dict) -> dict:
    """
    Normalise HELP COLUMN output keys to consistent PascalCase names.

    HELP COLUMN returns different column names depending on the target:
      - Named tables:   full names like "Column Name", "Type", "Format"
      - Derived tables:  may return abbreviated single-letter headers
                         (e.g. "C", "T", "F") - especially for DBC
                         system views accessed via the dt-wrapper technique.

    This function maps all known variants (full, spaced, and abbreviated)
    to a single canonical set of PascalCase keys so that downstream
    functions like ``_build_type_string`` work regardless of the HELP
    COLUMN flavour.

    Args:
        row: A single row dict from rows_to_json(HELP COLUMN results).

    Returns:
        dict: Row with normalised key names.  String values are stripped;
              None values are preserved as-is.
    """
    mapping = {
        # --- Full / spaced forms (named-table HELP COLUMN) ---
        "Column Name": "ColumnName",
        "Type": "ColumnType",
        "Comment": "Comment",
        "Nullable": "Nullable",
        "Format": "Format",
        "Title": "Title",
        "Max Length": "ColumnLength",
        "Length": "ColumnLength",
        "Decimal Total Digits": "DecimalTotalDigits",
        "Decimal Fractional Digits": "DecimalFractionalDigits",
        "Char Type": "CharType",
        "CharType": "CharType",
        "Upper Case": "UpperCase",
        "Case Specific": "CaseSpecific",
        "Not Casespecific Not Padded": "NCSNP",
        "Default Value": "DefaultValue",
        "Range": "Range",
        # --- Abbreviated single-letter forms (derived-table wrapper) ---
        # Mapping verified against Teradata HELP COLUMN dt.* output.
        # NOTE: If your Teradata version returns different abbreviations,
        #       extend this mapping accordingly.
        "C": "ColumnName",
        "T": "ColumnType",
        "N": "Nullable",
        "F": "Format",
        "M": "ColumnLength",
        "D": "DecimalTotalDigits",
        "R": "DecimalFractionalDigits",
        "U": "UpperCase",
        "I": "IdentityCol",
        "P": "PermitNull",
        "S": "CharType",
        "W": "ColumnWidth",
        "A": "Attributes",
    }

    normalised = {}
    for key, value in row.items():
        canonical_key = mapping.get(key, key.replace(" ", ""))
        # Preserve None as None; only strip genuine strings
        if isinstance(value, str):
            normalised[canonical_key] = value.strip()
        else:
            normalised[canonical_key] = value
    return normalised


def _safe_int(value) -> Optional[int]:
    """
    Safely convert a value to int, returning None on failure.

    HELP COLUMN sometimes returns numeric fields as padded strings
    or None. This avoids scattered try/except blocks throughout
    the type-string builder.

    Args:
        value: The value to convert (str, int, or None).

    Returns:
        int or None.
    """
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def _infer_type_from_format(fmt: str, max_length: int | None) -> str:
    """
    Infer a Teradata SQL type string from the Format and MaxLength
    fields when the ColumnType code is NULL.

    This commonly occurs with DBC system views accessed via the
    derived-table HELP COLUMN wrapper, where Teradata populates
    the Format and MaxLength but leaves the Type code empty.

    Inference rules (in order):
      - ``X(n)``                  -> CHARACTER type; use MaxLength
                                    to distinguish LATIN vs UNICODE
      - ``9`` / ``-`` / ``,``     -> Numeric; use MaxLength to pick
                                    BYTEINT / SMALLINT / INTEGER / BIGINT
      - ``YYYY-MM-DD``            -> DATE
      - ``YYYY-MM-DDBHH:MI:SS``  -> TIMESTAMP(0)
      - ``HH:MI:SS``             -> TIME

    Args:
        fmt:        The Format string from HELP COLUMN (already stripped).
        max_length: The MaxLength value (bytes), or None.

    Returns:
        str: Best-effort SQL type string, or the raw format if no
             rule matched.
    """
    if not fmt:
        return "UNKNOWN"

    import re as _re

    # -- Character format: X(n) --
    char_match = _re.match(r"^X\((\d+)\)$", fmt, _re.IGNORECASE)
    if char_match:
        char_len = int(char_match.group(1))
        # If MaxLength is double the char length -> UNICODE; else LATIN
        if max_length is not None and max_length == char_len * 2:
            return f"VARCHAR({char_len}) UNICODE"
        if max_length is not None and max_length == char_len:
            return f"VARCHAR({char_len}) LATIN"
        return f"VARCHAR({char_len})"

    # -- Timestamp format --
    if "YYYY" in fmt.upper() and ("HH" in fmt.upper() or "MI" in fmt.upper()):
        return "TIMESTAMP(0)"

    # -- Date format --
    if "YYYY" in fmt.upper() and "MM" in fmt.upper() and "DD" in fmt.upper():
        return "DATE"

    # -- Time format --
    if _re.match(r"^HH:MI", fmt, _re.IGNORECASE):
        return "TIME"

    # -- Numeric format (contains 9s, dashes, commas) --
    if _re.match(r"^[-,9(). ]+$", fmt):
        size_map = {1: "BYTEINT", 2: "SMALLINT", 4: "INTEGER", 8: "BIGINT"}
        if max_length in size_map:
            return size_map[max_length]
        return "INTEGER"

    return fmt


def _build_type_string(col: dict) -> str:
    """
    Construct a human-readable Teradata SQL type string from a
    normalised HELP COLUMN row.

    When the ColumnType code is populated, this function uses
    the standard type-code lookup (CHARACTER_TYPES, DECIMAL_TYPES,
    TYPE_CODE_MAP).  When it is NULL - as commonly happens with
    DBC system views - the function falls back to
    :func:`_infer_type_from_format` which derives the type from
    the Format string and MaxLength.

    Examples:
        CHAR(10) LATIN, VARCHAR(200) UNICODE, DECIMAL(18,2),
        INTEGER, DATE, TIMESTAMP, PERIOD(DATE)

    Args:
        col: A normalised column metadata dict from _standardise_helpcol_row.

    Returns:
        str: The Teradata SQL type string (e.g. "VARCHAR(200) UNICODE").
    """
    type_code = (col.get("ColumnType") or col.get("Type") or "").strip()
    fmt = (col.get("Format") or "").strip()
    max_length = _safe_int(col.get("ColumnLength") or col.get(
        "MaxLength") or col.get("Length"))

    # -- Character types: include length and charset --
    if type_code in CHARACTER_TYPES:
        char_type = _safe_int(col.get("CharType"))
        base_name = TYPE_CODE_MAP.get(type_code, type_code)
        length_part = f"({max_length})" if max_length is not None else ""
        charset_part = f" {CHARSET_MAP[char_type]}" if char_type in CHARSET_MAP else ""
        return f"{base_name}{length_part}{charset_part}"

    # -- Decimal/Number types: include precision and scale --
    if type_code in DECIMAL_TYPES:
        dec_tot = _safe_int(
            col.get("DecimalTotalDigits") or col.get("Decimal Total Digits")
        )
        dec_frac = _safe_int(
            col.get("DecimalFractionalDigits") or col.get(
                "Decimal Fractional Digits")
        )
        base_name = TYPE_CODE_MAP.get(type_code, type_code)
        if dec_tot is not None and dec_frac is not None:
            return f"{base_name}({dec_tot},{dec_frac})"
        return base_name

    # -- All other known types: straight lookup --
    if type_code in TYPE_CODE_MAP:
        return TYPE_CODE_MAP[type_code]

    # -- Type code is empty/NULL: infer from Format + MaxLength --
    if not type_code and fmt:
        return _infer_type_from_format(fmt, max_length)

    # -- Final fallback --
    return type_code or fmt or "UNKNOWN"


def _build_index_type_string(col: dict) -> Optional[str]:
    """
    Derive a human-readable Teradata index type from HELP COLUMN flags.

    Combines the three HELP COLUMN index flags (Indexed?, Primary?,
    Unique?) into one of four standard Teradata index type labels:

        UPI  — Unique Primary Index
        NUPI — Non-Unique Primary Index
        USI  — Unique Secondary Index
        NUSI — Non-Unique Secondary Index

    Returns None if the column does not participate in any index.

    HELP COLUMN flag values:
        Indexed?  - 'Y' = participates in an index, 'N' = no index
        Primary?  - 'P' = Primary index, 'S' = Secondary index,
                    None = not indexed
        Unique?   - 'Y' = unique, 'N' = non-unique, None = not indexed

    IMPORTANT CAVEAT: HELP COLUMN only reports that a column
    *participates* in an index, not which columns are grouped together
    in a composite (multi-column) index. For composite index membership
    and column ordering, query DBC.IndicesV which provides IndexNumber
    grouping and ColumnPosition.

    Args:
        col: A normalised column metadata dict from _standardise_helpcol_row.

    Returns:
        str or None: 'UPI', 'NUPI', 'USI', 'NUSI', or None if not indexed.
    """
    indexed = str(col.get("Indexed?") or "").strip().upper()
    if indexed != "Y":
        return None

    primary = str(col.get("Primary?") or "").strip().upper()
    unique = str(col.get("Unique?") or "").strip().upper()

    if primary == "P":
        return "UPI" if unique == "Y" else "NUPI"
    else:
        return "USI" if unique == "Y" else "NUSI"


def _build_charset_string(col: dict) -> Optional[str]:
    """
    Derive a human-readable character set name from the HELP COLUMN
    CharType code.

    Translates the numeric CharType code into a standard Teradata
    character set name (LATIN, UNICODE, etc.). Returns None for
    non-character columns where CharType is not applicable.

    Args:
        col: A normalised column metadata dict from _standardise_helpcol_row.

    Returns:
        str or None: 'LATIN', 'UNICODE', 'KANJI1', 'GRAPHIC',
                     'KANJISJIS', or None if not a character column.
    """
    char_type = _safe_int(col.get("CharType"))
    if char_type is None:
        return None
    return CHARSET_MAP.get(char_type)


def _get_objects(conn: TeradataConnection, db_name: str,
                 table_kind: Optional[str] = None) -> list:
    """
    Retrieve all qualifying objects (tables, views, functions) from a database.

    Queries DBC.TablesV filtered by TableKind. When table_kind is provided,
    only those specific kinds are returned; otherwise defaults to
    ('T','O','V','F') covering tables, NoPI tables, views, and functions.

    Uses the native TeradataConnection cursor with positional ? parameters.

    Args:
        conn:       TeradataConnection (injected by MCP server).
        db_name:    Target database name.
        table_kind: Optional CSV of TableKind codes, e.g. 'V' or 'T,V'.
                    Defaults to 'T,O,V,F' if not provided.

    Returns:
        list[dict]: Each dict contains DatabaseName, ObjectName, TableKind.
    """
    # Parse table_kind CSV into a list, defaulting to all standard types
    if table_kind:
        kinds = [k.strip().upper() for k in table_kind.split(",") if k.strip()]
    else:
        kinds = ["T", "O", "V", "F"]

    # Build parameterised IN clause
    placeholders = ",".join(["?"] * len(kinds))
    sql = f"""
        SELECT
            tv.DatabaseName  AS DatabaseName,
            tv.TableName     AS ObjectName,
            tv.TableKind     AS TableKind
        FROM DBC.TablesV AS tv
        WHERE tv.DatabaseName = ?
          AND tv.TableKind IN ({placeholders})
        ORDER BY tv.TableName
    """
    with conn.cursor() as cur:
        cur.execute(sql, [db_name] + kinds)
        rows = cur.fetchall()
        return [
            {
                "DatabaseName": row[0],
                "ObjectName": row[1].strip() if isinstance(row[1], str) else row[1],
                "TableKind": row[2].strip() if isinstance(row[2], str) else row[2],
            }
            for row in rows
        ]


def _get_table_kind(conn: TeradataConnection, db_name: str, object_name: str) -> Optional[str]:
    """
    Look up the TableKind for a single object in DBC.TablesV.

    Uses the native TeradataConnection cursor with positional ? parameters.

    Args:
        conn:        TeradataConnection (injected by MCP server).
        db_name:     Target database name.
        object_name: The specific object to look up.

    Returns:
        str or None: The TableKind code, or None if the object does not exist.
    """
    sql = """
        SELECT tv.TableKind
        FROM DBC.TablesV AS tv
        WHERE tv.DatabaseName = ?
          AND tv.TableName = ?
    """
    with conn.cursor() as cur:
        cur.execute(sql, [db_name, object_name])
        row = cur.fetchone()
        return row[0].strip() if row else None


def _help_column_table(conn: TeradataConnection, db_name: str, object_name: str) -> list:
    """
    Execute HELP COLUMN against a table or function and return normalised rows.

    Uses the direct HELP COLUMN syntax which works for tables (T),
    NoPI tables (O), and functions (F).

    Uses the native TeradataConnection cursor (no bind parameters needed
    for HELP COLUMN as the object name is part of the SQL syntax).

    Args:
        conn:        TeradataConnection (injected by MCP server).
        db_name:     Target database name.
        object_name: The table or function name.

    Returns:
        list[dict]: Normalised column metadata rows.
    """
    sql = f'HELP COLUMN "{db_name}"."{object_name}".*'
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        data = rows_to_json(cur.description, rows)
        return [_standardise_helpcol_row(row) for row in data]


def _help_column_view(
    conn: TeradataConnection, db_name: str, object_name: str, logger: logging.Logger
) -> list:
    """
    Execute HELP COLUMN against a view using a derived-table wrapper.

    Views require an indirect approach because HELP COLUMN on a view
    directly returns the view's own column definitions rather than the
    resolved column types. The derived-table technique forces Teradata
    to resolve the view columns first.

    NOTE: The inner SELECT uses a wildcard (SELECT dt01.*) which is
    necessary for HELP COLUMN to enumerate all resolved columns from
    the derived table. This is a documented exception to Rule 39
    (never use SELECT *) because HELP COLUMN requires it in this scenario.

    If the view is broken (references dropped objects, invalid SQL),
    this function catches the exception and returns a BROKEN_VIEW
    status record instead of raising.

    Uses the native TeradataConnection cursor (no bind parameters needed
    for HELP COLUMN as object names are part of the SQL syntax).

    Args:
        conn:        TeradataConnection (injected by MCP server).
        db_name:     Target database name.
        object_name: The view name.
        logger:      Logger instance for error reporting.

    Returns:
        list[dict]: Normalised column metadata rows, or a single
                    BROKEN_VIEW status record on failure.
    """
    # NOTE: Wildcard is required here - HELP COLUMN on a derived table
    # must enumerate all columns. See docstring for Rule 39 exception.
    sql = f"""
        HELP COLUMN dt01.*
        FROM (
            SELECT obj.*
            FROM "{db_name}"."{object_name}" AS obj
            WHERE 1 = 0
        ) AS dt01
    """

    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            data = rows_to_json(cur.description, rows)
            return [_standardise_helpcol_row(row) for row in data]

    except Exception as ex:
        logger.error(
            f"{C_MODULE}: Broken view detected: {db_name}.{object_name} - {ex}"
        )
        return [
            {
                "ObjectName": object_name,
                "status": "BROKEN_VIEW",
                "error_message": str(ex),
            }
        ]
>>>>>>> Stashed changes
