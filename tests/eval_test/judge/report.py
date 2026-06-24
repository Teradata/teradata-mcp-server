"""Collect eval outcomes and write human-readable summaries to results/."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
RUNS_DIR = RESULTS_DIR / "runs"
LATEST_POINTER_FILE = RESULTS_DIR / "latest.json"
INDEX_FILE = RESULTS_DIR / "index.json"
MAX_INDEX_RUNS = 50


@dataclass
class CaseEvalResult:
    case_id: str
    case_type: str
    description: str
    input: str
    expected_tools: list[dict[str, Any]]
    passed: bool
    failure_stage: str | None = None
    failure_detail: str | None = None
    actual_tools: list[dict[str, Any]] | None = None
    actual_output: str | None = None
    metric_reasons: list[str] = field(default_factory=list)
    recommendation: str | None = None
    turn_details: list[dict[str, Any]] | None = None


@dataclass
class EvalRunReport:
    started_at: str
    module_filter: str
    case_type_filter: str
    agent_model_id: str
    judge_model_id: str
    evals_database: str
    description_mode: str = "mcp_server"
    description_overrides_file: str | None = None
    description_override_count: int = 0
    run_label: str | None = None
    results: list[CaseEvalResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for result in self.results if result.passed)

    @property
    def failed_count(self) -> int:
        return self.total - self.passed_count


_report: EvalRunReport | None = None


def begin_eval_run(
    *,
    agent_model_id: str,
    judge_model_id: str,
    evals_database: str,
    description_mode: str = "mcp_server",
    description_overrides_file: str | None = None,
    description_override_count: int = 0,
    run_label: str | None = None,
) -> None:
    """Start a fresh in-memory report for the current pytest session."""
    global _report
    _report = EvalRunReport(
        started_at=datetime.now(timezone.utc).isoformat(),
        module_filter=os.environ.get("EVALS_RUN_MODULE", "all"),
        case_type_filter=os.environ.get("EVALS_RUN_TYPE", "all"),
        agent_model_id=agent_model_id,
        judge_model_id=judge_model_id,
        evals_database=evals_database,
        description_mode=description_mode,
        description_overrides_file=description_overrides_file,
        description_override_count=description_override_count,
        run_label=run_label or os.environ.get("EVALS_RUN_LABEL") or None,
    )


def record_case_result(result: CaseEvalResult) -> None:
    """Append a case outcome to the current report."""
    if _report is None:
        return
    _report.results.append(result)


def get_current_report() -> EvalRunReport | None:
    return _report


def _tool_names(tools: list[dict[str, Any]] | None) -> list[str]:
    if not tools:
        return []
    return [tool["name"] for tool in tools]


def _competing_tool_hint(description: str, expected_tool: str) -> str | None:
    patterns = [
        rf"\bnot\s+({expected_tool.split('_', 1)[0]}_\w+)\b",
        rf"\bover\s+({expected_tool.split('_', 1)[0]}_\w+)\b",
        rf"\bvs\.?\s+({expected_tool.split('_', 1)[0]}_\w+)\b",
        rf"\binstead of\s+({expected_tool.split('_', 1)[0]}_\w+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, description, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    generic = re.search(r"\b(base|dba|sec|qlty|chat|plot|tmpl)_\w+\b", description)
    if generic and generic.group(0) != expected_tool:
        return generic.group(0)
    return None


def build_recommendation(
    case: dict,
    *,
    failure_stage: str,
    failure_detail: str | None,
    expected_tools: list[dict[str, Any]],
    actual_tools: list[dict[str, Any]] | None,
    metric_reasons: list[str],
) -> str:
    """Turn a failure into actionable guidance on prompts and tool descriptions."""
    case_type = case.get("type", "happy_path")
    description = case.get("description", "")
    prompt = case.get("input") or "(multi-turn — see turn details)"
    expected_names = _tool_names(expected_tools)
    actual_names = _tool_names(actual_tools)
    expected_primary = expected_names[0] if expected_names else "the expected tool"
    actual_primary = actual_names[0] if actual_names else "no tool"

    if failure_stage == "agent":
        return (
            f"The agent loop failed before scoring: {failure_detail}. "
            "Check MCP server connectivity, Bedrock credentials, and that the eval prompt is reachable "
            f"with the current environment (`EVALS_DATABASE={os.environ.get('EVALS_DATABASE', '')}`)."
        )

    override_note = ""
    if os.environ.get("USE_DESCRIPTION_OVERRIDES", "").lower() in {"1", "true", "yes"} or os.environ.get(
        "DESCRIPTION_OVERRIDES_FILE"
    ):
        override_note = (
            " This run used description_overrides.json rather than live MCP descriptions — "
            "if a revised override fixes routing, promote that wording to the MCP server."
        )

    if case_type == "ambiguous_selection":
        competing = _competing_tool_hint(description, expected_primary)
        competitor_text = (
            f" and `{competing}`" if competing and competing != expected_primary else ""
        )
        return (
            f"This case tests routing between `{expected_primary}`{competitor_text}. "
            f"Eval prompt: \"{prompt}\". "
            f"The agent chose `{actual_primary}` instead of `{expected_primary}`. "
            "Recommendation: tighten the MCP tool descriptions so only one tool clearly applies — "
            f"sharpen `{expected_primary}` for this scenario or narrow `{actual_primary}` so it does not absorb it. "
            "Also confirm the eval prompt uses vocabulary different from both descriptions and is not biased "
            f"toward `{actual_primary}`."
            f"{override_note}"
        )

    if case_type == "missing_parameter":
        if actual_names:
            return (
                f"The prompt deliberately omits required information: \"{prompt}\". "
                f"The agent called `{', '.join(actual_names)}` instead of asking for clarification. "
                "Recommendation: review whether those tool descriptions invite calls without full context, "
                "and keep the eval prompt vague enough that asking is the only reasonable response."
            )
        return (
            f"The prompt deliberately omits required information: \"{prompt}\". "
            "The agent should ask for the missing detail rather than guess or call a tool. "
            f"Judge feedback: {'; '.join(metric_reasons) or failure_detail or 'did not request clarification'}. "
            "Recommendation: make the missing field obvious in the agent system prompt, or tighten tool descriptions "
            "that encourage premature tool use."
        )

    if case_type == "multi_tool":
        return (
            f"This workflow case expects tools in order: {', '.join(expected_names)}. "
            f"The agent produced: {', '.join(actual_names) or 'no tool calls'}. "
            f"Eval prompt: \"{prompt}\". "
            f"Failure detail: {failure_detail or '; '.join(metric_reasons)}. "
            "Recommendation: verify each tool description mentions when it belongs in a multi-step flow, "
            "and confirm the eval prompt states the full task without naming tools directly."
        )

    return (
        f"Expected `{expected_primary}` for prompt: \"{prompt}\". "
        f"The agent produced `{actual_primary}`. "
        f"Failure detail: {failure_detail or '; '.join(metric_reasons) or 'metric check failed'}. "
        "Recommendation: compare the eval prompt with the MCP description for "
        f"`{expected_primary}` — the prompt should map clearly to that tool without copying description wording."
        f"{override_note}"
    )


def _format_tools(tools: list[dict[str, Any]] | None) -> str:
    if not tools:
        return "_none_"
    lines = []
    for tool in tools:
        params = json.dumps(tool.get("params", {}), indent=2)
        lines.append(f"- `{tool['name']}` with params:\n```json\n{params}\n```")
    return "\n".join(lines)


def render_markdown(report: EvalRunReport) -> str:
    """Render a markdown summary for the eval run."""
    lines = [
        "# Teradata MCP Eval Run Summary",
        "",
        f"**Started (UTC):** {report.started_at}",
        f"**Module filter:** {report.module_filter}",
        f"**Case type filter:** {report.case_type_filter}",
        f"**Agent model:** {report.agent_model_id}",
        f"**Judge model:** {report.judge_model_id}",
        f"**Eval database:** {report.evals_database or '(not set)'}",
    ]
    if report.run_label:
        lines.append(f"**Run label:** {report.run_label}")
    if report.description_mode == "overrides":
        lines.append(
            f"**Tool descriptions:** overrides from `{report.description_overrides_file or 'description_overrides.json'}` "
            f"({report.description_override_count} tool(s) patched)"
        )
    else:
        lines.append("**Tool descriptions:** live MCP server (baseline)")
    lines.extend(
        [
            "",
            "## Overview",
            "",
            "| Metric | Count |",
            "| --- | ---: |",
            f"| Total cases | {report.total} |",
            f"| Passed | {report.passed_count} |",
            f"| Failed | {report.failed_count} |",
            "",
        ]
    )

    failed = [result for result in report.results if not result.passed]
    passed = [result for result in report.results if result.passed]

    if failed:
        lines.extend(["## Failed cases", ""])
        for result in failed:
            lines.extend(
                [
                    f"### {result.case_id} ({result.case_type})",
                    "",
                    f"**Description:** {result.description or '—'}",
                    "",
                    "**Eval prompt:**",
                    "",
                    f"> {result.input}",
                    "",
                    "**Expected tool(s):**",
                    "",
                    _format_tools(result.expected_tools),
                    "",
                    "**Actual tool(s):**",
                    "",
                    _format_tools(result.actual_tools),
                    "",
                ]
            )
            if result.actual_output:
                lines.extend(["**Agent response (excerpt):**", "", f"> {result.actual_output[:500]}", ""])
            if result.failure_stage or result.failure_detail:
                lines.append(
                    f"**Failure ({result.failure_stage or 'unknown'}):** "
                    f"{result.failure_detail or '; '.join(result.metric_reasons) or '—'}"
                )
                lines.append("")
            if result.metric_reasons:
                lines.append("**Judge notes:**")
                lines.append("")
                for reason in result.metric_reasons:
                    lines.append(f"- {reason}")
                lines.append("")
            if result.turn_details:
                lines.extend(["**Turn details:**", "", "```json", json.dumps(result.turn_details, indent=2), "```", ""])
            if result.recommendation:
                lines.extend(["**Recommendation:**", "", result.recommendation, ""])
    else:
        lines.extend(["## Failed cases", "", "_None — all cases passed._", ""])

    lines.extend(["## Passed cases", ""])
    if passed:
        for result in passed:
            lines.append(f"- `{result.case_id}` ({result.case_type})")
    else:
        lines.append("_None._")

    lines.append("")
    return "\n".join(lines)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w-]+", "-", text.strip().lower()).strip("-")
    return slug[:40] if slug else "run"


def build_run_id(report: EvalRunReport) -> str:
    """Build a human-readable directory name for an eval run."""
    started_at = report.started_at
    if started_at.endswith("+00:00"):
        started_at = f"{started_at[:-6]}Z"
    timestamp = started_at.replace(":", "-")
    module = _slugify(report.module_filter or "all")
    mode = "overrides" if report.description_mode == "overrides" else "baseline"
    parts = [timestamp, module, mode]
    if report.case_type_filter and report.case_type_filter != "all":
        parts.append(_slugify(report.case_type_filter))
    if report.run_label:
        parts.append(_slugify(report.run_label))
    return "__".join(parts)


@dataclass
class RunArtifacts:
    run_id: str
    run_dir: Path
    summary_md: Path
    summary_json: Path
    manifest: Path


def load_latest_pointer() -> dict[str, Any] | None:
    """Return the latest run pointer document, if present."""
    if not LATEST_POINTER_FILE.exists():
        return None
    try:
        data = json.loads(LATEST_POINTER_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def resolve_default_summary_path() -> Path:
    """Prefer the latest run's summary.json; fall back to legacy latest_summary.json."""
    pointer = load_latest_pointer()
    if pointer:
        summary_json = pointer.get("summary_json")
        if isinstance(summary_json, str):
            candidate = RESULTS_DIR / summary_json
            if candidate.exists():
                return candidate
    legacy = RESULTS_DIR / "latest_summary.json"
    if legacy.exists():
        return legacy
    return legacy


def run_dir_for_summary_path(summary_path: Path) -> Path | None:
    """Return the run directory that owns a summary file, when known."""
    resolved = summary_path.resolve()
    try:
        if resolved.parent.parent == RUNS_DIR.resolve() and resolved.name in {"summary.json", "summary.md"}:
            return resolved.parent
    except Exception:
        pass

    pointer = load_latest_pointer()
    if pointer and summary_path.name == "latest_summary.json":
        run_dir = pointer.get("run_dir")
        if isinstance(run_dir, str):
            return RESULTS_DIR / run_dir
    return None


def resolve_suggestion_output_path(summary_path: Path) -> Path:
    """Write suggestion drafts alongside the eval run when possible."""
    run_dir = run_dir_for_summary_path(summary_path)
    if run_dir is not None:
        return run_dir / "suggested_overrides.json"
    return RESULTS_DIR / "suggested_overrides.json"


def _summary_payload(report: EvalRunReport) -> dict[str, Any]:
    return {
        "run_id": build_run_id(report),
        "started_at": report.started_at,
        "module_filter": report.module_filter,
        "case_type_filter": report.case_type_filter,
        "run_label": report.run_label,
        "agent_model_id": report.agent_model_id,
        "judge_model_id": report.judge_model_id,
        "evals_database": report.evals_database,
        "description_mode": report.description_mode,
        "description_overrides_file": report.description_overrides_file,
        "description_override_count": report.description_override_count,
        "total": report.total,
        "passed": report.passed_count,
        "failed": report.failed_count,
        "cases": [asdict(result) for result in report.results],
    }


def _manifest_payload(report: EvalRunReport, *, run_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "started_at": report.started_at,
        "module_filter": report.module_filter,
        "case_type_filter": report.case_type_filter,
        "run_label": report.run_label,
        "description_mode": report.description_mode,
        "description_overrides_file": report.description_overrides_file,
        "description_override_count": report.description_override_count,
        "agent_model_id": report.agent_model_id,
        "judge_model_id": report.judge_model_id,
        "evals_database": report.evals_database,
        "total": report.total,
        "passed": report.passed_count,
        "failed": report.failed_count,
        "artifacts": {
            "summary_md": "summary.md",
            "summary_json": "summary.json",
            "manifest": "manifest.json",
            "suggested_overrides": "suggested_overrides.json",
        },
    }


def _index_entry(report: EvalRunReport, *, run_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "started_at": report.started_at,
        "module_filter": report.module_filter,
        "case_type_filter": report.case_type_filter,
        "run_label": report.run_label,
        "description_mode": report.description_mode,
        "passed": report.passed_count,
        "failed": report.failed_count,
        "total": report.total,
        "run_dir": f"runs/{run_id}",
        "summary_json": f"runs/{run_id}/summary.json",
        "summary_md": f"runs/{run_id}/summary.md",
    }


def _update_run_index(entry: dict[str, Any]) -> None:
    existing: list[dict[str, Any]] = []
    if INDEX_FILE.exists():
        try:
            data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("runs"), list):
                existing = [item for item in data["runs"] if isinstance(item, dict)]
        except Exception:
            existing = []

    run_id = entry.get("run_id")
    existing = [item for item in existing if item.get("run_id") != run_id]
    runs = [entry, *existing][:MAX_INDEX_RUNS]
    INDEX_FILE.write_text(json.dumps({"runs": runs}, indent=2) + "\n", encoding="utf-8")


def load_run_index() -> list[dict[str, Any]]:
    """Return indexed eval runs, newest first."""
    if not INDEX_FILE.exists():
        return []
    try:
        data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("runs"), list):
            return [item for item in data["runs"] if isinstance(item, dict)]
    except Exception:
        pass
    return []


def format_run_index(limit: int = 20) -> str:
    """Render a compact table of recent eval runs."""
    runs = load_run_index()[:limit]
    if not runs:
        return "No indexed eval runs yet."

    lines = [
        "Recent eval runs (newest first):",
        "",
        f"{'Run ID':<56} {'Mode':<10} {'Pass':>4} {'Fail':>4}",
        f"{'-' * 56} {'-' * 10} {'-' * 4} {'-' * 4}",
    ]
    for run in runs:
        run_id = str(run.get("run_id", "?"))[:56]
        mode = str(run.get("description_mode", "?"))[:10]
        passed = run.get("passed", "?")
        failed = run.get("failed", "?")
        lines.append(f"{run_id:<56} {mode:<10} {passed:>4} {failed:>4}")
    lines.extend(["", f"Latest pointer: {LATEST_POINTER_FILE}", f"Full index: {INDEX_FILE}"])
    return "\n".join(lines)


def write_eval_summary(report: EvalRunReport) -> RunArtifacts:
    """Write run artifacts under results/runs/<run_id>/ and update index pointers."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    run_id = build_run_id(report)
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    summary_md = run_dir / "summary.md"
    summary_json = run_dir / "summary.json"
    manifest = run_dir / "manifest.json"
    latest_markdown = RESULTS_DIR / "latest_summary.md"
    latest_json = RESULTS_DIR / "latest_summary.json"

    markdown = render_markdown(report)
    payload = _summary_payload(report)
    manifest_payload = _manifest_payload(report, run_id=run_id)

    summary_md.write_text(markdown + "\n", encoding="utf-8")
    summary_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    manifest.write_text(json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8")

    latest_markdown.write_text(markdown + "\n", encoding="utf-8")
    latest_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    run_dir_rel = f"runs/{run_id}"
    pointer = {
        "run_id": run_id,
        "started_at": report.started_at,
        "run_dir": run_dir_rel,
        "summary_md": f"{run_dir_rel}/summary.md",
        "summary_json": f"{run_dir_rel}/summary.json",
        "manifest": f"{run_dir_rel}/manifest.json",
        "module_filter": report.module_filter,
        "case_type_filter": report.case_type_filter,
        "run_label": report.run_label,
        "description_mode": report.description_mode,
        "passed": report.passed_count,
        "failed": report.failed_count,
        "total": report.total,
    }
    LATEST_POINTER_FILE.write_text(json.dumps(pointer, indent=2) + "\n", encoding="utf-8")
    _update_run_index(_index_entry(report, run_id=run_id))

    return RunArtifacts(
        run_id=run_id,
        run_dir=run_dir,
        summary_md=summary_md,
        summary_json=summary_json,
        manifest=manifest,
    )
