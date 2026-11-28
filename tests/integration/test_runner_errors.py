"""Regression coverage for expected errors in the integration runner."""

import asyncio
from unittest.mock import AsyncMock

from mcp.shared.exceptions import MCPError
from mcp.types import CallToolResult, TextContent

from run_mcp_tests import MCPTestRunner


def _run_with(result=None, error=None):
    runner = MCPTestRunner()
    runner.session = AsyncMock()
    runner.session.call_tool.return_value = result
    runner.session.call_tool.side_effect = error
    case = {
        "name": "masked",
        "parameters": {},
        "expect_error": True,
        "expect_error_excludes": ["private_detail"],
    }
    return asyncio.run(runner.run_test_case("test_tool", case))


def test_expected_protocol_error_is_accepted_when_masked():
    result = _run_with(error=MCPError(code=-32603, message="Database operation failed"))
    assert result["status"] == "PASS"


def test_expected_protocol_error_fails_when_details_leak():
    result = _run_with(error=MCPError(code=-32603, message="private_detail"))
    assert result["status"] == "FAIL"


def test_expected_tool_error_response_is_checked_for_leaks():
    response = CallToolResult(content=[TextContent(type="text", text="private_detail")], is_error=True)
    assert _run_with(result=response)["status"] == "FAIL"


def test_unexpected_exception_is_not_accepted_as_expected_error():
    assert _run_with(error=RuntimeError("connection failed"))["status"] == "FAIL"
