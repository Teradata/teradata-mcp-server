"""
Chat Completion tools for calling LLM inference servers via Teradata.
Follows the tmpl package pattern for semantic layer tools.
"""

import logging
import os
import re
from pathlib import Path

import yaml
from teradatasql import TeradataConnection

from teradata_mcp_server.tools.utils import create_response, rows_to_json

logger = logging.getLogger("teradata_mcp_server")

SYSTEM_MESSAGE_MAX_LENGTH = 100  # Max length for system message in Teradata string literal

def get_default_chat_config():
    """Default chat completion configuration as fallback"""
    return {
        "base_url": None,
        "model": None,
        "http_proxy": "",
        "ignore_https_verification": False,
        "custom_headers": [],
        "body_parameters": [],
        "pem_file_sql": "",
        "delays": "500",
        "retries_number": 0,
        "throw_error_on_rate_limit": False,
        "output_text_length": 16000,
        "remove_deepseek_thinking": False,
        "databases": {
            "function_db": "openai_client",
        },
        "output": {
            "include_diagnostics": True,
            "include_tachyon_headers": True,
        },
    }


def _validate_chat_config(config: dict) -> bool:
    """
    Validate that mandatory parameters are present.

    Mandatory:
      - base_url
      - model
      - databases.function_db
    """
    if not isinstance(config, dict):
        logger.error("chat config is not a dictionary")
        return False

    base_url = config.get("base_url")
    model = config.get("model")
    function_db = (
        config.get("databases", {}).get("function_db")
        if isinstance(config.get("databases"), dict)
        else None
    )

    missing = []
    if not base_url:
        missing.append("base_url")
    if not model:
        missing.append("model")
    if not function_db:
        missing.append("databases.function_db")

    if missing:
        logger.error(
            "Chat completion config missing mandatory parameter(s): %s. "
            "Tool will not be loaded.",
            ", ".join(missing),
        )
        return False

    return True


def load_chat_config():
    """
    Load chat completion configuration using the layered strategy.

    Loads from:
    1. Default values (in code)
    2. Packaged src/teradata_mcp_server/config/chat_config.yml (developer defaults)
    3. User config directory chat_config.yml (runtime overrides)

    Returns:
        Merged configuration dictionary
    """
    try:
        from teradata_mcp_server import config_loader

        # Load configuration (uses global config directory)
        config = config_loader.load_config(
            "chat_config.yml",
            defaults=get_default_chat_config()
        )

        logger.info("Chat completion configuration loaded successfully")
        return config

    except Exception as e:
        logger.error(f"Error loading chat completion config: {e}", exc_info=True)
        return get_default_chat_config()

# Initialize global config once at import time
CHAT_CONFIG = load_chat_config()


def _prepare_sql_inputs(sql: str, system_message: str) -> tuple[str, str]:
    """
    Prepare SQL and system message for use in Teradata queries.

    - Remove trailing semicolon from SQL (if present)
    - Normalize all whitespace (spaces, tabs, newlines) to single spaces
    - Escape single quotes in system message for Teradata string literal
    """
    # 1) Normalize whitespace in SQL
    #    Replace any run of whitespace (including newlines) with a single space
    normalized_sql = re.sub(r"\s+", " ", sql or "").strip()

    # 2) Remove trailing semicolon if present
    if normalized_sql.endswith(';'):
        normalized_sql = normalized_sql[:-1].strip()

    # 3) Normalize whitespace in system_message
    normalized_system_message = re.sub(r"\s+", " ", system_message or "").strip()

    # 4) Escape single quotes in system message for Teradata
    escaped_system_message = normalized_system_message.replace("'", "''")

    return normalized_sql, escaped_system_message


def build_complete_chat_sql(
    input_sql: str,
    system_message: str,
    config: dict
) -> str:
    """
    Build SQL query for CompleteChat table operator.

    Args:
        input_sql: SQL query returning table with 'txt' column
        system_message: System instruction for the assistant
        config: Configuration dictionary

    Returns:
        Complete SQL query string
    """
    # Validate required config
    base_url = config.get('base_url')
    if not base_url or base_url == "":
        raise ValueError(
            "BaseURL is required but not configured in chat_config.yml. "
            "Please set BaseURL to your inference server URL "
            "(e.g., 'http://localhost:11434' or 'https://api.openai.com')"
        )

    model = config.get('model')
    if not model or model == "":
        raise ValueError(
            "Model is required but not configured in chat_config.yml. "
            "Please set Model to your model name "
            "(e.g., 'qwen2.5-coder:7b', 'gpt-4', 'claude-3-opus')"
        )

    # Get API key from environment variable
    api_key = os.environ.get('CHAT_API_KEY')

    # Get database name
    database_name = config.get('databases', {}).get('function_db', 'openai_client')

    # Get other configuration values with defaults
    ignore_https = config.get('IgnoreHTTPSVerification', False)
    custom_headers = config.get('CustomHeaders', [])
    body_params = config.get('BodyParameters', [])
    delays = config.get('Delays', '500')
    retries = config.get('RetriesNumber', 0)
    throw_on_rate_limit = config.get('ThrowErrorOnRateLimit', False)
    output_text_length = config.get('OutputTextLength', 16000)
    remove_deepseek = config.get('RemoveDeepSeekThinking', False)
    include_diagnostics = config.get('output', {}).get('include_diagnostics', True)
    include_tachyon = config.get('output', {}).get('include_tachyon_headers', True)

    # Build USING clause parameters
    using_params = []
    using_params.append(f"        BaseURL('{base_url}')")
    using_params.append(f"        SystemMessage('{system_message}')")
    using_params.append(f"        Model('{model}')")

    # Add optional API key from environment
    if api_key:
        using_params.append(f"        ApiKey('{api_key}')")
        logger.debug("Using API key from CHAT_API_KEY environment variable")
    else:
        logger.debug("No API key found in CHAT_API_KEY environment variable")

    # Add custom headers
    if custom_headers:
        headers_list = [f"{h['key']}: {h['value']}" for h in custom_headers]
        headers_str = "', '".join(headers_list)
        using_params.append(f"        CustomHeaders('{headers_str}')")

    # Add body parameters
    if body_params:
        params_list = []
        for param in body_params:
            key = param['key']
            value = param['value']
            params_list.append(f"{key}:{value}")
        params_str = "', '".join(params_list)
        using_params.append(f"        BodyParameters('{params_str}')")

    # Add rate limiting config
    using_params.append(f"        Delays('{delays}')")
    using_params.append(f"        RetriesNumber({retries})")
    using_params.append(f"        ThrowErrorOnRateLimit('{str(throw_on_rate_limit).upper()}')")

    # Add output config
    using_params.append(f"        OutputTextLength({output_text_length})")
    using_params.append(f"        RemoveDeepSeekThinking('{str(remove_deepseek).upper()}')")

    # Add diagnostic options
    if include_diagnostics:
        using_params.append("        OutputProcessingDetails('TRUE')")

    if include_tachyon:
        using_params.append("        TachyonCallLevelHeaders('TRUE')")

    # Add HTTPS verification override
    if ignore_https:
        using_params.append("        IgnoreHTTPSVerification('TRUE')")

    # Build complete query
    using_clause = "\n".join(using_params)

    complete_sql_query = f"""SELECT *
FROM {database_name}.CompleteChat(
    ON ({input_sql}) AS InputTable
    USING
{using_clause}
) AS dt"""

    return complete_sql_query


def handle_chat_completeChat(
    conn: TeradataConnection,
    sql: str,
    system_message: str,
    *args,
    **kwargs
):
    """
    Execute chat completion using OpenAI-compatible LLM inference server.

    Calls the Teradata CompleteChat table operator to generate text completions,
    summaries, classifications, and other AI-powered text transformations.

    Arguments:
        sql: SQL query that returns a table with a 'txt' column containing prompts.
            Example: "SELECT id, txt FROM emails.customer_emails"
        system_message: System instruction that defines the assistant's behavior.
                       Example: "You are a sentiment analyzer. Classify as positive, negative, or neutral."

    Returns:
        JSON response with generated text for each input row, including:
        - response_txt: Generated text response from the LLM
    """
    logger.debug(
        f"Tool: handle_chat_completeChat: "
        f"sql={sql[:100] if sql else 'None'}..., "
        f"system_message={system_message[:50] if system_message else 'None'}..."
    )

    # Load config
    config = CHAT_CONFIG

    # If config is missing or invalid, do not execute the tool
    if not config:
        error_msg = (
            "Chat completion tool is disabled because mandatory configuration "
            "parameters are missing (base_url, model, databases.function_db)."
        )
        logger.error(error_msg)
        return create_response(
            {"error": error_msg},
            {
                "tool_name": "chat_completeChat",
                "status": "error",
                "error_type": "configuration_error",
            },
        )

    try:
        # Prepare inputs: remove trailing semicolon and escape quotes, normalize whitespace
        cleaned_sql, escaped_system_message = _prepare_sql_inputs(sql, system_message)

        # Build the base CompleteChat SQL query
        complete_sql_query = build_complete_chat_sql(
            input_sql=cleaned_sql,
            system_message=escaped_system_message,
            config=config
        )

        # Add CAST for response_txt using output_text_length from config
        output_len = int(config.get("output_text_length", 16000) or 16000)
        wrapped_sql = f"""
SELECT
    CAST(response_txt AS VARCHAR({output_len}) CHARACTER SET UNICODE) AS response_txt,
    t.*
FROM (
{complete_sql_query}
) AS t
"""

        logger.debug(f"Executing CompleteChat SQL (with CAST):\n{wrapped_sql}")

        # Execute query
        with conn.cursor() as cur:
            rows = cur.execute(wrapped_sql)
            data = rows_to_json(cur.description, rows.fetchall())

            # Build metadata
            metadata = {
                "tool_name": "chat_completeChat",
                "base_url": config.get("base_url"),
                "model": config.get("model"),
                "system_message": system_message[:100] + "..." if len(system_message) > SYSTEM_MESSAGE_MAX_LENGTH else system_message,
                "database_name": config.get("databases", {}).get("function_db"),
                "rows_processed": len(data)
            }

            logger.debug(f"Tool: handle_chat_completeChat: Metadata: {metadata}")
            return create_response(data, metadata)

    except ValueError as ve:
        # Configuration errors
        error_msg = str(ve)
        logger.error(f"Configuration error: {error_msg}", exc_info=True)
        return create_response(
            {"error": error_msg},
            {
                "tool_name": "chat_completeChat",
                "status": "error",
                "error_type": "configuration_error"
            }
        )
    except Exception as e:
        # Execution errors
        error_msg = str(e)
        logger.error(f"Execution error: {error_msg}", exc_info=True)
        return create_response(
            {"error": error_msg},
            {
                "tool_name": "chat_completeChat",
                "status": "error",
                "error_type": "execution_error"
            }
        )


def handle_chat_aggregatedCompleteChat(
    conn: TeradataConnection,
    sql: str,
    system_message: str,
    *args,
    **kwargs
):
    """
    Execute chat completion and return aggregated response statistics.

    Wraps CompleteChat with aggregation to identify common response patterns.
    Filters out empty responses, groups by unique response text, and counts occurrences.

    Use this tool when you want to:
    - Analyze distribution of LLM responses (e.g., sentiment counts)
    - Identify most common classifications or categories
    - Get summary statistics of text generation results
    - Count unique answer patterns across multiple inputs

    Arguments:
        sql: SQL query that returns a table with a 'txt' column containing prompts.
            Example: "SELECT id, txt FROM emails.customer_emails"
        system_message: System instruction that defines the assistant's behavior.
                       Example: "You are a sentiment analyzer. Classify as positive, negative, or neutral."

    Returns:
        JSON response with aggregated results:
        - response_txt: Unique response text
        - response_count: Number of times this response occurred
        - Metadata including total and unique response counts

    Example:
        Input: 100 customer emails for sentiment analysis
        Output:
        [
          {"response_txt": "positive", "response_count": 65},
          {"response_txt": "negative", "response_count": 20},
          {"response_txt": "neutral", "response_count": 15}
        ]
    """
    logger.debug(
        f"Tool: handle_chat_aggregatedCompleteChat: "
        f"sql={sql[:100] if sql else 'None'}..., "
        f"system_message={system_message[:50] if system_message else 'None'}..."
    )

    # Load config
    config = CHAT_CONFIG

    try:
        # Prepare inputs: remove trailing semicolon and escape quotes, normalize whitespace
        cleaned_sql, escaped_system_message = _prepare_sql_inputs(sql, system_message)

        # Build the base CompleteChat SQL query
        complete_chat_sql = build_complete_chat_sql(
            input_sql=cleaned_sql,
            system_message=escaped_system_message,
            config=config
        )

        output_len = int(config.get('OutputTextLength', 16000) or 16000)

        # Wrap with aggregation query, casting response_txt
        aggregated_sql = f"""
SELECT
    CAST(response_txt AS VARCHAR({output_len}) CHARACTER SET UNICODE) AS response_txt,
    COUNT(*) AS response_count
FROM (
    {complete_chat_sql}
) AS chat_results
WHERE response_txt IS NOT NULL
  AND response_txt <> ''
GROUP BY 1
"""

        logger.debug(f"Executing Aggregated CompleteChat SQL:\n{aggregated_sql}")

        # Execute query
        with conn.cursor() as cur:
            rows = cur.execute(aggregated_sql)
            data = rows_to_json(cur.description, rows.fetchall())

            # Calculate statistics - handle both int and string types
            total_responses = 0
            for row in data:
                count_value = row.get('response_count', 0)
                if isinstance(count_value, str | int | float):
                    total_responses += int(count_value)
                else:
                    total_responses += 0

            unique_responses = len(data)

            # Build metadata
            api_key_configured = bool(os.environ.get('CHAT_API_KEY'))

            metadata = {
                "tool_name": "chat_aggregatedCompleteChat",
                "operation": "aggregated_chat_completion",
                "base_url": config.get('base_url'),
                "model": config.get('model'),
                "system_message": system_message[:100] + "..." if len(system_message) > SYSTEM_MESSAGE_MAX_LENGTH else system_message,
                "database_name": config.get('databases', {}).get('function_db'),
                "api_key_configured": api_key_configured,
                "total_responses": total_responses,
                "unique_responses": unique_responses,
                "aggregation_applied": {
                    "filter": "response_txt IS NOT NULL AND response_txt <> ''",
                    "group_by": "column 1 (response_txt)",
                    "order_by": "response_count DESC, response_txt"
                },
                "description": "Aggregated chat completion results showing unique responses and their counts"
            }

            logger.debug(f"Tool: handle_chat_aggregatedCompleteChat: Metadata: {metadata}")
            return create_response(data, metadata)

    except ValueError as ve:
        error_msg = str(ve)
        logger.error(f"Configuration error: {error_msg}", exc_info=True)
        return create_response(
            {"error": error_msg},
            {
                "tool_name": "chat_aggregatedCompleteChat",
                "status": "error",
                "error_type": "configuration_error"
            }
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Execution error: {error_msg}", exc_info=True)
        return create_response(
            {"error": error_msg},
            {
                "tool_name": "chat_aggregatedCompleteChat",
                "status": "error",
                "error_type": "execution_error"
            }
        )


# Dynamically update docstrings with config values
def _update_docstrings_with_config():
    """Update function docstrings with actual configuration values"""
    config = CHAT_CONFIG

    # Get config values
    base_url = config.get('base_url', 'not configured')
    model = config.get('model', 'not configured')
    include_diagnostics = config.get('output', {}).get('include_diagnostics', True)
    include_tachyon = config.get('output', {}).get('include_tachyon_headers', True)

    # Build additional output fields list
    additional_outputs = []
    if include_tachyon:
        additional_outputs.append("        - Tachyon headers: x_request_id, x_correlation_id, x_wf_request_date")
    if include_diagnostics:
        additional_outputs.append("        - Diagnostics: retries_made, last_attempt_duration, rate_limit_exceeded")

    # Build config info string
    config_info = f"\n\nConfigured for: {base_url} using model '{model}'"

    # Update completeChat docstring
    if handle_chat_completeChat.__doc__:
        # Add additional output fields if any
        if additional_outputs:
            additional_fields = "\n" + "\n".join(additional_outputs)
            # Insert before the config info
            handle_chat_completeChat.__doc__ += additional_fields

        # Add config info
        handle_chat_completeChat.__doc__ += config_info

    # Update aggregatedCompleteChat docstring (it doesn't have conditional outputs, just add config)
    if handle_chat_aggregatedCompleteChat.__doc__:
        handle_chat_aggregatedCompleteChat.__doc__ += config_info


# Apply dynamic docstring updates
_update_docstrings_with_config()
