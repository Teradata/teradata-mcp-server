#!/usr/bin/env python3
"""
Integration test for set_state/get_state semantics under v4 sessionless protocol.

Verifies that:
1. RequestContext set in middleware via set_state("request_context", rc) is retrievable
   by tool handlers via get_state("request_context")
2. State is scoped within a single request (not carried across requests)
3. The within-request flow works correctly under sessionless model

Usage:
    uv run python tests/integration/test_set_state_sessionless.py

This test uses mocks to simulate FastMCP v4 context behavior without requiring
a running server or database connection.
"""

import asyncio
import sys
import unittest
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch


@dataclass
class MockRequestContext:
    """Minimal RequestContext for testing."""

    request_id: str
    session_id: str
    headers: dict
    assume_user: str | None = None


class SessionlessContextSimulator:
    """Simulates v4 FastMCP context with request-scoped state (no session persistence)."""

    def __init__(self):
        self._request_state: dict = {}
        self.transport = "streamable-http"
        self.request_id = "test-req-123"
        self.session_id = "test-sess-123"

    async def set_state(self, key: str, value, serializable: bool = True):
        """Store state in request-scoped storage."""
        self._request_state[key] = value

    def get_state(self, key: str):
        """Retrieve state from request-scoped storage."""
        return self._request_state.get(key)

    def clear_state(self):
        """Clear state (simulates end of request)."""
        self._request_state.clear()


class TestSetStateSessionlessSemantics(unittest.TestCase):
    """Test set_state/get_state behavior under v4 sessionless protocol."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_middleware_sets_state_tool_gets_state_same_request(self):
        """Within a single request, middleware set_state is visible to tool get_state."""
        from teradata_mcp_server.middleware import RequestContextMiddleware, RequestContext

        # Simulate v4 sessionless context
        ctx_sim = SessionlessContextSimulator()

        # Create middleware
        logger = MagicMock()
        auth_cache = MagicMock()
        tdconn_supplier = MagicMock()
        mw = RequestContextMiddleware(
            logger=logger,
            auth_cache=auth_cache,
            tdconn_supplier=tdconn_supplier,
            auth_mode="none",
        )

        # Simulate a request through middleware
        middleware_context = MagicMock()
        middleware_context.type = "request"  # v4: distinguish request from notification
        middleware_context.fastmcp_context = ctx_sim
        call_next = AsyncMock()

        with patch(
            "teradata_mcp_server.middleware.get_http_headers",
            return_value={"x-correlation-id": "corr-123"},
        ):
            # Run middleware on_request
            self._run(mw.on_request(middleware_context, call_next))

        # After middleware runs, RequestContext should be in the context state
        stored_rc = ctx_sim.get_state("request_context")
        self.assertIsNotNone(stored_rc, "RequestContext should be stored after middleware.on_request")
        self.assertIsInstance(stored_rc, RequestContext)
        self.assertEqual(stored_rc.correlation_id, "corr-123")
        self.assertEqual(stored_rc.request_id, "test-req-123")

    def test_state_not_carried_across_requests(self):
        """State from first request should not be visible in second request (sessionless isolation)."""
        from teradata_mcp_server.middleware import RequestContextMiddleware

        logger = MagicMock()
        auth_cache = MagicMock()
        tdconn_supplier = MagicMock()
        mw = RequestContextMiddleware(
            logger=logger,
            auth_cache=auth_cache,
            tdconn_supplier=tdconn_supplier,
            auth_mode="none",
        )

        # First request
        ctx_sim_1 = SessionlessContextSimulator()
        ctx_sim_1.request_id = "req-001"
        middleware_context_1 = MagicMock()
        middleware_context_1.type = "request"
        middleware_context_1.fastmcp_context = ctx_sim_1
        call_next = AsyncMock()

        with patch("teradata_mcp_server.middleware.get_http_headers", return_value={}):
            self._run(mw.on_request(middleware_context_1, call_next))

        stored_rc_1 = ctx_sim_1.get_state("request_context")
        self.assertIsNotNone(stored_rc_1)
        self.assertEqual(stored_rc_1.request_id, "req-001")

        # Second request with a new context (new sessionless flow)
        ctx_sim_2 = SessionlessContextSimulator()
        ctx_sim_2.request_id = "req-002"
        middleware_context_2 = MagicMock()
        middleware_context_2.type = "request"
        middleware_context_2.fastmcp_context = ctx_sim_2

        with patch("teradata_mcp_server.middleware.get_http_headers", return_value={}):
            self._run(mw.on_request(middleware_context_2, call_next))

        # Second request should have its own state, not carry over first request's state
        stored_rc_2 = ctx_sim_2.get_state("request_context")
        self.assertIsNotNone(stored_rc_2)
        self.assertEqual(stored_rc_2.request_id, "req-002")

        # Verify isolation: first request's state is not in second context
        self.assertNotEqual(stored_rc_1.request_id, stored_rc_2.request_id)

    def test_on_request_skips_non_request_messages(self):
        """v4: on_request fires for all message types; guard must skip notifications."""
        from teradata_mcp_server.middleware import RequestContextMiddleware

        logger = MagicMock()
        auth_cache = MagicMock()
        tdconn_supplier = MagicMock()
        mw = RequestContextMiddleware(
            logger=logger,
            auth_cache=auth_cache,
            tdconn_supplier=tdconn_supplier,
            auth_mode="none",
        )

        # Simulate a notification message (type != "request")
        ctx_sim = SessionlessContextSimulator()
        middleware_context = MagicMock()
        middleware_context.type = "notification"  # not a request
        middleware_context.fastmcp_context = ctx_sim
        call_next = AsyncMock(return_value="passthrough")

        result = self._run(mw.on_request(middleware_context, call_next))

        # Should pass through without processing
        call_next.assert_called_once()
        self.assertEqual(result, "passthrough")

        # No RequestContext should be set for notifications
        stored_rc = ctx_sim.get_state("request_context")
        self.assertIsNone(stored_rc, "RequestContext should NOT be set for non-request messages")

    def test_missing_type_field_defaults_to_request(self):
        """Guard gracefully handles missing type field by defaulting to 'request'."""
        from teradata_mcp_server.middleware import RequestContextMiddleware

        logger = MagicMock()
        auth_cache = MagicMock()
        tdconn_supplier = MagicMock()
        mw = RequestContextMiddleware(
            logger=logger,
            auth_cache=auth_cache,
            tdconn_supplier=tdconn_supplier,
            auth_mode="none",
        )

        # Context with no type attribute
        ctx_sim = SessionlessContextSimulator()
        middleware_context = MagicMock(spec=[])  # No attributes at all
        middleware_context.fastmcp_context = ctx_sim
        call_next = AsyncMock()

        with patch("teradata_mcp_server.middleware.get_http_headers", return_value={}):
            self._run(mw.on_request(middleware_context, call_next))

        # Should still process the request (default to "request")
        call_next.assert_called_once()
        stored_rc = ctx_sim.get_state("request_context")
        self.assertIsNotNone(stored_rc, "Should process as request when type is missing")


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2)
    sys.exit(0 if result.result.wasSuccessful() else 1)
