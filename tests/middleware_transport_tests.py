#!/usr/bin/env python3
"""
Unit tests for RequestContextMiddleware transport-path branching.

Verifies that on_request reads transport from ctx.transport at request time
and correctly routes to the stdio fast-path or the HTTP header-extraction path.
No database or running server required.

Usage:
    uv run python tests/middleware_transport_tests.py
"""

import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_middleware():
    from teradata_mcp_server.middleware import RequestContextMiddleware

    logger = MagicMock()
    auth_cache = MagicMock()
    tdconn_supplier = MagicMock()
    return RequestContextMiddleware(
        logger=logger,
        auth_cache=auth_cache,
        tdconn_supplier=tdconn_supplier,
        auth_mode="none",
    )


def _make_context(transport: str | None, fastmcp_context: bool = True):
    """Build a minimal MiddlewareContext-like object."""
    ctx = MagicMock()
    if fastmcp_context:
        ctx.fastmcp_context = MagicMock()
        ctx.fastmcp_context.transport = transport
        ctx.fastmcp_context.session_id = "test-session"
        ctx.fastmcp_context.set_state = AsyncMock()
    else:
        ctx.fastmcp_context = None
    return ctx


class TestMiddlewareTransportBranching(unittest.TestCase):
    def _run(self, coro):
        return asyncio.run(coro)

    def test_stdio_path_skips_http_headers(self):
        """transport='stdio' must not call get_http_headers."""
        mw = _make_middleware()
        context = _make_context("stdio")
        call_next = AsyncMock(return_value=None)

        with patch("teradata_mcp_server.middleware.get_http_headers") as mock_headers:
            self._run(mw.on_request(context, call_next))
            mock_headers.assert_not_called()

        call_next.assert_called_once_with(context)

    def test_http_path_calls_http_headers(self):
        """transport='streamable-http' must call get_http_headers."""
        mw = _make_middleware()
        context = _make_context("streamable-http")
        call_next = AsyncMock(return_value=None)

        with patch("teradata_mcp_server.middleware.get_http_headers", return_value={}) as mock_headers:
            self._run(mw.on_request(context, call_next))
            mock_headers.assert_called_once()

    def test_none_transport_falls_back_to_stdio(self):
        """transport=None (fastmcp_context absent) must take the stdio fast-path."""
        mw = _make_middleware()
        context = _make_context(transport=None, fastmcp_context=False)
        call_next = AsyncMock(return_value=None)

        with patch("teradata_mcp_server.middleware.get_http_headers") as mock_headers:
            self._run(mw.on_request(context, call_next))
            mock_headers.assert_not_called()

        call_next.assert_called_once_with(context)


class TestLifespanStateSupplier(unittest.TestCase):
    """Verify that middleware works correctly when tdconn_supplier is a lambda reading _state."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_lambda_supplier_called_for_basic_auth(self):
        """tdconn_supplier=lambda: _state.tdconn must be callable and return the mock TDConn."""
        from teradata_mcp_server.middleware import RequestContextMiddleware

        # Simulate the _ConnState pattern from app.py
        class _ConnState:
            tdconn = None

        _state = _ConnState()
        mock_tdconn = MagicMock()
        mock_tdconn.validate_auth_header.return_value = "testuser"
        _state.tdconn = mock_tdconn

        logger = MagicMock()
        auth_cache = MagicMock()
        auth_cache.get.return_value = None  # force validation path

        # This mirrors the pattern used in app.py after the lifespan refactor
        mw = RequestContextMiddleware(
            logger=logger,
            auth_cache=auth_cache,
            tdconn_supplier=lambda: _state.tdconn,
            auth_mode="basic",
        )

        context = MagicMock()
        context.fastmcp_context = MagicMock()
        context.fastmcp_context.transport = "streamable-http"
        context.fastmcp_context.session_id = "sess-1"
        context.fastmcp_context.set_state = AsyncMock()

        with patch(
            "teradata_mcp_server.middleware.get_http_headers",
            return_value={"authorization": "Basic dXNlcjpwYXNz"},
        ):
            call_next = AsyncMock(return_value=None)
            self._run(mw.on_request(context, call_next))

        # The supplier must have been called and delegated to the TDConn object
        mock_tdconn.validate_auth_header.assert_called_once()

    def test_lambda_supplier_returns_none_before_lifespan(self):
        """Before lifespan runs, _state.tdconn is None — supplier returns None gracefully."""
        from teradata_mcp_server.middleware import RequestContextMiddleware

        class _ConnState:
            tdconn = None

        _state = _ConnState()
        # tdconn stays None (lifespan not started)

        logger = MagicMock()
        auth_cache = MagicMock()

        mw = RequestContextMiddleware(
            logger=logger,
            auth_cache=auth_cache,
            tdconn_supplier=lambda: _state.tdconn,
            auth_mode="none",
        )

        # stdio path — supplier is not called; just verify the middleware initialises
        context = MagicMock()
        context.fastmcp_context = MagicMock()
        context.fastmcp_context.transport = "stdio"
        context.fastmcp_context.session_id = "sess-2"
        context.fastmcp_context.set_state = AsyncMock()

        call_next = AsyncMock(return_value=None)
        asyncio.run(mw.on_request(context, call_next))
        call_next.assert_called_once_with(context)


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2)
    sys.exit(0 if result.result.wasSuccessful() else 1)
