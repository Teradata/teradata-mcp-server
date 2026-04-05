import logging
import re
from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.engine import Connection, default
from teradatasql import TeradataConnection

from teradata_mcp_server.tools.utils import create_response, rows_to_json

logger = logging.getLogger("teradata_mcp_server")


# ------------------ Tool  ------------------#
# Read query tool
def handle_base_readQuery(
    conn: Connection, sql: str | None = None, tool_name: str | None = None, persist: bool = False, *args, **kwargs
):
    """
    Execute a SQL query via SQLAlchemy, bind parameters if provided (prepared SQL), and return the fully rendered SQL (with literals) in metadata.

    Arguments:
      sql     - SQL text, with optional bind-parameter placeholders
      persist - Set to True to persist the results as a table and reuse it later. Recommended for large result sets.

    Returns:
      ResponseType: formatted response with query results + metadata
                   (includes 'volatile_table' field in metadata if persist=True)
    """
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


# ------------------ Tool  ------------------#
# Dynamic SQL execution tool
def util_base_dynamicQuery(conn: TeradataConnection, sql_generator: Callable[..., str], *args, **kwargs):
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
                {"name": col[0], "type": col[1].__name__ if hasattr(col[1], "__name__") else str(col[1])}
                for col in cur.description
            ]
            if cur.description
            else [],
            "row_count": len(data),
        }
        logger.debug(f"Tool: util_base_dynamicQuery: metadata: {metadata}")
        return create_response(data, metadata)


# ------------------ Tool  ------------------#
# Extract and save DDL tool
def handle_base_saveDDL(
    conn: TeradataConnection,
    database_name: str,
    object_name: str,
    object_type: str = "PROCEDURE",
    output_dir: str = "./ddls_extracted",
    *args,
    **kwargs,
):
    """
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
