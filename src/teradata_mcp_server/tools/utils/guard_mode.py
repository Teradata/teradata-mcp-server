"""Guard-mode helpers for multi-step confirmation flows on destructive operations.

Tools marked with ``destructive_hint=True`` (or specific destructive branches
within a multi-operation tool) can call ``confirm_destructive_operation`` to
require explicit user confirmation, via FastMCP's elicitation API
(``Context.elicit``), before proceeding.

Elicitation is async and only available on ``fastmcp.server.context.Context``.
Tool handlers in this codebase (``handle_*``) are synchronous and run inside
``asyncio.to_thread``, so they cannot call ``ctx.elicit`` directly. The
confirmation must happen in the async tool wrapper, before the sync handler
is dispatched to the thread pool — call ``confirm_destructive_operation``
there and only invoke the handler once it returns without raising.

Example usage pattern:

    from fastmcp.exceptions import ToolError
    from teradata_mcp_server.tools.utils.guard_mode import confirm_destructive_operation

    async def _mcp_tool(ctx: Context, **kwargs) -> Any:
        if kwargs.get("operation") == "delete":
            await confirm_destructive_operation(
                ctx,
                operation_name="Delete Job",
                description=f"Delete job '{kwargs.get('job_name')}'? This is irreversible.",
            )
        return await asyncio.to_thread(handle_bar_manageJob, **kwargs)
"""

from fastmcp.exceptions import ToolError
from fastmcp.server.context import Context
from fastmcp.server.elicitation import AcceptedElicitation, CancelledElicitation, DeclinedElicitation


async def confirm_destructive_operation(
    ctx: Context,
    operation_name: str,
    description: str,
    risk_level: str = "high",
) -> None:
    """Ask the client to confirm a destructive operation before proceeding.

    Raises ``ToolError`` if the user declines, cancels, or answers "no" —
    callers should let this propagate rather than catching it, so the
    operation is aborted and the reason surfaces to the client.

    Args:
        ctx: The active FastMCP request context.
        operation_name: Human-readable name of the operation (e.g. "Delete Job").
        description: Detailed description of what will happen.
        risk_level: "high" or "critical"; only affects the message wording.
    """
    prefix = "⚠️ WARNING" if risk_level == "high" else "🔴 CRITICAL"
    message = f"{prefix}: {operation_name}\n\n{description}\n\nThis action cannot be undone. Confirm to proceed?"

    result = await ctx.elicit(message, response_type=bool)

    if isinstance(result, AcceptedElicitation):
        if result.data:
            return
        raise ToolError(f"{operation_name} was not confirmed — operation cancelled.")
    if isinstance(result, DeclinedElicitation):
        raise ToolError(f"{operation_name} was declined by the user — operation cancelled.")
    if isinstance(result, CancelledElicitation):
        raise ToolError(f"{operation_name} confirmation was cancelled — operation cancelled.")
    raise ToolError(f"{operation_name} confirmation returned an unexpected result — operation cancelled.")
