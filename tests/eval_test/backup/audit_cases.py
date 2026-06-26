"""
Audit eval case coverage: ambiguous tool pairs and (optionally) live MCP tool list.

Usage:
    uv run python backup/audit_cases.py                         # ambiguous pairs, all priority modules
    uv run python backup/audit_cases.py --module base           # one module
    uv run python backup/audit_cases.py --strict                # exit 1 on pair gaps (offline, CI-safe)
    uv run python backup/audit_cases.py --strict --live-mcp     # also diff against running MCP server
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CASES_DIR = Path(__file__).resolve().parent.parent / "cases"

IN_SCOPE_MODULES = frozenset({"base", "dba", "sec", "qlty", "chat", "plot", "tmpl"})
PRIORITY_MODULES = frozenset({"base", "dba", "sec", "qlty"})
DEFAULT_AUDIT_MODULES = ("base", "dba", "sec", "qlty")

# Tool pairs whose descriptions should be distinct; each needs ≥1 ambiguous_selection case.
AMBIGUOUS_PAIRS: dict[str, list[tuple[str, str]]] = {
    "base": [
        ("base_readQuery", "base_tablePreview"),
        ("base_tableDDL", "base_columnMetadata"),
        ("base_tableList", "base_databaseList"),
        ("base_saveDDL", "base_tableDDL"),
        ("base_tableAffinity", "base_tableUsage"),
        ("base_columnDescription", "base_columnMetadata"),
    ],
    "dba": [
        ("dba_tableSpace", "dba_databaseSpace"),
        ("dba_databaseSpace", "dba_systemSpace"),
        ("dba_tableSqlList", "dba_userSqlList"),
        ("dba_tableUsageImpact", "dba_resusageSummary"),
        ("dba_tableUsageImpact", "dba_sessionInfo"),
        ("dba_userDelay", "dba_flowControl"),
    ],
    "sec": [
        ("sec_userDbPermissions", "sec_userRoles"),
        ("sec_userDbPermissions", "sec_rolePermissions"),
        ("sec_userRoles", "sec_rolePermissions"),
    ],
    "qlty": [
        ("qlty_missingValues", "qlty_rowsWithMissingValues"),
        ("qlty_standardDeviation", "qlty_univariateStatistics"),
        ("qlty_columnSummary", "qlty_univariateStatistics"),
    ],
}


def get_module(tool_name: str) -> str | None:
    prefix = tool_name.split("_")[0]
    return prefix if prefix in IN_SCOPE_MODULES else None


def load_cases(module: str) -> list[dict]:
    path = CASES_DIR / f"{module}.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [c for c in data.get("cases", []) if "id" in c]


def tools_referenced_in_cases(cases: list[dict]) -> set[str]:
    names: set[str] = set()
    for case in cases:
        for block in case.get("expected_tools", []):
            names.add(block["name"])
        for turn in case.get("turns", []):
            for block in turn.get("expected_tools", []):
                names.add(block["name"])
    return names


def happy_path_tools(cases: list[dict]) -> set[str]:
    names: set[str] = set()
    for case in cases:
        if case.get("type") != "happy_path":
            continue
        for block in case.get("expected_tools", []):
            names.add(block["name"])
    return names


def covered_ambiguous_pairs(module: str, cases: list[dict]) -> set[frozenset[str]]:
    pairs = AMBIGUOUS_PAIRS.get(module, [])
    if not pairs:
        return set()

    covered: set[frozenset[str]] = set()
    for case in cases:
        if case.get("type") != "ambiguous_selection":
            continue
        expected_tools = case.get("expected_tools", [])
        if not expected_tools:
            continue
        winner = expected_tools[0]["name"]
        case_id = case.get("id", "")
        description = case.get("description", "")

        for tool_a, tool_b in pairs:
            pair = frozenset({tool_a, tool_b})
            if winner not in pair:
                continue
            loser = tool_b if winner == tool_a else tool_a
            loser_token = loser.split("_", 1)[-1]
            if loser_token in case_id or loser in description:
                covered.add(pair)

    return covered


def audit_ambiguous_pair_gaps(module: str, cases: list[dict]) -> list[str]:
    pairs = AMBIGUOUS_PAIRS.get(module, [])
    if not pairs:
        return []

    covered = covered_ambiguous_pairs(module, cases)
    gaps: list[str] = []
    happy_tools = happy_path_tools(cases)

    for tool_a, tool_b in pairs:
        pair = frozenset({tool_a, tool_b})
        if pair not in covered:
            gaps.append(f"  missing ambiguous case: {tool_a} vs {tool_b}")

    for tool_a, tool_b in pairs:
        for tool in (tool_a, tool_b):
            if tool not in happy_tools:
                gaps.append(f"  missing happy_path for tool involved in pair: {tool}")

    return gaps


def audit_live_tool_gaps(
    module: str,
    live_tools: set[str],
    cases: list[dict],
    *,
    require_happy_path: bool,
) -> list[str]:
    gaps: list[str] = []
    happy_tools = happy_path_tools(cases)
    referenced = tools_referenced_in_cases(cases)

    if require_happy_path:
        for tool in sorted(live_tools):
            if tool not in happy_tools:
                gaps.append(f"  missing happy_path for live tool: {tool}")

    for tool in sorted(referenced):
        if tool not in live_tools:
            gaps.append(f"  stale tool name in cases (not on MCP server): {tool}")

    extra_live = live_tools - referenced
    if extra_live and not require_happy_path:
        for tool in sorted(extra_live):
            if tool not in happy_tools:
                gaps.append(f"  note: live tool has no cases yet: {tool}")

    return gaps


async def fetch_tools_by_module(mcp_url: str) -> dict[str, set[str]]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()

    by_module: dict[str, set[str]] = {module: set() for module in IN_SCOPE_MODULES}
    for tool in result.tools:
        module = get_module(tool.name)
        if module:
            by_module[module].add(tool.name)
    return by_module


def audit_module(
    module: str,
    *,
    live_tools: set[str] | None = None,
    check_pairs: bool = True,
    check_live: bool = False,
) -> list[str]:
    cases = load_cases(module)
    gaps: list[str] = []

    if check_pairs:
        gaps.extend(audit_ambiguous_pair_gaps(module, cases))

    if check_live and live_tools is not None:
        require_happy = module in PRIORITY_MODULES
        gaps.extend(
            audit_live_tool_gaps(
                module,
                live_tools,
                cases,
                require_happy_path=require_happy,
            )
        )

    return gaps


def resolve_modules(module: str | None, live_mcp: bool) -> list[str]:
    if module:
        return [module]
    if live_mcp:
        return sorted(IN_SCOPE_MODULES)
    return list(DEFAULT_AUDIT_MODULES)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit eval case coverage")
    parser.add_argument("--module", help="Audit one module only")
    parser.add_argument(
        "--live-mcp",
        action="store_true",
        help="Diff cases against tools returned by the running MCP server",
    )
    parser.add_argument(
        "--skip-pairs",
        action="store_true",
        help="Skip ambiguous pair checks (live MCP diff only)",
    )
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any gaps found")
    args = parser.parse_args()

    modules = resolve_modules(args.module, args.live_mcp)
    live_by_module: dict[str, set[str]] | None = None

    if args.live_mcp:
        mcp_url = os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:8001/mcp")
        print(f"Connecting to MCP server at {mcp_url} ...")
        try:
            live_by_module = asyncio.run(fetch_tools_by_module(mcp_url))
            total = sum(len(tools) for tools in live_by_module.values())
            print(f"Found {total} in-scope tools across {len(IN_SCOPE_MODULES)} modules\n")
        except Exception as exc:
            print(f"ERROR: could not connect to MCP server: {exc}", file=sys.stderr)
            sys.exit(1)

    any_gaps = False
    check_pairs = not args.skip_pairs

    for module in modules:
        live_tools = live_by_module.get(module, set()) if live_by_module else None
        gaps = audit_module(
            module,
            live_tools=live_tools,
            check_pairs=check_pairs and module in AMBIGUOUS_PAIRS,
            check_live=args.live_mcp,
        )

        print(f"[{module}]")
        if not gaps:
            if args.live_mcp and live_tools is not None:
                print(f"  OK — {len(live_tools)} live tool(s), cases in sync")
            elif check_pairs and module in AMBIGUOUS_PAIRS:
                print("  OK — all registered ambiguous pairs covered")
            else:
                print("  OK")
        else:
            any_gaps = True
            print("  GAPS:")
            for gap in gaps:
                print(gap)
        print()

    if any_gaps and args.strict:
        sys.exit(1)

    if not any_gaps:
        print("Audit passed.")


if __name__ == "__main__":
    main()
