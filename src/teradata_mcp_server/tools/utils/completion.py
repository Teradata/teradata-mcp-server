"""Argument completion handlers for dynamic table/column name suggestions."""

from mcp_types import Completion
from sqlalchemy import Connection, text


async def fetch_table_completions(prefix: str, conn: Connection | None) -> list[Completion]:
    """Query Teradata for table names matching the given prefix.

    Args:
        prefix: The partial table name to match (e.g., "customer" matches "customer_dim")
        conn: SQLAlchemy connection; if None, returns empty list

    Returns:
        List of Completion suggestions from DBC.TablesV, limited to 50 results
    """
    if not conn:
        return []

    prefix_pattern = f"{prefix}%"

    query = text("""
        SELECT DISTINCT TableName
        FROM DBC.TablesV
        WHERE TableName LIKE :pattern
        AND DatabaseName NOT IN ('DBC', 'SYSLIB', 'SYSUDTLIB')
        ORDER BY TableName
        LIMIT 50
    """)

    try:
        result = conn.execute(query, {"pattern": prefix_pattern})
        tables = [row[0] for row in result.fetchall()]
        return [Completion(label=table) for table in tables]
    except Exception:
        # Silently fail on query errors (missing view, permission denied, etc.)
        return []


async def fetch_column_completions(prefix: str, conn: Connection | None) -> list[Completion]:
    """Query Teradata for column names matching the given prefix.

    Args:
        prefix: The partial column name to match (e.g., "cust" matches "customer_id")
        conn: SQLAlchemy connection; if None, returns empty list

    Returns:
        List of Completion suggestions from DBC.ColumnsV, limited to 50 results
    """
    if not conn:
        return []

    prefix_pattern = f"{prefix}%"

    query = text("""
        SELECT DISTINCT ColumnName
        FROM DBC.ColumnsV
        WHERE ColumnName LIKE :pattern
        AND DatabaseName NOT IN ('DBC', 'SYSLIB', 'SYSUDTLIB')
        ORDER BY ColumnName
        LIMIT 50
    """)

    try:
        result = conn.execute(query, {"pattern": prefix_pattern})
        columns = [row[0] for row in result.fetchall()]
        return [Completion(label=column) for column in columns]
    except Exception:
        # Silently fail on query errors
        return []
