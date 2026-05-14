"""Utilities for Teradata tools package.

Exposes helper functions used across tools implementations. This package
replaces the older single-module utils.py to avoid name conflicts and to group
protocol-agnostic helpers together.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from collections import OrderedDict
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from .queryband import build_queryband, sanitize_qb_value  # noqa: F401


# -------------------- Serialization & response helpers -------------------- #
def serialize_teradata_types(obj: Any) -> Any:
    """Convert Teradata-specific types to JSON-serialisable formats.

    Handles None explicitly so that database NULL values are preserved
    as Python None (→ JSON null) rather than the string ``"None"``.

    Args:
        obj: The value to convert.

    Returns:
        A JSON-native type (str, int, float, bool, None) or an
        ISO-formatted date string.
    """
    if obj is None:
        return None
    if isinstance(obj, date | datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def rows_to_json(cursor_description: Any, rows: list[Any]) -> list[dict[str, Any]]:
    """Convert DB rows into JSON objects using column names as keys."""
    if not cursor_description or not rows:
        return []
    columns = [col[0] for col in cursor_description]
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append({col: serialize_teradata_types(val) for col, val in zip(columns, row)})
    return out


def _make_serialisable(obj: Any) -> Any:
    """Recursively walk an object tree, converting every leaf to a
    JSON-native Python type.

    This is the deep-conversion counterpart of
    :func:`serialize_teradata_types`.  It ensures that nested dicts
    and lists produced by tool handlers contain only types that
    ``json.dumps`` can serialise without a custom *default* hook,
    and — critically — that ``None`` values survive as ``None``
    (JSON ``null``) instead of the string ``"None"``.

    Args:
        obj: Any Python object (scalar, dict, list, tuple, etc.).

    Returns:
        A recursively sanitised copy whose leaves are all
        ``str | int | float | bool | None``.
    """
    if obj is None:
        return None
    if isinstance(obj, str | int | float | bool):
        return obj
    if isinstance(obj, date | datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _make_serialisable(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_make_serialisable(item) for item in obj]
    # Fallback: cast to string (e.g. bytes, custom objects)
    return str(obj)


def create_response(
    data: Any,
    metadata: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> dict:
    """Create a standardised MCP response structure.

    .. versionchanged:: 1.1.0
       Returns a **dict** instead of a JSON string.  The MCP
       framework requires ``structured_content`` to be a ``dict``
       (or ``None``); returning a JSON string caused the server to
       wrap it in a ``[{"type": "text", ...}]`` list which the
       framework rejected.

       All nested values are recursively sanitised via
       :func:`_make_serialisable` so that ``None`` / NULL values
       are preserved as ``None`` (JSON ``null``) and Teradata-
       specific types (``Decimal``, ``datetime``, etc.) are
       converted to JSON-native equivalents.

    Args:
        data:     Payload — typically a list of row-dicts.
        metadata: Optional dict of tool metadata (tool_name, sql, etc.).
        error:    Optional error dict; if supplied the response
                  status is set to ``"error"``.

    Returns:
        dict: A JSON-serialisable dict ready to be used as
              MCP ``structured_content``.
    """
    if error:
        resp: dict[str, Any] = {"status": "error", "message": error}
        if metadata:
            resp["metadata"] = _make_serialisable(metadata)
        return resp

    resp = {
        "status": "success",
        "results": _make_serialisable(data),
    }
    if metadata:
        resp["metadata"] = _make_serialisable(metadata)
    return resp


# ------------------------------ Auth helpers ------------------------------ #
def parse_auth_header(auth_header: str | None) -> tuple[str, str]:
    """Parse an HTTP Authorization header into (scheme, value).

    Returns ("", "") if header is missing or malformed. Scheme is lowercased
    and stripped. Value is stripped (but not decoded).
    """
    if not auth_header:
        return "", ""
    try:
        scheme, _, value = auth_header.partition(" ")
        return scheme.strip().lower(), value.strip()
    except Exception:
        return "", ""


def compute_auth_token_sha256(auth_header: str | None) -> str | None:
    """Return a hex SHA-256 over the value portion of Authorization header."""
    scheme, value = parse_auth_header(auth_header)
    if not value:
        return None
    try:
        h = hashlib.sha256()
        h.update(value.encode("utf-8"))
        return h.hexdigest()
    except Exception:
        return None


def parse_basic_credentials(b64_value: str) -> tuple[str | None, str | None]:
    """Decode a Basic credential value into (username, secret)."""
    try:
        raw = base64.b64decode(b64_value).decode("utf-8")
        if ":" not in raw:
            return None, None
        user, secret = raw.split(":", 1)
        user = user.strip()
        secret = secret.strip()
        if not user or not secret:
            return None, None
        return user, secret
    except Exception:
        return None, None


def infer_logmech_from_header(auth_header: str | None, default_basic_logmech: str = "LDAP") -> tuple[str, str]:
    """Infer LOGMECH and the credential payload based on the header.

    Returns (logmech, payload) where:
      - If scheme == 'bearer' → ("JWT", <token>)
      - If scheme == 'basic'  → (default_basic_logmech, <secret>)
      - Otherwise → ("", "")
    """
    scheme, value = parse_auth_header(auth_header)
    if scheme == "bearer" and value:
        return "JWT", value
    if scheme == "basic" and value:
        return default_basic_logmech.upper(), value
    return "", ""


def execute_analytic_function(function_name: str, tables_to_df=None, **kwargs):
    """
    Executes the specified analytic function with the provided keyword arguments.

    :param function_name: Name of the analytic function to execute.
    :param tables_to_df: List of table names to convert to DataFrames.
    :param kwargs: Keyword arguments for the analytic function.
    :return: Response containing the result of the function execution.
    """
    # Log the received keyword arguments. But make sure not to log sensitive information.
    # Hence remove 'headers' from print.
    if tables_to_df is None:
        tables_to_df = []
    func_params = {k: v for k, v in kwargs.items() if k != "headers"}

    # Analytic functions are called with 'tdml_' prefix. Remove it.
    function_name = function_name[5:]

    logger = logging.getLogger("teradata_mcp_server.utils")
    logger.info(f"received kwargs: {func_params} for the function {function_name}")

    # Import the function dynamically based on its name

    import teradataml as tdml
    from teradataml import DataFrame, copy_to_sql, in_schema
    from teradataml.common.utils import UtilFuncs

    # Teradataml accepts DataFrame as input, so we need to convert the table_name
    # and object to DataFrame. Some of the functions accepts object also. If object
    # is provided, we convert it to DataFrame as well.
    db_name = kwargs.get("database_name")
    for arg_name in tables_to_df:
        table_name = kwargs.get(arg_name)

        # Create DataFrame only if table_name is provided.
        if table_name:
            # Table name can be provided with or without schema name. First, extract the schema name and table name.
            db_name_extracted, table_name = (
                UtilFuncs._extract_db_name(table_name),
                UtilFuncs._extract_table_name(table_name),
            )

            # In some rare cases, input is received with db_name and also table name with schema.
            # If they are different, raise a ValueError.
            if db_name and db_name_extracted and (db_name != db_name_extracted):
                raise ValueError(
                    f"Database name provided in 'database_name' argument: {db_name} is different "
                    f"from the database name provided in table name: {db_name_extracted}. "
                    f"Provide same values. Or, provide database name in table name only."
                )

            db_name = db_name or db_name_extracted

            kwargs[arg_name] = DataFrame(in_schema(db_name, table_name)) if db_name else DataFrame(table_name)

    # Execute the function with the provided keyword arguments
    result = getattr(tdml, function_name)(**kwargs)

    result_to_store = result.result if getattr(result, "result", None) else result.output

    metadata = {
        "tool_name": function_name,
        "database_name": kwargs.get("database_name"),
        "output_table_name": kwargs.get("output_table_name"),
    }

    # If output_table_name is provided, copy the result to the specified table.
    if kwargs.get("output_table_name") is not None:
        copy_to_sql(result_to_store, table_name=kwargs["output_table_name"], if_exists="fail")

        return create_response(result, metadata)

    return create_response([rec._asdict() for rec in result_to_store.itertuples()], metadata)


def _clean_python_types(raw_types: str) -> str:
    """Extract simple type names from a Python type tuple string, removing teradataml internals."""
    import re

    names = re.findall(r"class '(?:[\w.]+\.)?(\w+)'", raw_types)
    cleaned = []
    for n in names:
        mapped = "str" if n in ("Feature", "DataFrame") else n
        if mapped not in cleaned:
            cleaned.append(mapped)
    return ", ".join(cleaned) if cleaned else "str"


def build_tdml_tool_docstring(summary: str, func_metadata, partition_order_cols: list[str]) -> str:
    """Build a compact MCP tool docstring from a curated summary and function metadata."""
    lines = [summary, "", "Arguments:"]

    for arg in func_metadata.arguments:
        name = arg.get_lang_name()
        desc = (arg.get_lang_description() or arg.get_sql_description() or "").strip()
        # Keep only first sentence
        first_sentence = desc.split(".")[0].rstrip()
        required_label = "Required" if arg.is_required() else "Optional"
        types_str = _clean_python_types(str(arg.get_python_type() or ""))
        lines.append(f"  {name} - {first_sentence}. {required_label}. Types: {types_str}.")

    for col_name in partition_order_cols:
        lines.append(
            f"  {col_name}_partition_column - Partition column(s) for the {col_name} table. Optional. Types: str, list."
        )
        lines.append(
            f"  {col_name}_order_column - Order column(s) for the {col_name} table. Optional. Types: str, list."
        )

    lines.append("  output_table_name - Persist result to this table. Optional. Types: str.")
    lines.append("  database_name - Database to use. Optional. Types: str.")
    lines.append("")
    lines.append("Returns:")
    lines.append("  list of dicts, or table name when output_table_name is set.")

    return "\n".join(lines)


def get_anlytic_function_signature(params):
    """
    Get the function signature from the parameters.

    PARAMETERS:
        params:
            Required Argument.
            Specifies the parameters of the function.
            Types: list of dict

    RETURNS:
        str: Function signature string.

    RAISES:
        None
    """
    function_params = OrderedDict((k, v) for k, v in params.items())
    function_params["output_table_name"] = None
    function_params["database_name"] = None

    # Generate function argument string.
    func_args_str = ", ".join(
        [
            "{} = {}".format(param, f'"{value}"' if isinstance(value, str) else value)
            for param, value in function_params.items()
        ]
    )
    return func_args_str


def get_dynamic_function_definition():
    """
    Generate a dynamic function definition string for Teradata Analytics functions.
    """
    s = '''
def {analytic_function}({func_args_str}):
    """
    {doc_string}

    Most Importantly:
          Never add optional arguments while function calling, unless specified in user query.
          Never include empty list in any of the function arguments.
          For any argument, user can pass multiple values.
          Do not consider a comma seperated values in such case.
          Generate a list of values in such case and pass it as argument.
    """
    params = {{arg: value for arg, value in locals().items() if arg not in ('vantage_auth')}}
    tables_to_df = {tables_to_df}
    return execute_analytic_function('{analytic_function}', tables_to_df, **params)
    '''
    return s


def get_partition_col_order_col_doc_string(col_name):
    """Returns the column name used to add partition/order params for a given input table."""
    return col_name
