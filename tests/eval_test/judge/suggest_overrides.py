"""LLM-assisted draft descriptions for description_overrides.json from eval failures."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from judge.report import (
    RESULTS_DIR,
    _competing_tool_hint,
    resolve_default_summary_path,
    resolve_suggestion_output_path,
    run_dir_for_summary_path,
)

load_dotenv()

DEFAULT_SUMMARY_PATH = RESULTS_DIR / "latest_summary.json"
DEFAULT_OUTPUT_PATH = RESULTS_DIR / "suggested_overrides.json"

DEFAULT_CASE_TYPES = frozenset({"ambiguous_selection", "happy_path", "missing_parameter", "multi_tool"})

AMBIGUOUS_PROMPT = """\
You are improving MCP tool descriptions so an AI agent routes user requests to the correct tool.

An ambiguous_selection eval failed: the agent chose the wrong tool.

Eval case id: {case_id}
Case intent: {case_description}
User prompt: {eval_prompt}
Expected tool: {expected_tool}
Tool the agent chose instead: {actual_tool}
Failure: {failure_detail}
{judge_notes_block}

Current MCP descriptions:

[{expected_tool}]
{expected_description}

[{actual_tool}]
{actual_description}

{existing_override_block}

Rewrite BOTH descriptions so only `{expected_tool}` fits the prompt and `{actual_tool}` clearly does not.
Rules: state when to use and explicit "Do NOT use when…" limits; stay faithful to Teradata MCP behavior;
2–4 sentences each; do not copy the eval prompt verbatim.

Respond with valid JSON only:
{{
  "tools": {{
    "{expected_tool}": "<revised description>",
    "{actual_tool}": "<revised description>"
  }},
  "rationale": "<one sentence>"
}}
"""

HAPPY_PATH_PROMPT = """\
You are improving MCP tool descriptions so an AI agent selects the correct tool and parameters.

A happy_path eval failed: the agent did not call the expected tool correctly.

Eval case id: {case_id}
Case intent: {case_description}
User prompt: {eval_prompt}
Expected tool: {expected_tool}
Actual tool(s) called: {actual_tools_summary}
Failure: {failure_detail}
{judge_notes_block}

Current MCP descriptions:
{tool_description_block}

{existing_override_block}

Revise the description(s) for: {tool_list}.
Make `{expected_tool}` clearly match prompts like the one above. If another tool absorbed the request, \
narrow that tool with explicit limitations.
Rules: stay faithful to Teradata MCP behavior; 2–4 sentences per tool; do not copy the eval prompt verbatim.

Respond with valid JSON only:
{{
  "tools": {{
    "<tool_name>": "<revised description>"
  }},
  "rationale": "<one sentence>"
}}
Include one entry per tool listed in "Revise the description(s) for".
"""

MISSING_PARAMETER_PROMPT = """\
You are improving MCP tool descriptions so an AI agent asks for missing information instead of \
calling tools prematurely or guessing.

A missing_parameter eval failed.

Eval case id: {case_id}
Case intent: {case_description}
User prompt: {eval_prompt}
Expected behavior: ask for clarification — do NOT call a tool yet
Actual tool(s) called: {actual_tools_summary}
Failure: {failure_detail}
{judge_notes_block}
{turn_details_block}

Current MCP descriptions:
{tool_description_block}

{existing_override_block}

Revise the description(s) for: {tool_list}.
Each revised description must state which required inputs must be present before calling \
(e.g. database_name, table_name, sql) and tell the agent to ask the user when they are missing.
Rules: stay faithful to Teradata MCP behavior; 2–4 sentences per tool; do not copy the eval prompt verbatim.

Respond with valid JSON only:
{{
  "tools": {{
    "<tool_name>": "<revised description>"
  }},
  "rationale": "<one sentence>"
}}
"""

MULTI_TOOL_PROMPT = """\
You are improving MCP tool descriptions for multi-step workflows.

A multi_tool eval failed: the agent did not chain tools in the expected order.

Eval case id: {case_id}
Case intent: {case_description}
User prompt: {eval_prompt}
Expected tool order: {expected_tools_summary}
Actual tool(s) called: {actual_tools_summary}
Failure: {failure_detail}
{judge_notes_block}

Current MCP descriptions:
{tool_description_block}

{existing_override_block}

Revise the description(s) for: {tool_list}.
Clarify when each tool applies in a multi-step task and what must be completed before the next tool.
Rules: stay faithful to Teradata MCP behavior; 2–4 sentences per tool; do not copy the eval prompt verbatim.

Respond with valid JSON only:
{{
  "tools": {{
    "<tool_name>": "<revised description>"
  }},
  "rationale": "<one sentence>"
}}
"""


@dataclass
class CaseSuggestionPlan:
    case_id: str
    case_type: str
    tool_names: list[str]
    prompt: str
    skip_reason: str | None = None


def load_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Summary not found: {path}. Run baseline evals first.")
    return json.loads(path.read_text())


def load_failed_cases(
    summary: dict[str, Any],
    *,
    case_types: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Return failed cases from an eval summary, optionally filtered by case type."""
    allowed = case_types or DEFAULT_CASE_TYPES
    cases = summary.get("cases", [])
    return [
        case
        for case in cases
        if not case.get("passed", True) and case.get("case_type") in allowed
    ]


def load_failed_ambiguous_cases(summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Return failed ambiguous_selection cases (backward-compatible helper)."""
    return load_failed_cases(summary, case_types=frozenset({"ambiguous_selection"}))


def _tool_name(blocks: list[dict[str, Any]] | None, *, fallback: str = "") -> str:
    if not blocks:
        return fallback
    return blocks[0].get("name", fallback)


def _tool_names_from_blocks(blocks: list[dict[str, Any]] | None) -> list[str]:
    if not blocks:
        return []
    return [tool["name"] for tool in blocks if tool.get("name")]


def tool_pair_for_case(case: dict[str, Any]) -> tuple[str, str] | None:
    """Return (expected_tool, competing_tool) for an ambiguous_selection failure."""
    expected = _tool_name(case.get("expected_tools"))
    if not expected:
        return None

    actual = _tool_name(case.get("actual_tools"))
    if actual and actual != expected:
        return expected, actual

    competing = _competing_tool_hint(case.get("description", ""), expected)
    if competing and competing != expected:
        return expected, competing

    if actual:
        return expected, actual

    return None


def _format_tool_list(names: list[str]) -> str:
    return ", ".join(f"`{name}`" for name in names) if names else "(none)"


def _format_tools_summary(blocks: list[dict[str, Any]] | None) -> str:
    if not blocks:
        return "none"
    parts = []
    for tool in blocks:
        params = json.dumps(tool.get("params", {}), sort_keys=True)
        parts.append(f"{tool['name']}({params})")
    return "; ".join(parts)


def _existing_override_block(tool_names: list[str], existing_overrides: dict[str, str]) -> str:
    if not existing_overrides:
        return ""
    lines = ["Existing local overrides (may be empty for these tools):"]
    for name in tool_names:
        if name in existing_overrides:
            lines.append(f"[{name}] {existing_overrides[name]}")
    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def _judge_notes_block(case: dict[str, Any]) -> str:
    reasons = case.get("metric_reasons") or []
    if not reasons:
        return ""
    return "Judge notes:\n" + "\n".join(f"- {reason}" for reason in reasons)


def _turn_details_block(case: dict[str, Any]) -> str:
    turn_details = case.get("turn_details")
    if not turn_details:
        return ""
    return "Turn details:\n" + json.dumps(turn_details, indent=2)


def _tool_description_block(tool_names: list[str], live_descriptions: dict[str, str]) -> str:
    blocks = []
    for name in tool_names:
        blocks.append(f"[{name}]\n{live_descriptions.get(name, '(no description on MCP server)')}")
    return "\n\n".join(blocks)


def tools_for_case(case: dict[str, Any]) -> list[str]:
    """Return tool names whose descriptions should be revised for this failure."""
    case_type = case.get("case_type", "happy_path")
    expected = _tool_names_from_blocks(case.get("expected_tools"))
    actual = _tool_names_from_blocks(case.get("actual_tools"))

    if case_type == "ambiguous_selection":
        pair = tool_pair_for_case(case)
        return list(pair) if pair else []

    if case_type == "happy_path":
        names = list(dict.fromkeys(expected + [n for n in actual if n not in expected]))
        return names or expected

    if case_type == "missing_parameter":
        if actual:
            return actual
        # Clarification-only failure with no tool calls — nothing to patch in descriptions.
        return []

    if case_type == "multi_tool":
        return list(dict.fromkeys(expected + [n for n in actual if n not in expected]))

    return []


def build_case_plan(
    case: dict[str, Any],
    *,
    live_descriptions: dict[str, str],
    existing_overrides: dict[str, str],
) -> CaseSuggestionPlan | None:
    """Build the Bedrock prompt plan for one failed case, or None if not actionable."""
    case_id = case.get("case_id", "<unknown>")
    case_type = case.get("case_type", "happy_path")
    tool_names = tools_for_case(case)

    if case_type == "missing_parameter" and not tool_names:
        return CaseSuggestionPlan(
            case_id=case_id,
            case_type=case_type,
            tool_names=[],
            prompt="",
            skip_reason="No tool calls to address — failure is clarification wording, not tool routing.",
        )

    if not tool_names:
        return None

    common = {
        "case_id": case_id,
        "case_description": case.get("description", ""),
        "eval_prompt": case.get("input", ""),
        "failure_detail": case.get("failure_detail") or "; ".join(case.get("metric_reasons") or []) or "unknown",
        "judge_notes_block": _judge_notes_block(case),
        "existing_override_block": _existing_override_block(tool_names, existing_overrides),
        "tool_description_block": _tool_description_block(tool_names, live_descriptions),
        "tool_list": _format_tool_list(tool_names),
    }

    if case_type == "ambiguous_selection":
        expected_tool, actual_tool = tool_names[0], tool_names[1]
        prompt = AMBIGUOUS_PROMPT.format(
            expected_tool=expected_tool,
            actual_tool=actual_tool,
            expected_description=live_descriptions.get(expected_tool, "(no description on MCP server)"),
            actual_description=live_descriptions.get(actual_tool, "(no description on MCP server)"),
            **common,
        )
    elif case_type == "happy_path":
        expected_tool = _tool_name(case.get("expected_tools"))
        prompt = HAPPY_PATH_PROMPT.format(
            expected_tool=expected_tool,
            actual_tools_summary=_format_tools_summary(case.get("actual_tools")),
            **common,
        )
    elif case_type == "missing_parameter":
        prompt = MISSING_PARAMETER_PROMPT.format(
            actual_tools_summary=_format_tools_summary(case.get("actual_tools")),
            turn_details_block=_turn_details_block(case),
            **common,
        )
    elif case_type == "multi_tool":
        prompt = MULTI_TOOL_PROMPT.format(
            expected_tools_summary=_format_tools_summary(case.get("expected_tools")),
            actual_tools_summary=_format_tools_summary(case.get("actual_tools")),
            **common,
        )
    else:
        return None

    return CaseSuggestionPlan(
        case_id=case_id,
        case_type=case_type,
        tool_names=tool_names,
        prompt=prompt,
    )


def collect_tool_names(cases: list[dict[str, Any]]) -> set[str]:
    names: set[str] = set()
    for case in cases:
        names.update(tools_for_case(case))
    return names


async def fetch_live_descriptions(mcp_url: str, tool_names: set[str]) -> dict[str, str]:
    """Fetch live MCP descriptions for the requested tool names."""
    if not tool_names:
        return {}

    async with streamablehttp_client(mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()

    descriptions: dict[str, str] = {}
    for tool in result.tools:
        if tool.name in tool_names:
            descriptions[tool.name] = tool.description or ""
    return descriptions


def load_existing_overrides(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if isinstance(v, str) and not k.startswith("_")}
    except Exception:
        pass
    return {}


def parse_suggestion_response(text: str) -> dict[str, Any]:
    """Extract the JSON object from an LLM response."""
    start = text.index("{")
    end = text.rindex("}") + 1
    parsed = json.loads(text[start:end])
    if not isinstance(parsed, dict) or "tools" not in parsed:
        raise ValueError("LLM response missing 'tools' object")
    return parsed


def suggest_for_plan(
    plan: CaseSuggestionPlan,
    *,
    bedrock_client,
    model_id: str,
) -> dict[str, Any]:
    response = bedrock_client.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": plan.prompt}]}],
    )
    text = response["output"]["message"]["content"][0]["text"].strip()
    return parse_suggestion_response(text)


def merge_suggestions(
    *,
    source_summary: Path,
    case_results: list[dict[str, Any]],
    skipped: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build the output document written to suggested_overrides.json."""
    merged_tools: dict[str, str] = {}
    for entry in case_results:
        for name, description in entry.get("tools", {}).items():
            merged_tools[name] = description

    payload: dict[str, Any] = {
        "_comment": "LLM draft — review before running suggest_overrides.py --apply",
        "_generated_at": datetime.now(timezone.utc).isoformat(),
        "_source_summary": str(source_summary),
        "_supported_case_types": sorted(DEFAULT_CASE_TYPES),
        "_instructions": (
            "Review this draft, then run: uv run python suggest_overrides.py --apply "
            "and re-run evals with: uv run python run_evals.py --with-description-overrides"
        ),
        "suggestions": merged_tools,
        "cases": case_results,
    }
    run_dir = run_dir_for_summary_path(source_summary)
    if run_dir is not None:
        payload["_source_run_id"] = run_dir.name
        payload["_source_run_dir"] = str(run_dir.relative_to(RESULTS_DIR))
    if skipped:
        payload["skipped"] = skipped
    return payload


DEFAULT_OVERRIDES_COMMENT = (
    "Dev-space description overrides. Gitignored. Edit freely, then promote to MCP server."
)


def load_suggestion_draft(path: Path) -> dict[str, str]:
    """Return tool-name → description entries from a suggested_overrides.json draft."""
    if not path.exists():
        raise FileNotFoundError(f"Suggestions file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid suggestions file (expected JSON object): {path}")

    suggestions = data.get("suggestions", {})
    if not isinstance(suggestions, dict):
        raise ValueError(f"Invalid suggestions file (missing 'suggestions' object): {path}")

    return {name: text for name, text in suggestions.items() if isinstance(name, str) and isinstance(text, str)}


def apply_suggestions_to_overrides(
    *,
    suggestions_path: Path | None = None,
    overrides_path: Path | None = None,
    only_tools: set[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Replace description_overrides.json with reviewed suggestions only."""
    from agent.client import DEFAULT_OVERRIDES_FILE

    resolved_suggestions = suggestions_path or resolve_suggestion_output_path(resolve_default_summary_path())
    target = overrides_path or DEFAULT_OVERRIDES_FILE
    suggestions = load_suggestion_draft(resolved_suggestions)
    if only_tools is not None:
        suggestions = {name: text for name, text in suggestions.items() if name in only_tools}

    if not suggestions:
        return {
            "message": "No suggestions to apply.",
            "suggestions_path": str(resolved_suggestions),
            "overrides_path": str(target),
            "applied": [],
            "removed": [],
        }

    previous_tools: set[str] = set()
    comment = DEFAULT_OVERRIDES_COMMENT
    if target.exists():
        previous_raw = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(previous_raw, dict):
            raise ValueError(f"Invalid overrides file (expected JSON object): {target}")
        previous_tools = {
            key for key, value in previous_raw.items() if isinstance(value, str) and not key.startswith("_")
        }
        if isinstance(previous_raw.get("_comment"), str):
            comment = previous_raw["_comment"]

    applied = sorted(suggestions)
    removed = sorted(previous_tools - set(suggestions))
    raw = {"_comment": comment, **suggestions}

    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")

    return {
        "suggestions_path": str(resolved_suggestions),
        "overrides_path": str(target),
        "applied": applied,
        "removed": removed,
        "applied_count": len(suggestions),
    }


def _parse_case_types(case_type: str | None) -> frozenset[str]:
    if not case_type:
        return DEFAULT_CASE_TYPES
    selected = {part.strip() for part in case_type.split(",") if part.strip()}
    unknown = selected - DEFAULT_CASE_TYPES
    if unknown:
        allowed = ", ".join(sorted(DEFAULT_CASE_TYPES))
        raise ValueError(f"Unknown case type(s): {', '.join(sorted(unknown))}. Allowed: {allowed}")
    return frozenset(selected)


def generate_suggestions(
    *,
    summary_path: Path | None = None,
    output_path: Path | None = None,
    overrides_path: Path | None = None,
    mcp_url: str | None = None,
    model_id: str | None = None,
    case_type: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Generate draft override descriptions for failed eval cases."""
    import boto3

    resolved_summary = summary_path or resolve_default_summary_path()
    resolved_output = output_path or resolve_suggestion_output_path(resolved_summary)

    summary = load_summary(resolved_summary)
    allowed_types = _parse_case_types(case_type)
    failed_cases = load_failed_cases(summary, case_types=allowed_types)
    if not failed_cases:
        allowed = ", ".join(sorted(allowed_types))
        return {
            "suggestions": {},
            "cases": [],
            "message": f"No failed cases in summary for type(s): {allowed}.",
        }

    tool_names = collect_tool_names(failed_cases)
    resolved_url = mcp_url or os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:8001/mcp")
    live_descriptions = asyncio.run(fetch_live_descriptions(resolved_url, tool_names))

    missing = sorted(name for name in tool_names if name not in live_descriptions)
    if missing:
        raise RuntimeError(f"Could not fetch live descriptions for: {', '.join(missing)}")

    existing_overrides = load_existing_overrides(overrides_path)
    resolved_model = model_id or os.environ.get(
        "BEDROCK_JUDGE_MODEL_ID",
        os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
    )
    region = os.environ.get("AWS_REGION", "us-east-1")
    bedrock_client = boto3.client("bedrock-runtime", region_name=region)

    case_results: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    for case in failed_cases:
        plan = build_case_plan(case, live_descriptions=live_descriptions, existing_overrides=existing_overrides)
        if plan is None:
            continue
        if plan.skip_reason:
            skipped.append({"case_id": plan.case_id, "case_type": plan.case_type, "reason": plan.skip_reason})
            continue

        if dry_run:
            case_results.append(
                {
                    "case_id": plan.case_id,
                    "case_type": plan.case_type,
                    "tool_names": plan.tool_names,
                    "eval_prompt": case.get("input"),
                    "prompt_preview": plan.prompt,
                }
            )
            continue

        parsed = suggest_for_plan(plan, bedrock_client=bedrock_client, model_id=resolved_model)
        tools = parsed.get("tools", {})
        if not isinstance(tools, dict):
            raise ValueError(f"Invalid tools payload for case {plan.case_id}")

        case_results.append(
            {
                "case_id": plan.case_id,
                "case_type": plan.case_type,
                "tool_names": plan.tool_names,
                "eval_prompt": case.get("input"),
                "tools": {k: v for k, v in tools.items() if isinstance(v, str)},
                "rationale": parsed.get("rationale", ""),
            }
        )

    if not case_results and not skipped:
        return {
            "suggestions": {},
            "cases": [],
            "message": "Failed cases found but none were actionable for description overrides.",
        }

    payload = merge_suggestions(source_summary=resolved_summary, case_results=case_results, skipped=skipped or None)
    if not dry_run and (case_results or skipped):
        resolved_output.parent.mkdir(parents=True, exist_ok=True)
        resolved_output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        legacy_output = RESULTS_DIR / "suggested_overrides.json"
        if resolved_output != legacy_output:
            legacy_output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return payload
