"""Unit tests for LLM override suggestion helpers."""

import json
from pathlib import Path

import pytest

from judge.suggest_overrides import (
    apply_suggestions_to_overrides,
    build_case_plan,
    load_failed_ambiguous_cases,
    load_failed_cases,
    load_suggestion_draft,
    merge_suggestions,
    parse_suggestion_response,
    tool_pair_for_case,
    tools_for_case,
)


def test_load_failed_cases_filters_by_type():
    summary = {
        "cases": [
            {"case_id": "a", "case_type": "ambiguous_selection", "passed": False},
            {"case_id": "b", "case_type": "missing_parameter", "passed": False},
            {"case_id": "c", "case_type": "happy_path", "passed": False},
            {"case_id": "d", "case_type": "missing_parameter", "passed": True},
        ]
    }
    assert [c["case_id"] for c in load_failed_cases(summary)] == ["a", "b", "c"]
    assert [c["case_id"] for c in load_failed_cases(summary, case_types=frozenset({"missing_parameter"}))] == ["b"]


def test_load_failed_ambiguous_cases_backward_compatible():
    summary = {
        "cases": [
            {"case_id": "a", "case_type": "ambiguous_selection", "passed": False},
            {"case_id": "c", "case_type": "happy_path", "passed": False},
        ]
    }
    assert [case["case_id"] for case in load_failed_ambiguous_cases(summary)] == ["a"]


def test_tool_pair_uses_actual_tool_when_present():
    case = {
        "description": "Should use base_readQuery, not base_tablePreview",
        "expected_tools": [{"name": "base_readQuery", "params": {}}],
        "actual_tools": [{"name": "base_tablePreview", "params": {}}],
    }
    assert tool_pair_for_case(case) == ("base_readQuery", "base_tablePreview")


def test_tools_for_case_missing_parameter_uses_actual_tools():
    case = {
        "case_type": "missing_parameter",
        "expected_tools": [],
        "actual_tools": [{"name": "base_tableList", "params": {"database_name": ""}}],
    }
    assert tools_for_case(case) == ["base_tableList"]


def test_tools_for_case_missing_parameter_without_tools_is_empty():
    case = {
        "case_type": "missing_parameter",
        "expected_tools": [],
        "actual_tools": [],
    }
    assert tools_for_case(case) == []


def test_build_case_plan_skips_clarification_only_missing_parameter():
    case = {
        "case_id": "base_unknown_tool_missing",
        "case_type": "missing_parameter",
        "description": "No matching tool",
        "input": "Tune indexes",
        "expected_tools": [],
        "actual_tools": [],
        "failure_detail": "judge failed",
    }
    plan = build_case_plan(case, live_descriptions={}, existing_overrides={})
    assert plan is not None
    assert plan.skip_reason
    assert plan.tool_names == []


def test_build_case_plan_happy_path_includes_expected_and_actual():
    case = {
        "case_id": "base_readQuery_happy",
        "case_type": "happy_path",
        "description": "Run SQL",
        "input": "query employees",
        "expected_tools": [{"name": "base_readQuery", "params": {}}],
        "actual_tools": [{"name": "base_tablePreview", "params": {}}],
        "failure_detail": "wrong tool",
    }
    plan = build_case_plan(
        case,
        live_descriptions={"base_readQuery": "live", "base_tablePreview": "live2"},
        existing_overrides={},
    )
    assert plan is not None
    assert plan.tool_names == ["base_readQuery", "base_tablePreview"]
    assert "happy_path eval failed" in plan.prompt


def test_parse_suggestion_response_extracts_json():
    parsed = parse_suggestion_response('{"tools": {"base_readQuery": "new text"}, "rationale": "ok"}')
    assert parsed["tools"]["base_readQuery"] == "new text"


def test_parse_suggestion_response_rejects_missing_tools():
    with pytest.raises(ValueError, match="missing 'tools'"):
        parse_suggestion_response('{"rationale": "ok"}')


def test_merge_suggestions_deduplicates_by_last_case():
    payload = merge_suggestions(
        source_summary=Path("results/latest_summary.json"),
        case_results=[
            {
                "case_id": "one",
                "tools": {"base_readQuery": "first", "base_tablePreview": "preview first"},
                "rationale": "a",
            },
            {
                "case_id": "two",
                "tools": {"base_readQuery": "second"},
                "rationale": "b",
            },
        ],
    )
    assert payload["suggestions"]["base_readQuery"] == "second"
    assert payload["suggestions"]["base_tablePreview"] == "preview first"


def test_load_suggestion_draft_reads_tools(tmp_path: Path):
    draft = tmp_path / "suggested_overrides.json"
    draft.write_text(
        json.dumps(
            {
                "suggestions": {"base_tableList": "new list text", "base_readQuery": "new query text"},
                "cases": [],
            }
        )
    )
    assert load_suggestion_draft(draft) == {
        "base_tableList": "new list text",
        "base_readQuery": "new query text",
    }


def test_apply_suggestions_to_overrides_replaces_existing_tools(tmp_path: Path):
    draft = tmp_path / "suggested_overrides.json"
    overrides = tmp_path / "description_overrides.json"
    draft.write_text(json.dumps({"suggestions": {"base_tableList": "new list", "base_newTool": "brand new"}}))
    overrides.write_text(
        json.dumps(
            {
                "_comment": "keep me",
                "base_readQuery": "existing query",
                "base_tableList": "old list",
            },
            indent=2,
        )
        + "\n"
    )

    result = apply_suggestions_to_overrides(
        suggestions_path=draft,
        overrides_path=overrides,
        dry_run=False,
    )
    assert result["applied"] == ["base_newTool", "base_tableList"]
    assert result["removed"] == ["base_readQuery"]

    merged = json.loads(overrides.read_text())
    assert merged["_comment"] == "keep me"
    assert "base_readQuery" not in merged
    assert merged["base_tableList"] == "new list"
    assert merged["base_newTool"] == "brand new"


def test_apply_suggestions_to_overrides_dry_run_does_not_write(tmp_path: Path):
    draft = tmp_path / "suggested_overrides.json"
    overrides = tmp_path / "description_overrides.json"
    draft.write_text(json.dumps({"suggestions": {"base_tableList": "new list"}}))
    overrides.write_text(json.dumps({"base_tableList": "old list"}))

    result = apply_suggestions_to_overrides(
        suggestions_path=draft,
        overrides_path=overrides,
        dry_run=True,
    )
    assert result["applied"] == ["base_tableList"]
    assert json.loads(overrides.read_text())["base_tableList"] == "old list"


def test_apply_suggestions_to_overrides_filters_by_tool(tmp_path: Path):
    draft = tmp_path / "suggested_overrides.json"
    overrides = tmp_path / "description_overrides.json"
    draft.write_text(
        json.dumps({"suggestions": {"base_tableList": "new list", "base_readQuery": "new query"}})
    )

    result = apply_suggestions_to_overrides(
        suggestions_path=draft,
        overrides_path=overrides,
        only_tools={"base_tableList"},
        dry_run=False,
    )
    assert result["applied"] == ["base_tableList"]
    assert result["removed"] == []
    merged = json.loads(overrides.read_text())
    assert list(merged.keys()) == ["_comment", "base_tableList"]
    assert merged["base_tableList"] == "new list"
