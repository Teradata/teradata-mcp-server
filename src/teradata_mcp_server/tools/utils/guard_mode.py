"""Guard-mode helpers for multi-step confirmation flows on destructive operations.

Tools marked with ``destructive_hint=True`` (or specific destructive branches
within a multi-operation tool) can call ``confirm_destructive_operation`` to
require explicit user confirmation before proceeding.

Two MCP protocol eras need two different confirmation mechanisms, and this
module picks the right one per-call based on the active request's negotiated
protocol version:

- **Handshake era** (protocol <= 2025-11-25): the server can push a standalone
  ``elicitation/create`` request mid-call and block on the reply.
  ``Context.elicit`` supports this directly.
- **Modern / sessionless era** (2026-07-28, SEP-2577): there is no
  server-initiated back-channel, so ``Context.elicit`` raises ``ToolError``
  unconditionally on this era. Confirmation instead uses the stateless
  multi-round-trip guard pattern (SEP-2322): the tool call's first leg
  returns an ``InputRequiredResult`` asking the question, and the client
  resubmits the *same* tool call carrying the answer in
  ``ctx.input_responses`` / ``ctx.request_state``.

Tool handlers in this codebase (``handle_*``) are synchronous and run inside
``asyncio.to_thread``, so confirmation must happen in the async tool wrapper,
before the sync handler is dispatched to the thread pool. On the modern era's
"ask" leg there is no handler dispatch at all yet — ``confirm_destructive_operation``
signals that by raising ``ConfirmationRequiredError``, which the wrapper (see
``tools/utils/factory.py``) catches and returns as the tool's result instead
of an error, since asking is a legitimate leg of the call, not a failure.

Example usage pattern:

    from teradata_mcp_server.tools.utils.guard_mode import (
        ConfirmationRequiredError,
        confirm_destructive_operation,
    )

    async def _mcp_tool(ctx: Context, **kwargs) -> Any:
        if kwargs.get("operation") == "delete":
            try:
                await confirm_destructive_operation(
                    ctx,
                    operation_name="Delete Job",
                    description=f"Delete job '{kwargs.get('job_name')}'? This is irreversible.",
                )
            except ConfirmationRequiredError as ask:
                return ask.input_required
        return await asyncio.to_thread(handle_bar_manageJob, **kwargs)
"""

from fastmcp.exceptions import ToolError
from fastmcp.server.context import Context
from fastmcp.server.elicitation import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
    handle_elicit_accept,
    parse_elicit_response_type,
)
from mcp_types import ElicitRequest, ElicitRequestFormParams, ElicitResult, InputRequiredResult
from mcp_types.version import MODERN_PROTOCOL_VERSIONS

_CONFIRM_KEY = "confirm"


class ConfirmationRequiredError(Exception):
    """Signals that a modern-era guarded call must ask before proceeding.

    Carries the ``InputRequiredResult`` (SEP-2322) the caller should return
    as-is from the tool wrapper — this is a normal stateless leg of the call,
    not an error condition, so it must not be surfaced as a raised ToolError.
    """

    def __init__(self, input_required: InputRequiredResult) -> None:
        super().__init__("confirmation required")
        self.input_required = input_required


def _is_modern_protocol(ctx: Context) -> bool:
    """True when the active request negotiated the sessionless 2026-07-28 era."""
    rc = ctx.request_context
    return rc is not None and rc.protocol_version in MODERN_PROTOCOL_VERSIONS


def _confirmation_message(operation_name: str, description: str, risk_level: str) -> str:
    prefix = "⚠️ WARNING" if risk_level == "high" else "🔴 CRITICAL"
    return f"{prefix}: {operation_name}\n\n{description}\n\nThis action cannot be undone. Confirm to proceed?"


def _build_confirmation_ask(operation_name: str, description: str, risk_level: str) -> InputRequiredResult:
    message = _confirmation_message(operation_name, description, risk_level)
    schema = parse_elicit_response_type(bool).schema
    return InputRequiredResult(
        input_requests={
            _CONFIRM_KEY: ElicitRequest(params=ElicitRequestFormParams(message=message, requested_schema=schema))
        },
        request_state=operation_name,
    )


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

    On the modern sessionless protocol era, raises ``ConfirmationRequiredError``
    instead when no answer has been given yet — the caller must return its
    ``.input_required`` payload as the tool's result rather than treating it
    as a failure (see module docstring).

    Args:
        ctx: The active FastMCP request context.
        operation_name: Human-readable name of the operation (e.g. "Delete Job").
        description: Detailed description of what will happen.
        risk_level: "high" or "critical"; only affects the message wording.
    """
    if _is_modern_protocol(ctx):
        await _confirm_via_guard_pattern(ctx, operation_name, description, risk_level)
        return

    message = _confirmation_message(operation_name, description, risk_level)
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


async def _confirm_via_guard_pattern(
    ctx: Context,
    operation_name: str,
    description: str,
    risk_level: str,
) -> None:
    """SEP-2322 multi-round-trip confirmation for the modern sessionless era."""
    responses = ctx.input_responses
    response = responses.get(_CONFIRM_KEY) if responses else None

    if response is None:
        raise ConfirmationRequiredError(_build_confirmation_ask(operation_name, description, risk_level))

    if not isinstance(response, ElicitResult):
        raise ToolError(f"{operation_name} confirmation returned an unexpected result — operation cancelled.")

    if response.action == "accept":
        config = parse_elicit_response_type(bool)
        accepted = handle_elicit_accept(config, response.content)
        if accepted.data:
            return
        raise ToolError(f"{operation_name} was not confirmed — operation cancelled.")
    if response.action == "decline":
        raise ToolError(f"{operation_name} was declined by the user — operation cancelled.")
    if response.action == "cancel":
        raise ToolError(f"{operation_name} confirmation was cancelled — operation cancelled.")
    raise ToolError(f"{operation_name} confirmation returned an unexpected result — operation cancelled.")
