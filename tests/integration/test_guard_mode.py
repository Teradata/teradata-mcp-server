#!/usr/bin/env python3
"""
Unit tests for guard-mode confirmation flows (Phase 4.4 / issue #407).

Verifies that:
1. confirm_destructive_operation() accepts/rejects based on the elicitation
   result (accepted+True, accepted+False, declined, cancelled) on the
   handshake-era (<= 2025-11-25) protocol, where Context.elicit() pushes a
   standalone request mid-call.
2. On the modern sessionless protocol (2026-07-28, SEP-2577), where
   Context.elicit() is unavailable, confirm_destructive_operation() instead
   raises ConfirmationRequiredError with an InputRequiredResult "ask" on the first
   round, and resolves accept/decline/cancel from ctx.input_responses on a
   retried call.
3. The per-tool guard checks in app.py flag exactly the destructive
   operation branches scoped for confirmation, and leave safe branches
   (list/get/status/etc.) alone.
4. create_mcp_tool()'s guard wiring calls the confirmation flow before
   dispatching to the executor when a guard flags a call, skips it entirely
   (no Context needed) when the guard returns None, and — on the modern
   protocol — returns the InputRequiredResult ask as the tool's result
   instead of raising or dispatching.

Usage:
    uv run python tests/integration/test_guard_mode.py

This test uses mocks to simulate FastMCP elicitation without requiring a
running server, live database connection, or a real MCP client.
"""

import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastmcp.exceptions import ToolError
from fastmcp.server.elicitation import AcceptedElicitation, CancelledElicitation, DeclinedElicitation
from mcp_types import ElicitResult, InputRequiredResult

from teradata_mcp_server.tools.utils.factory import create_mcp_tool
from teradata_mcp_server.tools.utils.guard_mode import ConfirmationRequiredError, confirm_destructive_operation

_MODERN_PROTOCOL = "2026-07-28"


def _modern_ctx(input_responses=None):
    """A mock Context negotiated on the modern sessionless protocol."""
    ctx = MagicMock()
    ctx.request_context.protocol_version = _MODERN_PROTOCOL
    ctx.input_responses = input_responses
    return ctx


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestConfirmDestructiveOperation(unittest.TestCase):
    """Test confirm_destructive_operation() against each elicitation outcome."""

    def test_accepted_true_passes(self):
        ctx = AsyncMock()
        ctx.elicit.return_value = AcceptedElicitation(data=True)
        _run(confirm_destructive_operation(ctx, "Delete Job", "Delete job 'x'."))  # must not raise
        ctx.elicit.assert_awaited_once()

    def test_accepted_false_raises(self):
        ctx = AsyncMock()
        ctx.elicit.return_value = AcceptedElicitation(data=False)
        with self.assertRaises(ToolError):
            _run(confirm_destructive_operation(ctx, "Delete Job", "Delete job 'x'."))

    def test_declined_raises(self):
        ctx = AsyncMock()
        ctx.elicit.return_value = DeclinedElicitation()
        with self.assertRaises(ToolError):
            _run(confirm_destructive_operation(ctx, "Delete Job", "Delete job 'x'."))

    def test_cancelled_raises(self):
        ctx = AsyncMock()
        ctx.elicit.return_value = CancelledElicitation()
        with self.assertRaises(ToolError):
            _run(confirm_destructive_operation(ctx, "Delete Job", "Delete job 'x'."))


class TestConfirmDestructiveOperationModernProtocol(unittest.TestCase):
    """Test confirm_destructive_operation() on the modern sessionless (2026-07-28) era.

    Context.elicit() is unavailable on this era (SEP-2577 removed the
    server-initiated back-channel), so confirmation instead uses the SEP-2322
    multi-round-trip guard pattern: no answer yet -> ask (ConfirmationRequiredError);
    an answer present in ctx.input_responses -> resolve accept/decline/cancel.
    """

    def test_no_prior_response_asks(self):
        ctx = _modern_ctx(input_responses=None)
        with self.assertRaises(ConfirmationRequiredError) as cm:
            _run(confirm_destructive_operation(ctx, "Delete Job", "Delete job 'x'."))
        ask = cm.exception.input_required
        self.assertIsInstance(ask, InputRequiredResult)
        self.assertIn("confirm", ask.input_requests)
        self.assertEqual(ask.request_state, "Delete Job")
        ctx.elicit.assert_not_called()

    def test_accepted_true_passes(self):
        ctx = _modern_ctx(input_responses={"confirm": ElicitResult(action="accept", content={"value": True})})
        _run(confirm_destructive_operation(ctx, "Delete Job", "Delete job 'x'."))  # must not raise

    def test_accepted_false_raises(self):
        ctx = _modern_ctx(input_responses={"confirm": ElicitResult(action="accept", content={"value": False})})
        with self.assertRaises(ToolError):
            _run(confirm_destructive_operation(ctx, "Delete Job", "Delete job 'x'."))

    def test_declined_raises(self):
        ctx = _modern_ctx(input_responses={"confirm": ElicitResult(action="decline")})
        with self.assertRaises(ToolError):
            _run(confirm_destructive_operation(ctx, "Delete Job", "Delete job 'x'."))

    def test_cancelled_raises(self):
        ctx = _modern_ctx(input_responses={"confirm": ElicitResult(action="cancel")})
        with self.assertRaises(ToolError):
            _run(confirm_destructive_operation(ctx, "Delete Job", "Delete job 'x'."))


class TestPerToolGuardChecks(unittest.TestCase):
    """Test the app.py guard functions flag exactly the scoped destructive operations."""

    @classmethod
    def setUpClass(cls):
        from teradata_mcp_server import app

        cls.app = app

    def test_bar_manageJob_gates_run_and_delete_only(self):
        guard = self.app._GUARD_CHECKS["bar_manageJob"]
        self.assertIsNotNone(guard({"operation": "run", "job_name": "j1"}))
        self.assertIsNotNone(guard({"operation": "delete", "job_name": "j1"}))
        for safe_op in ("list", "get", "create", "update", "status", "retire", "unretire"):
            self.assertIsNone(guard({"operation": safe_op, "job_name": "j1"}), safe_op)

    def test_bar_manageDsaDiskFileSystem_gates_delete_all_and_remove_only(self):
        guard = self.app._GUARD_CHECKS["bar_manageDsaDiskFileSystem"]
        self.assertIsNotNone(guard({"operation": "delete_all"}))
        self.assertIsNotNone(guard({"operation": "remove"}))
        for safe_op in ("list", "config"):
            self.assertIsNone(guard({"operation": safe_op}), safe_op)

    def test_bar_manageMediaServer_gates_delete_only(self):
        guard = self.app._GUARD_CHECKS["bar_manageMediaServer"]
        self.assertIsNotNone(guard({"operation": "delete", "server_name": "ms1"}))
        for safe_op in ("list", "get", "add", "list_consumers", "list_consumers_by_server"):
            self.assertIsNone(guard({"operation": safe_op}), safe_op)

    def test_bar_manageTeradataSystem_gates_delete_system_only(self):
        guard = self.app._GUARD_CHECKS["bar_manageTeradataSystem"]
        self.assertIsNotNone(guard({"operation": "delete_system", "system_name": "sys1"}))
        for safe_op in (
            "list_systems",
            "get_system",
            "config_system",
            "enable_system",
            "list_consumers",
            "get_consumer",
        ):
            self.assertIsNone(guard({"operation": safe_op}), safe_op)

    def test_bar_manageDiskFileTargetGroup_gates_delete_only(self):
        guard = self.app._GUARD_CHECKS["bar_manageDiskFileTargetGroup"]
        self.assertIsNotNone(guard({"operation": "delete", "target_group_name": "tg1"}))
        for safe_op in ("list", "get", "create", "enable", "disable"):
            self.assertIsNone(guard({"operation": safe_op}), safe_op)

    def test_tdvs_grant_revoke_destroy_always_gated(self):
        self.assertIsNotNone(
            self.app._GUARD_CHECKS["tdvs_grant_user_permission"](
                {"vs_name": "v", "user_name": "u", "permission": "USER"}
            )
        )
        self.assertIsNotNone(
            self.app._GUARD_CHECKS["tdvs_revoke_user_permission"](
                {"vs_name": "v", "user_name": "u", "permission": "USER"}
            )
        )
        self.assertIsNotNone(self.app._GUARD_CHECKS["tdvs_destroy"]({"vs_name": "v"}))

    def test_tdvs_annotations_fixed(self):
        # Regression guard for the naming-mismatch bug: these must resolve via
        # exact match, not fall through to the tdvs_ prefix's read_only default.
        for tool_name in ("tdvs_grant_user_permission", "tdvs_revoke_user_permission", "tdvs_destroy"):
            ann = self.app._annotations_for(tool_name)
            self.assertFalse(ann.read_only_hint, tool_name)
            self.assertTrue(ann.destructive_hint, tool_name)


class TestCreateMcpToolGuardWiring(unittest.TestCase):
    """Test that create_mcp_tool() invokes confirmation only when the guard flags a call."""

    def _build_tool(self, guard):
        import inspect

        executor = unittest.mock.Mock(return_value="ok")
        sig = inspect.Signature(parameters=[inspect.Parameter("operation", inspect.Parameter.POSITIONAL_OR_KEYWORD)])
        tool = create_mcp_tool(
            executor_func=executor,
            signature=sig,
            tool_name="fake_tool",
            guard=guard,
        )
        return tool, executor

    def test_guard_none_skips_confirmation(self):
        # A guard returning None must never trigger elicitation, even though
        # _fetch_request_context() still calls get_context() unconditionally
        # for its own (unrelated) purpose of reading request-scoped state.
        tool, executor = self._build_tool(guard=lambda kwargs: None)
        fake_ctx = AsyncMock()
        with patch("fastmcp.server.dependencies.get_context", return_value=fake_ctx):
            result = _run(tool(operation="list"))
        fake_ctx.elicit.assert_not_called()
        executor.assert_called_once()
        self.assertEqual(result, "ok")

    def test_guard_flagged_confirms_before_dispatch(self):
        tool, executor = self._build_tool(guard=lambda kwargs: ("Delete Thing", "Delete it."))
        fake_ctx = AsyncMock()
        fake_ctx.elicit.return_value = AcceptedElicitation(data=True)
        with patch("fastmcp.server.dependencies.get_context", return_value=fake_ctx):
            result = _run(tool(operation="delete"))
        fake_ctx.elicit.assert_awaited_once()
        executor.assert_called_once()
        self.assertEqual(result, "ok")

    def test_guard_flagged_and_declined_blocks_dispatch(self):
        tool, executor = self._build_tool(guard=lambda kwargs: ("Delete Thing", "Delete it."))
        fake_ctx = AsyncMock()
        fake_ctx.elicit.return_value = DeclinedElicitation()
        with (
            patch("fastmcp.server.dependencies.get_context", return_value=fake_ctx),
            self.assertRaises(ToolError),
        ):
            _run(tool(operation="delete"))
        executor.assert_not_called()

    def test_guard_flagged_but_no_context_available_blocks_dispatch(self):
        tool, executor = self._build_tool(guard=lambda kwargs: ("Delete Thing", "Delete it."))
        with (
            patch("fastmcp.server.dependencies.get_context", side_effect=RuntimeError("no context")),
            self.assertRaises(ToolError),
        ):
            _run(tool(operation="delete"))
        executor.assert_not_called()

    def test_guard_flagged_modern_protocol_returns_ask_without_dispatch(self):
        # On the modern sessionless era, the first leg of a guarded call must
        # return the InputRequiredResult ask as the tool's *result* — not raise,
        # not dispatch — since the client is expected to retry the same call.
        tool, executor = self._build_tool(guard=lambda kwargs: ("Delete Thing", "Delete it."))
        fake_ctx = _modern_ctx(input_responses=None)
        with patch("fastmcp.server.dependencies.get_context", return_value=fake_ctx):
            result = _run(tool(operation="delete"))
        self.assertIsInstance(result, InputRequiredResult)
        self.assertIn("confirm", result.input_requests)
        executor.assert_not_called()

    def test_guard_flagged_modern_protocol_accepted_dispatches(self):
        # On a retried call carrying an accepted response, the wrapper proceeds
        # to the executor exactly as the handshake-era accept path does.
        tool, executor = self._build_tool(guard=lambda kwargs: ("Delete Thing", "Delete it."))
        fake_ctx = _modern_ctx(input_responses={"confirm": ElicitResult(action="accept", content={"value": True})})
        with patch("fastmcp.server.dependencies.get_context", return_value=fake_ctx):
            result = _run(tool(operation="delete"))
        executor.assert_called_once()
        self.assertEqual(result, "ok")

    def test_guard_flagged_modern_protocol_declined_blocks_dispatch(self):
        tool, executor = self._build_tool(guard=lambda kwargs: ("Delete Thing", "Delete it."))
        fake_ctx = _modern_ctx(input_responses={"confirm": ElicitResult(action="decline")})
        with (
            patch("fastmcp.server.dependencies.get_context", return_value=fake_ctx),
            self.assertRaises(ToolError),
        ):
            _run(tool(operation="delete"))
        executor.assert_not_called()


if __name__ == "__main__":
    result = unittest.main(exit=False)
    sys.exit(0 if result.result.wasSuccessful() else 1)
