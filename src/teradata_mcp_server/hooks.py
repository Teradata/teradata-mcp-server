from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class ToolCallContext:
    """Snapshot of per-invocation state passed to every server hook."""

    tool_name: str
    kwargs: dict  # keyword args the tool was called with (conn/tool_name already removed)
    request_context: object  # RequestContext from middleware; typed as object to avoid circular import
    engine: object  # sqlalchemy.engine.Engine tied to this request
    profile_name: str | None
    db_user: str | None


@dataclass
class ServerHooks:
    """Optional extension points called around each tool invocation.

    Set any field to a callable to intercept that event.  All hooks are
    synchronous and run inside the worker thread that executes the tool.
    Exceptions raised inside a hook are caught and logged; they never
    interrupt tool execution.

    Example — minimal hooks module (save as ``my_hooks.py``, then set
    ``HOOKS_MODULE=/path/to/my_hooks.py`` or ``--hooks_module``):

        from teradata_mcp_server.hooks import ServerHooks, ToolCallContext

        def _on_tool_call(ctx: ToolCallContext) -> None:
            print(ctx.tool_name, ctx.kwargs)

        def get_hooks() -> ServerHooks:
            return ServerHooks(on_tool_call=_on_tool_call)
    """

    on_tool_call: Callable[[ToolCallContext], None] | None = None
    on_tool_result: Callable[[ToolCallContext, object], None] | None = None
    on_tool_error: Callable[[ToolCallContext, Exception], None] | None = None
