"""
Utilities for executing database-registered tools (UDFs and Macros).

This module provides the execution logic for tools that are registered
in the database registry views.
"""

import logging
from typing import Any, Dict
from sqlalchemy import text
from sqlalchemy.engine import Connection

logger = logging.getLogger("teradata_mcp_server.registry_tools")


def build_registry_sql(tool_def: Dict[str, Any], params: Dict[str, Any]) -> str:
    """
    Build SQL statement to execute a database-registered tool (UDF or Macro).

    This is used by the simplified registry implementation where registry tools
    are executed via handle_base_readQuery (same as YAML tools).

    Args:
        tool_def: Tool definition from registry with db_object, object_type, parameters
        params: Parameter values from the tool call

    Returns:
        SQL statement as a string
    """
    db_object = tool_def['db_object']
    object_type = tool_def['object_type']
    params_def = tool_def.get('parameters', {})

    # Sort parameters by position
    sorted_params = sorted(params_def.items(), key=lambda x: x[1].get('position', 0))

    # Build parameter list
    param_values = []
    for param_name, param_info in sorted_params:
        value = params.get(param_name)
        formatted_value = _format_sql_value(value, param_info.get('type_hint', str))
        param_values.append(formatted_value)

    params_str = ', '.join(param_values)

    # Build SQL based on object type
    if object_type.upper() == 'M':
        sql = f"EXEC {db_object}({params_str})"
    else:  # UDF
        sql = f"SELECT {db_object}({params_str})"

    return sql

def _format_sql_value(value: Any, python_type: type) -> str:
    """
    Format a Python value for SQL insertion.

    Args:
        value: The value to format
        python_type: The Python type hint for the parameter

    Returns:
        Formatted SQL value as a string
    """
    if value is None:
        return 'NULL'

    # String types need quoting
    if python_type in (str, type(None)):
        # Escape single quotes by doubling them (SQL standard)
        escaped_value = str(value).replace("'", "''")
        return f"'{escaped_value}'"

    # Boolean types
    if python_type == bool:
        return '1' if value else '0'

    # Numeric types - convert to string without quotes
    if python_type in (int, float):
        return str(value)

    # Default: treat as string
    escaped_value = str(value).replace("'", "''")
    return f"'{escaped_value}'"
