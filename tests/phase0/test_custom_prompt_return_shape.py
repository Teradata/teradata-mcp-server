#!/usr/bin/env python
"""Unit tests for the return shape of YAML-defined (custom) prompts.

FastMCP (>= the 4.x line this project requires) renders a prompt only when the
function returns ``str``, ``list[Message]`` or ``PromptResult``. A bare ``Message``
is rejected at render time with::

    Prompt must return str, list[Message], or PromptResult, got Message

so every prompt registered through ``make_custom_prompt`` (the ``*_objects.yml``
prompts, with or without parameters) failed on ``prompts/get``. Tools were
unaffected; only prompt rendering broke.
"""

import ast
import asyncio
from pathlib import Path

import pytest
from fastmcp import Client, FastMCP
from fastmcp.prompts import Message
from mcp.types import TextContent

APP = Path(__file__).resolve().parents[2] / "src" / "teradata_mcp_server" / "app.py"


def _render(returns_list: bool):
    mcp = FastMCP("prompt-shape")

    async def _p():
        m = Message(role="user", content=TextContent(type="text", text="hello"))
        return [m] if returns_list else m

    _p.__name__ = "shape_probe"
    mcp.prompt(description="probe")(_p)

    async def go():
        async with Client(mcp) as c:
            return await c.get_prompt("shape_probe")

    return asyncio.run(go())


def test_fastmcp_rejects_a_bare_message():
    """The contract this fix follows: a bare Message does not render."""
    with pytest.raises(Exception, match="got Message"):
        _render(returns_list=False)


def test_fastmcp_renders_a_list_of_messages():
    result = _render(returns_list=True)
    assert [m.content.text for m in result.messages] == ["hello"]


def test_make_custom_prompt_returns_a_list_on_every_branch():
    """Both branches of make_custom_prompt (no parameters / with parameters)."""
    tree = ast.parse(APP.read_text())
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "make_custom_prompt")
    prompt_fns = [n for n in ast.walk(fn)
                  if isinstance(n, ast.AsyncFunctionDef) and n.name.startswith("_dynamic_prompt")]
    assert len(prompt_fns) == 2, "expected one prompt function per branch"
    for pf in prompt_fns:
        returns = [n for n in ast.walk(pf) if isinstance(n, ast.Return) and n.value is not None]
        assert returns, "the prompt function must return its message"
        for r in returns:
            assert isinstance(r.value, ast.List), (
                f"{pf.name} (line {r.lineno}) must return a list of Message, "
                f"not a bare Message")
