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
    """Convert Teradata-specific types to JSON serializable formats."""
    if isinstance(obj, (date, datetime)):
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


def create_response(data: Any, metadata: dict[str, Any] | None = None, error: dict[str, Any] | None = None) -> str:
    """Create a standardized JSON response structure."""
    if error:
        resp = {"status": "error", "message": error}
        if metadata:
            resp["metadata"] = metadata
        return json.dumps(resp, default=serialize_teradata_types)
    resp = {"status": "success", "results": data}
    if metadata:
        resp["metadata"] = metadata
    return json.dumps(resp, default=serialize_teradata_types)


# ------------------------------ Auth helpers ------------------------------ #
def parse_auth_header(auth_header: Optional[str]) -> tuple[str, str]:
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


def compute_auth_token_sha256(auth_header: Optional[str]) -> Optional[str]:
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


def parse_basic_credentials(b64_value: str) -> tuple[Optional[str], Optional[str]]:
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


def infer_logmech_from_header(auth_header: Optional[str], default_basic_logmech: str = "LDAP") -> tuple[str, str]:
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


def execute_analytic_function(function_name: str, tables_to_df=[], **kwargs):
    """
    Executes the specified analytic function with the provided keyword arguments.

    :param function_name: Name of the analytic function to execute.
    :param tables_to_df: List of table names to convert to DataFrames.
    :param kwargs: Keyword arguments for the analytic function.
    :return: Response containing the result of the function execution.
    """
    # Log the received keyword arguments. But make sure not to log sensitive information.
    # Hence remove 'headers' from print.
    func_params = {k: v for k, v in kwargs.items() if k != 'headers'}

    # Analytic functions are called with 'tdml_' prefix. Remove it.
    function_name = function_name[5:]

    logger = logging.getLogger("teradata_mcp_server.utils")
    logger.info("received kwargs: {} for the function {}".format(func_params, function_name))

    # Import the function dynamically based on its name

    from teradataml import DataFrame, in_schema, copy_to_sql
    from teradataml.common.utils import UtilFuncs
    import teradataml as tdml
    # Teradataml accepts DataFrame as input, so we need to convert the table_name
    # and object to DataFrame. Some of the functions accepts object also. If object
    # is provided, we convert it to DataFrame as well.
    db_name = kwargs.get('database_name', None)
    for arg_name in tables_to_df:

        table_name = kwargs.get(arg_name)

        # Create DataFrame only if table_name is provided.
        if table_name:

            # Table name can be provided with or without schema name. First, extract the schema name and table name.
            db_name_extracted, table_name = (UtilFuncs._extract_db_name(table_name),
                                             UtilFuncs._extract_table_name(table_name))

            # In some rare cases, input is received with db_name and also table name with schema.
            # If they are different, raise a ValueError.
            if db_name and db_name_extracted and (db_name != db_name_extracted):
                raise ValueError(f"Database name provided in 'database_name' argument: {db_name} is different "
                                 f"from the database name provided in table name: {db_name_extracted}. "
                                 f"Provide same values. Or, provide database name in table name only.")

            db_name = db_name or db_name_extracted

            kwargs[arg_name] = DataFrame(in_schema(db_name, table_name)) if db_name else DataFrame(table_name)

    # Execute the function with the provided keyword arguments
    result = getattr(tdml, function_name)(**kwargs)

    result_to_store = result.result if getattr(result, 'result', None) else result.output

    metadata = {
        "tool_name": function_name,
        "database_name": kwargs.get('database_name'),
        "output_table_name": kwargs.get('output_table_name')
    }

    # If output_table_name is provided, copy the result to the specified table.
    if kwargs.get('output_table_name') is not None:
        copy_to_sql(result_to_store,
                    table_name=kwargs['output_table_name'],
                    if_exists='fail')

        return create_response(result, metadata)

    return create_response([rec._asdict() for rec in result_to_store.itertuples()], metadata)


def convert_tdml_docstring_to_mcp_docstring(doc_string, partition_order_cols_doc_str):
    """
    Convert TeradataML function docstring to MCP tool docstring format.

    PARAMETERS:
        doc_string:
            Required Argument.
            Specifies the doc string for TeradataML function whose docstring needs to be converted.
            Types: str

        partition_order_cols_doc_str:
            Required Argument.
            Specifies a list of docstring fragments (strings) related to partition columns and order columns
            to be joined and appended.
            Types: list of str

    RETURNS:
        str: Converted docstring in MCP tool format.

    RAISES:
        None
    """

    # Replace all teradataml DataFrame with table & "data:" with "table_name".
    doc_string = doc_string.replace("teradataml DataFrame", "table name")
    doc_string = doc_string.replace("DataFrame", "table name")

    # Remove every thing from generic arguments since examples are not use full.
    # Then add output argument.
    addon_doc_string = """

        output_table_name:
            Optional Argument.
            Specifies the name of the table to push the result.
            Types: str

        database_name:
            Optional Argument.
            Specifies the name of the database to use.
            Types: str

    RETURNS:
        list of dictionaries or table.
        When user specifies the output_table_name argument, the function
        returns the table name where the result is pushed. Otherwise, it returns
        a list of dictionaries containing the result.
"""
    base_doc = doc_string.split("**generic_arguments")[0].strip()
    partition_order_doc = "".join(partition_order_cols_doc_str)
    final_doc_string = base_doc + partition_order_doc + addon_doc_string
    return final_doc_string


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
    function_params = OrderedDict((k, v)
                                  for k, v in params.items())
    function_params['output_table_name'] = None
    function_params['database_name'] = None

    # Generate function argument string.
    func_args_str = ", ".join(
        [
            "{} = {}".format(param, '"{}"'.format(value) if isinstance(value, str) else value)
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
    """
    Get the docstring for partition_column parameter.
    """
    return f"""

        {col_name}_partition_column:
            Optional Argument.
            Specifies the column(s) to partition the table mentioned in argument '{col_name}'.
            Types: str OR list of Strings (str)

        {col_name}_order_column:
            Optional Argument.
            Specifies the column(s) to order the data inside the table mentioned in argument '{col_name}'.
            Types: str OR list of Strings (str)"""