"""Unit tests for eval summary reporting."""

import json

from judge.report import (
    CaseEvalResult,
    EvalRunReport,
    build_recommendation,
    build_run_id,
    load_latest_pointer,
    render_markdown,
    resolve_default_summary_path,
    resolve_suggestion_output_path,
    write_eval_summary,
)


def test_build_recommendation_ambiguous_selection():
    case = {
        "type": "ambiguous_selection",
        "description": "Prompt with a WHERE clause should use base_readQuery, not base_tablePreview",
        "input": "Get orders where amount > 500",
    }
    recommendation = build_recommendation(
        case,
        failure_stage="deterministic",
        failure_detail="expected tool 'base_readQuery', got 'base_tablePreview'",
        expected_tools=[{"name": "base_readQuery", "params": {}}],
        actual_tools=[{"name": "base_tablePreview", "params": {}}],
        metric_reasons=[],
    )
    assert "base_readQuery" in recommendation
    assert "base_tablePreview" in recommendation
    assert "Get orders where amount > 500" in recommendation


def test_render_markdown_includes_failed_case_prompt_and_recommendation():
    report = EvalRunReport(
        started_at="2026-06-23T12:00:00+00:00",
        module_filter="base",
        case_type_filter="all",
        agent_model_id="agent-model",
        judge_model_id="judge-model",
        evals_database="demo_user",
        results=[
            CaseEvalResult(
                case_id="base_readQuery_ambiguous",
                case_type="ambiguous_selection",
                description="Should prefer readQuery",
                input="Show high-value orders",
                expected_tools=[{"name": "base_readQuery", "params": {"sql": "SELECT 1"}}],
                passed=False,
                failure_stage="deterministic",
                failure_detail="wrong tool",
                actual_tools=[{"name": "base_tablePreview", "params": {}}],
                recommendation="Sharpen tool descriptions.",
            )
        ],
    )

    markdown = render_markdown(report)
    assert "# Teradata MCP Eval Run Summary" in markdown
    assert "Show high-value orders" in markdown
    assert "Sharpen tool descriptions." in markdown
    assert "Failed | 1 |" in markdown


def test_build_run_id_includes_module_mode_and_label():
    report = EvalRunReport(
        started_at="2026-06-23T12:00:00+00:00",
        module_filter="base",
        case_type_filter="all",
        agent_model_id="agent-model",
        judge_model_id="judge-model",
        evals_database="demo_user",
        description_mode="overrides",
        run_label="after-tablelist-fix",
    )
    run_id = build_run_id(report)
    assert run_id.startswith("2026-06-23T12-00-00Z")
    assert "__base__overrides__after-tablelist-fix" in run_id


def test_write_eval_summary_creates_run_directory_and_pointers(tmp_path, monkeypatch):
    monkeypatch.setattr("judge.report.RESULTS_DIR", tmp_path)
    monkeypatch.setattr("judge.report.RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr("judge.report.LATEST_POINTER_FILE", tmp_path / "latest.json")
    monkeypatch.setattr("judge.report.INDEX_FILE", tmp_path / "index.json")

    report = EvalRunReport(
        started_at="2026-06-23T12:00:00+00:00",
        module_filter="base",
        case_type_filter="all",
        agent_model_id="agent-model",
        judge_model_id="judge-model",
        evals_database="demo_user",
        description_mode="baseline",
        results=[
            CaseEvalResult(
                case_id="base_tableList_happy",
                case_type="happy_path",
                description="List tables",
                input="List tables in my database",
                expected_tools=[{"name": "base_tableList", "params": {}}],
                passed=True,
                actual_tools=[{"name": "base_tableList", "params": {}}],
            )
        ],
    )

    artifacts = write_eval_summary(report)
    assert artifacts.run_dir.exists()
    assert artifacts.summary_md.exists()
    assert artifacts.summary_json.exists()
    assert artifacts.manifest.exists()
    assert (tmp_path / "latest_summary.md").exists()
    assert (tmp_path / "latest_summary.json").exists()

    pointer = load_latest_pointer()
    assert pointer is not None
    assert pointer["run_id"] == artifacts.run_id
    assert pointer["summary_json"] == f"runs/{artifacts.run_id}/summary.json"

    index = json.loads((tmp_path / "index.json").read_text())
    assert index["runs"][0]["run_id"] == artifacts.run_id


def test_resolve_default_summary_path_prefers_latest_pointer(tmp_path, monkeypatch):
    monkeypatch.setattr("judge.report.RESULTS_DIR", tmp_path)
    monkeypatch.setattr("judge.report.LATEST_POINTER_FILE", tmp_path / "latest.json")

    run_dir = tmp_path / "runs" / "demo-run"
    run_dir.mkdir(parents=True)
    summary = run_dir / "summary.json"
    summary.write_text("{}")

    (tmp_path / "latest.json").write_text(
        json.dumps({"summary_json": "runs/demo-run/summary.json"})
    )
    (tmp_path / "latest_summary.json").write_text("{}")

    assert resolve_default_summary_path() == summary


def test_resolve_suggestion_output_path_uses_run_directory(tmp_path, monkeypatch):
    monkeypatch.setattr("judge.report.RESULTS_DIR", tmp_path)
    monkeypatch.setattr("judge.report.RUNS_DIR", tmp_path / "runs")

    summary = tmp_path / "runs" / "demo-run" / "summary.json"
    summary.parent.mkdir(parents=True)
    summary.write_text("{}")

    output = resolve_suggestion_output_path(summary)
    assert output == summary.parent / "suggested_overrides.json"
