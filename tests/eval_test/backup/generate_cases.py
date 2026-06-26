"""
Bootstrap generator: connects to the MCP server, reads tool descriptions,
and asks Bedrock Claude to draft one happy_path test case per tool.

Usage:
    uv run python backup/generate_cases.py                  # all in-scope modules
    uv run python backup/generate_cases.py --module base    # one module only
    uv run python backup/generate_cases.py --dry-run        # print without writing
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import boto3
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

load_dotenv()

CASES_DIR = Path(__file__).resolve().parent.parent / "cases"
IN_SCOPE_MODULES = {"base", "dba", "sec", "qlty", "chat", "plot", "tmpl"}

DRAFT_PROMPT = """\
You are building an eval suite for an MCP tool server connected to a Teradata database.

Below is the definition of one MCP tool:

Name: {name}
Description: {description}
Input schema: {schema}

Write ONE natural language prompt that a business user might type to invoke this tool.
Rules:
- Do NOT copy phrases directly from the tool description — use different vocabulary.
- Use concrete but generic values (e.g. a real-sounding database name like "Sales" or "HR").
- The prompt should be unambiguous: it should clearly call for THIS tool, not a different one.
- Keep it to one or two sentences.

Also provide the expected parameter values the tool should be called with.
Use realistic placeholder values where the actual value depends on environment.

Respond with valid JSON only — no markdown, no explanation:
{{
  "input": "<the user prompt>",
  "expected_params": {{<param_name>: <value>, ...}}
}}
"""


def get_module(tool_name: str) -> str | None:
    prefix = tool_name.split("_")[0]
    return prefix if prefix in IN_SCOPE_MODULES else None


def make_bedrock_client():
    region = os.environ.get("AWS_REGION", "us-east-1")
    return boto3.client("bedrock-runtime", region_name=region)


def draft_case(tool, bedrock_client, model_id: str) -> dict | None:
    prompt = DRAFT_PROMPT.format(
        name=tool.name,
        description=tool.description or "(no description)",
        schema=json.dumps(tool.inputSchema, indent=2),
    )
    try:
        response = bedrock_client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
        )
        text = response["output"]["message"]["content"][0]["text"].strip()
        # Extract JSON even if there's surrounding whitespace or markdown fences
        start = text.index("{")
        end = text.rindex("}") + 1
        parsed = json.loads(text[start:end])
        return {
            "id": f"{tool.name}_happy",
            "type": "happy_path",
            "description": f"Auto-generated happy path for {tool.name}",
            "input": parsed["input"],
            "expected_tools": [
                {"name": tool.name, "params": parsed.get("expected_params", {})}
            ],
        }
    except Exception as exc:
        print(f"  WARNING: could not generate case for {tool.name}: {exc}", file=sys.stderr)
        return None


async def collect_tools(mcp_url: str) -> list:
    async with streamablehttp_client(mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return result.tools


def load_existing(module: str) -> list[dict]:
    path = CASES_DIR / f"{module}.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [c for c in data.get("cases", []) if "id" in c]


def write_cases(module: str, cases: list[dict]) -> None:
    path = CASES_DIR / f"{module}.json"
    path.write_text(json.dumps({"module": module, "cases": cases}, indent=2) + "\n")
    print(f"  Wrote {len(cases)} cases → {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate happy_path eval cases from live MCP tool descriptions")
    parser.add_argument("--module", help="Only generate for this module (default: all in-scope)")
    parser.add_argument("--dry-run", action="store_true", help="Print generated cases without writing to disk")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing happy_path cases (default: skip if already present)")
    args = parser.parse_args()

    mcp_url = os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:8001/mcp")
    model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    target_modules = {args.module} if args.module else IN_SCOPE_MODULES

    print(f"Connecting to MCP server at {mcp_url} ...")
    tools = asyncio.run(collect_tools(mcp_url))
    print(f"Found {len(tools)} tools total")

    bedrock = make_bedrock_client()

    # Group tools by module
    by_module: dict[str, list] = {m: [] for m in target_modules}
    for tool in tools:
        mod = get_module(tool.name)
        if mod in target_modules:
            by_module[mod].append(tool)

    for module, module_tools in by_module.items():
        if not module_tools:
            print(f"\n[{module}] no tools found — skipping")
            continue

        print(f"\n[{module}] {len(module_tools)} tools")
        existing = load_existing(module)
        existing_ids = {c["id"] for c in existing}
        new_cases = list(existing)

        for tool in module_tools:
            case_id = f"{tool.name}_happy"
            if case_id in existing_ids and not args.overwrite:
                print(f"  Skipping {tool.name} (already has happy_path case)")
                continue
            print(f"  Drafting case for {tool.name} ...")
            case = draft_case(tool, bedrock, model_id)
            if case is None:
                continue
            # Replace existing happy_path if overwrite, else append
            new_cases = [c for c in new_cases if c["id"] != case_id]
            new_cases.append(case)

        if args.dry_run:
            print(json.dumps({"module": module, "cases": new_cases}, indent=2))
        else:
            write_cases(module, new_cases)

    print("\nDone. Review generated cases, then hand-author ambiguous_selection, missing_parameter, and multi_tool cases.")


if __name__ == "__main__":
    main()
