import logging
import re

from sqlalchemy import text
from sqlalchemy.engine import Connection, default
from teradatasql import TeradataConnection

from teradata_mcp_server.tools.utils import create_response, rows_to_json

logger = logging.getLogger("teradata_mcp_server")

#------------------ Tool  ------------------#
# Read query tool
def handle_base_readQuery(
    conn: Connection,
    sql: str | None = None,
    tool_name: str | None = None,
    *args,
    **kwargs
):
    """
    Execute a SQL query via SQLAlchemy, bind parameters if provided (prepared SQL), and return the fully rendered SQL (with literals) in metadata.

    Arguments:
      sql    - SQL text, with optional bind-parameter placeholders

    Returns:
      ResponseType: formatted response with query results + metadata
    """
    logger.debug(f"Tool: handle_base_readQuery: Args: sql: {sql}, args={args!r}, kwargs={kwargs!r}")

    # 1. Build a textual SQL statement
    stmt = text(sql)

    # 2. Execute with bind parameters if provided
    result = conn.execute(stmt, kwargs) if kwargs else conn.execute(stmt)

    # 3. Fetch rows & column metadata
    cursor = result.cursor  # underlying DB-API cursor
    raw_rows = cursor.fetchall() or []
    data = rows_to_json(cursor.description, raw_rows)
    columns = [
        {
            "name": col[0],
            "type": getattr(col[1], "__name__", str(col[1]))
        }
        for col in (cursor.description or [])
    ]

    # 4. Compile the statement with literal binds for “final SQL”
    #    Fallback to DefaultDialect if conn has no `.dialect`
    dialect = getattr(conn, "dialect", default.DefaultDialect())
    compiled = stmt.compile(
        dialect=dialect,
        compile_kwargs={"literal_binds": True}
    )
    final_sql = str(compiled)

    # 5. Build metadata using the rendered SQL
    metadata = {
        "tool_name": tool_name if tool_name else "base_readQuery",
        "sql": final_sql,
        "columns": columns,
        "row_count": len(data),
    }
    logger.debug(f"Tool: handle_base_readQuery: metadata: {metadata}")
    return create_response(data, metadata)


#------------------ Tool  ------------------#
# List databases tool
def handle_base_databaseList(conn: TeradataConnection, *args, **kwargs):
    """
    Lists all databases in the Teradata System.

    Returns:
      ResponseType: formatted response with query results + metadata
    """
    logger.debug(f"Tool: handle_base_databaseList: Args: None")

    sql = "select DataBaseName, DECODE(DBKind, 'U', 'User', 'D','DataBase') as DBType, CommentString from dbc.DatabasesV dv where OwnerName <> 'PDCRADM'"

    with conn.cursor() as cur:
        rows = cur.execute(sql)
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "base_databaseList",
            "sql": sql,
            "columns": [
                {"name": col[0], "type": col[1].__name__ if hasattr(col[1], '__name__') else str(col[1])}
                for col in cur.description
            ] if cur.description else [],
            "row_count": len(data)
        }
        logger.debug(f"Tool: handle_base_databaseList: metadata: {metadata}")
        return create_response(data, metadata)


#------------------ Tool  ------------------#
# List tables tool
def handle_base_tableList(conn: TeradataConnection, database_name: str | None = None, *args, **kwargs):
    """
    Lists all tables in a database.

    Arguments:
      database_name - Database name

    Returns:
      ResponseType: formatted response with query results + metadata
    """
    logger.debug(f"Tool: handle_base_tableList: Args: database_name: {database_name}")

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
                {"name": col[0], "type": col[1].__name__ if hasattr(col[1], '__name__') else str(col[1])}
                for col in cur.description
            ] if cur.description else [],
            "row_count": len(data)
        }
        logger.debug(f"Tool: handle_base_tableList: metadata: {metadata}")
        return create_response(data, metadata)


#------------------ Tool  ------------------#
# get DDL tool
def handle_base_tableDDL(conn: TeradataConnection, database_name: str | None, table_name: str, *args, **kwargs):
    """
    Displays the DDL definition of a table via SQLAlchemy, bind parameters if provided (prepared SQL), and return the fully rendered SQL (with literals) in metadata.

    Arguments:
      database_name - Database name
      table_name - table name

    Returns:
      ResponseType: formatted response with query results + metadata
    """
    logger.debug(f"Tool: handle_base_tableDDL: Args: database_name: {database_name}, table_name: {table_name}")

    if database_name is not None:
        table_name = f"{database_name}.{table_name}"
    with conn.cursor() as cur:
        rows = cur.execute(f"show table {table_name}")
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "base_tableDDL",
            "database": database_name,
            "table": table_name,
            "rows": len(data)
        }
        logger.debug(f"Tool: handle_base_tableDDL: metadata: {metadata}")
        return create_response(data, metadata)

#------------------ Tool  ------------------#
# Read column description tool
def handle_base_columnDescription(conn: TeradataConnection, database_name: str | None, obj_name: str, *args, **kwargs):
    """
    Shows detailed column information about a database table via SQLAlchemy, bind parameters if provided (prepared SQL), and return the fully rendered SQL (with literals) in metadata.

    Arguments:
      database_name - Database name
      obj_name - table or view name

    Returns:
      ResponseType: formatted response with query results + metadata
    """
    logger.debug(f"Tool: handle_base_columnDescription: Args: database_name: {database_name}, obj_name: {obj_name}")

    if len(database_name) == 0:
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
            "column_count": len(data)
        }
        logger.debug(f"Tool: handle_base_columnDescription: metadata: {metadata}")
        return create_response(data, metadata)


#------------------ Tool  ------------------#
# Read table preview tool
def handle_base_tablePreview(conn: TeradataConnection, table_name: str, database_name: str | None = None, *args, **kwargs):
    """
    This function returns data sample and inferred structure from a database table or view via SQLAlchemy, bind parameters if provided (prepared SQL), and return the fully rendered SQL (with literals) in metadata.

    Arguments:
      table_name - table or view name
      database_name - Database name

    Returns:
      ResponseType: formatted response with query results + metadata
    """
    logger.debug(f"Tool: handle_base_tablePreview: Args: tablename: {table_name}, databasename: {database_name}")

    if database_name is not None:
        table_name = f"{database_name}.{table_name}"
    with conn.cursor() as cur:
        cur.execute(f'select top 5 * from {table_name}')
        columns = cur.description
        sample = rows_to_json(cur.description, cur.fetchall())

        metadata = {
            "tool_name": "base_tablePreview",
            "database": database_name,
            "table_name": table_name,
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
        logger.debug(f"Tool: handle_base_tablePreview: metadata: {metadata}")
        return create_response(sample, metadata)

#------------------ Tool  ------------------#
# Read table affinity tool
def handle_base_tableAffinity(conn: TeradataConnection, database_name: str, obj_name: str, *args, **kwargs):
    """
    Get tables commonly used together by database users, this is helpful to infer relationships between tables via SQLAlchemy, bind parameters if provided (prepared SQL), and return the fully rendered SQL (with literals) in metadata.

    Arguments:
      database_name - Database name
      object_name - table or view name

    Returns:
      ResponseType: formatted response with query results + metadata
    """
    logger.debug(f"Tool: handle_base_tableAffinity: Args: database_name: {database_name}, obj_name: {obj_name}")
    table_affiity_sql="""
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
        rows = cur.execute(table_affiity_sql.format(table_name=obj_name, database_name=database_name))
        data = rows_to_json(cur.description, rows.fetchall())
    if len(data):
        affinity_info=f'This data contains the list of tables most commonly queried alongside object {database_name}.{obj_name}'
    else:
        affinity_info=f'Object {database_name}.{obj_name} is not often queried with any other table or queried at all, try other ways to infer its relationships.'
    metadata = {
        "tool_name": "handle_base_tableAffinity",
        "database": database_name,
        "object": obj_name,
        "table_count": len(data),
        "comment": affinity_info
    }
    logger.debug(f"Tool: handle_base_tableAffinity: metadata: {metadata}")
    return create_response(data, metadata)


#------------------ Tool  ------------------#
# Read table usage tool
def handle_base_tableUsage(conn: TeradataConnection, database_name: str | None = None, *args, **kwargs):
    """
    Measure the usage of a table and views by users in a given schema, this is helpful to infer what database objects are most actively used or drive most value via SQLAlchemy, bind parameters if provided (prepared SQL), and return the fully rendered SQL (with literals) in metadata.

    Arguments:
      database_name - Database name

    Returns:
      ResponseType: formatted response with query results + metadata
    """

    logger.debug("Tool: handle_base_tableUsage: Args: database_name:")
    database_name_filter = f"AND objectdatabasename = '{database_name}'" if database_name else ""

    table_usage_sql="""
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
        rows = cur.execute(table_usage_sql.format(database_name_filter=database_name_filter))
        data = rows_to_json(cur.description, rows.fetchall())
    if len(data):
        info=f'This data contains the list of tables most frequently queried objects in database schema {database_name}'
    else:
        info=f'No tables have recently been queried in the database schema {database_name}.'
    metadata = {
        "tool_name": "handle_base_tableUsage",
        "database": database_name,
        "table_count": len(data),
        "comment": info
    }
    logger.debug(f"Tool: handle_base_tableUsage: metadata: {metadata}")
    return create_response(data, metadata)

#------------------ Tool  ------------------#
# Dynamic SQL execution tool
def util_base_dynamicQuery(conn: TeradataConnection, sql_generator: callable, *args, **kwargs):
    """
    This tool is used to execute dynamic SQL queries that are generated at runtime by a generator function.

    Arguments:
      sql_generator (callable) - a generator function that returns a SQL query string

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
                {"name": col[0], "type": col[1].__name__ if hasattr(col[1], '__name__') else str(col[1])}
                for col in cur.description
            ] if cur.description else [],
            "row_count": len(data)
        }
        logger.debug(f"Tool: util_base_dynamicQuery: metadata: {metadata}")
        return create_response(data, metadata)
