import inspect
import asyncio

def create_mcp_tool(
    *,
    executor_func=None,
    signature,
    inject_kwargs=None,
    validate_required=False,
    tool_name="mcp_tool",
    tool_description=None,
):
    """
    Unified factory for creating async MCP tool functions.


    All tool functions use asyncio.to_thread to execute blocking database operations.

    Args:
        executor_func: Callable that will be executed. Should be a function that
                        calls execute_db_tool with appropriate arguments.
        signature: The inspect.Signature for the MCP tool function.
        inject_kwargs: Dict of kwargs to inject when calling executor_func.
        validate_required: Whether to validate required parameters are present.
        tool_name: Name to assign to the MCP tool function.
        tool_description: Description/docstring for the MCP tool function.

    Returns:
        An async function suitable for use as an MCP tool.
    """
    inject_kwargs = inject_kwargs or {}

    # Extract annotations from signature parameters
    annotations = {
        name: param.annotation
        for name, param in signature.parameters.items()
        if param.annotation is not inspect.Parameter.empty
    }

    if validate_required:
        # Build list of required parameter names (those without defaults)
        required_params = [
            name for name, param in signature.parameters.items()
            if param.default is inspect.Parameter.empty
        ]

        async def _mcp_tool(**kwargs):
            missing = [n for n in required_params if n not in kwargs]
            if missing:
                raise ValueError(f"Missing required parameters: {missing}")
            merged_kwargs = {**inject_kwargs, **kwargs}
            return await asyncio.to_thread(executor_func, **merged_kwargs)
    else:
        async def _mcp_tool(**kwargs):
            merged_kwargs = {**inject_kwargs, **kwargs}
            return await asyncio.to_thread(executor_func, **merged_kwargs)

    _mcp_tool.__name__ = tool_name
    _mcp_tool.__signature__ = signature
    _mcp_tool.__doc__ = tool_description
    _mcp_tool.__annotations__ = annotations

    return _mcp_tool