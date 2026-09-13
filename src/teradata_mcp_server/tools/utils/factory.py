import asyncio
import inspect
from collections.abc import Callable
from typing import Any

GuardCheck = Callable[[dict[str, Any]], tuple[str, str] | None]


async def _fetch_request_context() -> Any:
    """Fetch RequestContext from FastMCP state in the async layer before thread dispatch."""
    try:
        from fastmcp.server.dependencies import get_context

        ctx = get_context()
        return await ctx.get_state("request_context")
    except Exception:
        return None


async def _confirm_guarded_operation(guard: GuardCheck, kwargs: dict[str, Any]) -> Any | None:
    """Run a guard check and, if it flags this call, require confirmation.

    Returns an ``InputRequiredResult`` the caller must return as-is (the
    modern-era "ask" leg of the call — see ``guard_mode.ConfirmationRequiredError``),
    or ``None`` to let the caller proceed to the handler.

    Unlike _fetch_request_context, failures here are NOT swallowed: if a guard
    flags a call as destructive, the operation must either be confirmed or
    fail outright — silently proceeding unconfirmed would defeat the point.
    """
    gate = guard(kwargs)
    if gate is None:
        return None

    from fastmcp.exceptions import ToolError
    from fastmcp.server.dependencies import get_context

    from teradata_mcp_server.tools.utils.guard_mode import ConfirmationRequiredError, confirm_destructive_operation

    operation_name, description = gate
    try:
        ctx = get_context()
    except Exception as e:
        raise ToolError(
            f"'{operation_name}' requires user confirmation, but no request context is available: {e}"
        ) from None
    try:
        await confirm_destructive_operation(ctx, operation_name, description)
    except ConfirmationRequiredError as ask:
        return ask.input_required
    return None


def create_mcp_tool(
    *,
    executor_func=None,
    signature,
    inject_kwargs=None,
    validate_required=False,
    tool_name="mcp_tool",
    tool_description=None,
    guard: GuardCheck | None = None,
):
    """
    Unified factory for creating async MCP tool functions.

    All tool functions use asyncio.to_thread to execute blocking database operations.
    Request context is automatically injected via _fetch_request_context.

    Args:
        executor_func: Callable that will be executed. Should be a function that
                        calls execute_db_tool with appropriate arguments.
        signature: The inspect.Signature for the MCP tool function.
        inject_kwargs: Dict of kwargs to inject when calling executor_func.
        validate_required: Whether to validate required parameters are present.
        tool_name: Name to assign to the MCP tool function.
        tool_description: Description/docstring for the MCP tool function.
        guard: Optional callable inspecting a call's kwargs. Return
            (operation_name, description) to require the client to confirm via
            elicitation before the handler runs, or None to let this call
            through unconfirmed. Lets a single tool gate only its destructive
            branches (e.g. an `operation="delete"` value) rather than every call.

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
            name for name, param in signature.parameters.items() if param.default is inspect.Parameter.empty
        ]

        async def _mcp_tool(**kwargs: Any) -> Any:
            missing = [n for n in required_params if n not in kwargs]
            if missing:
                raise ValueError(f"Missing required parameters: {missing}")
            if guard is not None:
                ask = await _confirm_guarded_operation(guard, kwargs)
                if ask is not None:
                    return ask
            request_context = await _fetch_request_context()
            merged_kwargs = {**inject_kwargs, **kwargs, "_request_context": request_context}
            return await asyncio.to_thread(executor_func, **merged_kwargs)
    else:

        async def _mcp_tool(**kwargs: Any) -> Any:
            if guard is not None:
                ask = await _confirm_guarded_operation(guard, kwargs)
                if ask is not None:
                    return ask
            request_context = await _fetch_request_context()
            merged_kwargs = {**inject_kwargs, **kwargs, "_request_context": request_context}
            return await asyncio.to_thread(executor_func, **merged_kwargs)

    _mcp_tool.__name__ = tool_name
    _mcp_tool.__signature__ = signature  # type: ignore[attr-defined]
    _mcp_tool.__doc__ = tool_description
    _mcp_tool.__annotations__ = annotations

    return _mcp_tool
