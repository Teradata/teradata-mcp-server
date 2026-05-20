"""Verify that tool registrations include the expected ToolAnnotations.

Runs without a live Teradata connection — list_tools is answered from server
metadata before any database query is made.

Usage:
    uv run python tests/verify_tool_annotations.py
"""

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Representative sample: one tool per annotation class.
# Tools from optional modules (bar_, tdml_, tdvs_) are skipped when not loaded.
EXPECTED: dict[str, dict[str, bool]] = {
    # read-only + idempotent (base_ prefix)
    "base_readQuery": {"readOnlyHint": True, "idempotentHint": True},
    # read-only + idempotent (dba_ prefix — all current tools are SELECT-only)
    "dba_tableSpace": {"readOnlyHint": True, "idempotentHint": True},
    # read-only + idempotent (sec_ prefix)
    "sec_userDbPermissions": {"readOnlyHint": True, "idempotentHint": True},
    # destructive (bar_ prefix)
    "bar_manageDsaDiskFileSystem": {"readOnlyHint": False, "destructiveHint": True},
    # per-tool override: tdvs_ prefix default is read-only, but grant/revoke are destructive
    "tdvs_grant_user": {"readOnlyHint": False, "destructiveHint": True},
    "tdvs_revoke_user": {"readOnlyHint": False, "destructiveHint": True},
    # tdvs_ prefix default still applies to non-grant/revoke tools
    "tdvs_similarity": {"readOnlyHint": True, "idempotentHint": True},
    # tdml_ — not read-only but idempotent
    "tdml_KMeans": {"readOnlyHint": False, "idempotentHint": True},
}


async def main() -> None:
    env = {**os.environ, "DATABASE_URI": "teradata://dummy:dummy@localhost:1025/dummy"}

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "teradata_mcp_server"],
        env=env,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            tools = {t.name: t for t in result.tools}

    failures: list[str] = []
    skipped: list[str] = []

    for tool_name, expected_hints in EXPECTED.items():
        if tool_name not in tools:
            skipped.append(tool_name)
            continue

        ann = tools[tool_name].annotations
        for hint, expected_value in expected_hints.items():
            actual = getattr(ann, hint, None) if ann else None
            if actual != expected_value:
                failures.append(
                    f"  {tool_name}.{hint}: expected {expected_value}, got {actual}"
                )

    if skipped:
        print(f"SKIPPED ({len(skipped)} tools not loaded — optional modules):")
        for name in skipped:
            print(f"  {name}")

    if failures:
        print(f"FAIL ({len(failures)} assertion(s)):")
        for f in failures:
            print(f)
        sys.exit(1)
    else:
        verified = len(EXPECTED) - len(skipped)
        print(f"PASS — verified annotations on {verified} tool(s)")


if __name__ == "__main__":
    asyncio.run(main())
