"""
Dump live MCP tool descriptions to results/live_descriptions_<module>.json.

Usage:
    uv run python backup/inspect_tools.py                  # all base tools
    uv run python backup/inspect_tools.py --module base    # explicit module filter
    uv run python backup/inspect_tools.py --all-modules    # every module on the server

Output: results/live_descriptions_<module>.json  (one file per module)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

load_dotenv()

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
DEFAULT_MODULES = {"base"}


async def fetch_tools(mcp_url: str) -> list[dict]:
    async with streamablehttp_client(mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "inputSchema": t.inputSchema,
                }
                for t in result.tools
            ]


def group_by_module(tools: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for tool in tools:
        module = tool["name"].split("_")[0]
        grouped.setdefault(module, []).append(tool)
    return grouped


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump live MCP tool descriptions.")
    parser.add_argument("--module", default=None, help="Filter to a single module prefix (e.g. base)")
    parser.add_argument("--all-modules", action="store_true", help="Include all modules (default: base only)")
    args = parser.parse_args()

    mcp_url = os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:8001/mcp")
    print(f"Fetching tools from {mcp_url} ...")

    tools = asyncio.run(fetch_tools(mcp_url))
    grouped = group_by_module(tools)

    if args.module:
        target_modules = {args.module}
    elif args.all_modules:
        target_modules = set(grouped.keys())
    else:
        target_modules = DEFAULT_MODULES

    RESULTS_DIR.mkdir(exist_ok=True)

    for module, module_tools in sorted(grouped.items()):
        if module not in target_modules:
            continue

        out_path = RESULTS_DIR / f"live_descriptions_{module}.json"
        payload = {
            "module": module,
            "mcp_url": mcp_url,
            "tool_count": len(module_tools),
            "tools": module_tools,
        }
        out_path.write_text(json.dumps(payload, indent=2))
        print(f"  [{module}] {len(module_tools)} tools → {out_path}")

    print("Done.")


if __name__ == "__main__":
    main()
