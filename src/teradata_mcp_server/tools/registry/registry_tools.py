"""
Utilities for executing database-registered tools (UDFs and Macros).

This module provides the execution logic for tools that are registered
in the database registry views.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger("teradata_mcp_server.registry_tools")


def format_sql_value(value: Any, python_type: type) -> str:
    """
    Format a Python value as SQL literal for direct insertion into SQL.

    This is used instead of parameter binding because SQLAlchemy's parameter
    binding does not preserve type information correctly with the Teradata driver.

    Args:
        value: The value to format
        python_type: The Python type hint for the parameter

    Returns:
        Formatted SQL literal as a string
    """
    if value is None:
        return 'NULL'

    # Boolean types (check before numeric as bool is subclass of int)
    if python_type == bool:
        return '1' if value else '0'

    # Numeric types - convert to string without quotes
    if python_type in (int, float):
        return str(value)

    # String types need quoting and escaping
    if python_type in (str, type(None)):
        # Escape single quotes by doubling them (SQL standard)
        escaped_value = str(value).replace("'", "''")
        return f"'{escaped_value}'"

    # Default: treat as string
    escaped_value = str(value).replace("'", "''")
    return f"'{escaped_value}'"


def cast_parameter_value(value: Any, target_type: type) -> Any:
    """
    Cast a parameter value to the target Python type for SQLAlchemy binding.

    This ensures that parameters passed from JSON/HTTP (often as strings)
    are properly typed before being bound to SQL parameters. SQLAlchemy needs
    correctly typed Python values to generate appropriate SQL bind parameters.

    Args:
        value: The value to cast (may be string, int, float, None, etc.)
        target_type: The target Python type (int, float, str, bool, etc.)

    Returns:
        The value cast to the target type, or None if value is None

    Example:
        >>> cast_parameter_value("123", int)
        123
        >>> cast_parameter_value("3.14", float)
        3.14
        >>> cast_parameter_value("true", bool)
        True
        >>> cast_parameter_value(None, int)
        None
    """
    # Handle None/NULL values
    if value is None:
        return None

    # If already correct type, return as-is
    if isinstance(value, target_type):
        return value

    try:
        # Boolean type requires special handling
        if target_type == bool:
            # Handle string boolean values
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'y', 't')
            # Convert to bool
            return bool(value)

        # Numeric types
        if target_type in (int, float):
            return target_type(value)

        # String type
        if target_type == str:
            return str(value)

        # For other types, attempt direct conversion
        return target_type(value)

    except (ValueError, TypeError) as e:
        logger.warning(
            f"Failed to cast parameter value {value!r} to type {target_type.__name__}: {e}. "
            f"Returning original value."
        )
        return value


def cast_parameters(params: Dict[str, Any], tool_def: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cast all parameter values to their expected types based on tool definition.

    This ensures that parameters received from clients (often as JSON strings)
    are properly typed before being passed to SQLAlchemy for binding.

    Args:
        params: Dictionary of parameter name -> value
        tool_def: Tool definition containing parameter metadata with type_hint

    Returns:
        Dictionary with same keys but values cast to correct types

    Example:
        >>> tool_def = {
        ...     'parameters': {
        ...         'customer_id': {'type_hint': int, 'position': 1},
        ...         'country': {'type_hint': str, 'position': 2}
        ...     }
        ... }
        >>> cast_parameters({'customer_id': '123', 'country': 'Spain'}, tool_def)
        {'customer_id': 123, 'country': 'Spain'}
    """
    params_def = tool_def.get('parameters', {})
    cast_params = {}

    for param_name, param_value in params.items():
        # Get type hint from tool definition
        param_info = params_def.get(param_name, {})
        target_type = param_info.get('type_hint', str)

        # Cast the value
        cast_value = cast_parameter_value(param_value, target_type)
        cast_params[param_name] = cast_value

        # Log ALWAYS for debugging (use info level to ensure it's visible)
        logger.info(
            f"[TYPE_CAST] Parameter '{param_name}': "
            f"before={param_value!r} (type={type(param_value).__name__}), "
            f"target_type={target_type.__name__}, "
            f"after={cast_value!r} (type={type(cast_value).__name__})"
        )

    return cast_params


def build_registry_sql_with_values(tool_def: Dict[str, Any], params: Dict[str, Any]) -> str:
    """
    Build SQL statement with actual parameter values formatted as literals.

    This approach is used because SQLAlchemy's parameter binding doesn't preserve
    type information correctly with the Teradata driver. By formatting values
    directly into the SQL, we ensure Teradata receives correctly typed literals.

    Args:
        tool_def: Tool definition from registry with db_object, object_type, parameters
        params: Dictionary of parameter values to format into SQL

    Returns:
        Complete SQL statement as a string with values inserted

    Example:
        >>> tool_def = {
        ...     'db_object': 'mydb.calculate_revenue',
        ...     'object_type': 'F',
        ...     'parameters': {
        ...         'customer_id': {'position': 1, 'type_hint': int},
        ...         'country': {'position': 2, 'type_hint': str}
        ...     }
        ... }
        >>> build_registry_sql_with_values(tool_def, {'customer_id': 123, 'country': 'Spain'})
        "SELECT mydb.calculate_revenue(123, 'Spain')"
    """
    db_object = tool_def['db_object']
    object_type = tool_def['object_type']
    params_def = tool_def.get('parameters', {})

    # Sort parameters by position to maintain correct order
    sorted_params = sorted(params_def.items(), key=lambda x: x[1].get('position', 0))

    # Build parameter values as SQL literals
    param_values = []
    for param_name, param_info in sorted_params:
        value = params.get(param_name)
        python_type = param_info.get('type_hint', str)

        # Format the value as SQL literal
        formatted_value = format_sql_value(value, python_type)
        param_values.append(formatted_value)

        logger.debug(f"Formatted parameter '{param_name}': {value!r} ({type(value).__name__}) -> {formatted_value} (SQL literal)")

    params_str = ', '.join(param_values)

    # Build SQL based on object type
    if object_type.upper() == 'M':
        sql = f"EXEC {db_object}({params_str})"
    else:  # UDF (F = Function)
        sql = f"SELECT {db_object}({params_str})"

    logger.info(f"Built SQL with formatted values for {db_object}: {sql}")
    return sql


def build_registry_sql(tool_def: Dict[str, Any]) -> str:
    """
    Legacy function for backward compatibility.
    Returns SQL string without typed bindings.

    Note: This is kept for compatibility with tests and YAML tools.
    Registry tools should use build_registry_sql_with_bindings() instead.
    """
    db_object = tool_def['db_object']
    object_type = tool_def['object_type']
    params_def = tool_def.get('parameters', {})

    # Sort parameters by position to maintain correct order
    sorted_params = sorted(params_def.items(), key=lambda x: x[1].get('position', 0))

    # Build named parameter placeholders
    param_placeholders = [f":{param_name}" for param_name, _ in sorted_params]
    params_str = ', '.join(param_placeholders)

    # Build SQL based on object type
    if object_type.upper() == 'M':
        sql = f"EXEC {db_object}({params_str})"
    else:  # UDF (F = Function)
        sql = f"SELECT {db_object}({params_str})"

    return sql
