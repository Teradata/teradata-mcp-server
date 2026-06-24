"""Deterministic structural checks that run before the LLM judge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Param values compared exactly when non-empty in the expected case.
EXACT_VALUE_KEYS = frozenset(
    {
        "database_name",
        "table_name",
        "column_name",
        "user_name",
        "username",
        "role_name",
    }
)

# Param keys that must be present but may differ in value (e.g. SQL wording).
PRESENCE_ONLY_KEYS = frozenset({"sql", "query"})


@dataclass
class ToolCallRecord:
    name: str
    input_parameters: dict[str, Any]


def _check_params(expected_params: dict[str, Any], actual_params: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for key, expected_value in expected_params.items():
        if key not in actual_params:
            errors.append(f"missing param key '{key}'")
            continue

        actual_value = actual_params[key]

        if key in PRESENCE_ONLY_KEYS:
            if expected_value and not actual_value:
                errors.append(f"param '{key}' must not be empty")
            continue

        if key in EXACT_VALUE_KEYS and expected_value not in ("", None):
            if actual_value != expected_value:
                errors.append(
                    f"param '{key}': expected {expected_value!r}, got {actual_value!r}",
                )

    return errors


def _check_tool_pair(
    expected: ToolCallRecord,
    actual: ToolCallRecord,
    *,
    label: str,
) -> list[str]:
    errors: list[str] = []
    if actual.name != expected.name:
        errors.append(f"{label}: expected tool {expected.name!r}, got {actual.name!r}")
    errors.extend(_check_params(expected.input_parameters, actual.input_parameters))
    return errors


def run_deterministic_checks(
    case: dict,
    tools_called: list[ToolCallRecord],
) -> list[str]:
    """Return a list of structural check failures (empty list means pass)."""
    case_type = case.get("type", "happy_path")
    expected_raw = case.get("expected_tools", [])
    expected = [
        ToolCallRecord(name=t["name"], input_parameters=t.get("params", {}))
        for t in expected_raw
    ]

    if case_type == "missing_parameter":
        if tools_called:
            names = [tc.name for tc in tools_called]
            return [f"expected no tool calls for missing_parameter case, got {names}"]
        return []

    if not expected:
        return []

    errors: list[str] = []

    if case_type == "multi_tool":
        if len(tools_called) != len(expected):
            errors.append(
                f"multi_tool: expected {len(expected)} tool call(s), got {len(tools_called)}",
            )
            return errors
        for i, (exp, act) in enumerate(zip(expected, tools_called, strict=True)):
            errors.extend(_check_tool_pair(exp, act, label=f"step {i + 1}"))
        return errors

    if not tools_called:
        return ["expected at least one tool call, got none"]

    errors.extend(_check_tool_pair(expected[0], tools_called[0], label="primary tool"))

    return errors


def assert_deterministic_checks(case: dict, tools_called: list[ToolCallRecord]) -> None:
    """Fail fast on structural mismatch before invoking the LLM judge."""
    errors = run_deterministic_checks(case, tools_called)
    if errors:
        case_id = case.get("id", "<unknown>")
        detail = "; ".join(errors)
        raise AssertionError(f"[{case_id}] deterministic check failed: {detail}")
