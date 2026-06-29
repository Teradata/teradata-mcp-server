"""
Entry point for the Teradata MCP eval suite.

Usage:
    uv run python run_evals.py                        # all modules
    uv run python run_evals.py --module base          # one module
    uv run python run_evals.py --module base --type ambiguous_selection
    uv run python run_evals.py --verbose
    uv run python run_evals.py --module base --with-description-overrides
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import Any

from preflight import run_preflight
from agent.client import description_overrides_enabled, resolve_description_overrides_file
from judge.report import format_run_index, load_latest_pointer
from judge.model_batch import (
    cost_env_for_role,
    cost_env_names_for_role,
    load_model_batch_config,
    write_batch_summary,
)


CASE_TYPE_FILTERS = {
    "happy_path": "happy",
    "ambiguous_selection": "ambiguous",
    "missing_parameter": "missing",
    "multi_tool": "multi_tool",
    "multi_turn": "clarify_then_call",
}


def _pytest_command(args: argparse.Namespace) -> list[str]:
    cmd = ["deepeval", "test", "run", "tests/"]

    if args.module:
        cmd += ["-k", f"test_{args.module}"]

    if args.case_type:
        keyword = CASE_TYPE_FILTERS.get(args.case_type, args.case_type)
        existing_k = next((cmd[i + 1] for i, c in enumerate(cmd) if c == "-k"), None)
        if existing_k:
            idx = cmd.index("-k")
            cmd[idx + 1] = f"{existing_k} and {keyword}"
        else:
            cmd += ["-k", keyword]

    if args.verbose:
        cmd.append("-v")

    return cmd


def _configure_common_env(args: argparse.Namespace) -> None:
    os.environ["EVALS_RUN_MODULE"] = args.module or "all"
    os.environ["EVALS_RUN_TYPE"] = args.case_type or "all"
    if args.run_label:
        os.environ["EVALS_RUN_LABEL"] = args.run_label
    elif "EVALS_RUN_LABEL" in os.environ:
        del os.environ["EVALS_RUN_LABEL"]

    if args.with_description_overrides or args.description_overrides_file:
        os.environ["USE_DESCRIPTION_OVERRIDES"] = "1"
    if args.description_overrides_file:
        os.environ["DESCRIPTION_OVERRIDES_FILE"] = args.description_overrides_file


def _print_description_mode() -> None:
    if description_overrides_enabled():
        overrides_file = resolve_description_overrides_file()
        print(f"Tool descriptions: overrides from {overrides_file}")
    else:
        print("Tool descriptions: live MCP server (baseline)")


def _run_deepeval(cmd: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    print(f"Running: {' '.join(cmd)}\n")
    return subprocess.run(cmd, env=env)


def _print_latest_run() -> None:
    pointer = load_latest_pointer()
    if pointer:
        print("")
        print(f"Eval run: {pointer.get('run_id')}")
        print(f"Run directory: results/{pointer.get('run_dir')}")
        print(f"Summary: results/{pointer.get('summary_md')}")
        print("Latest copy: results/latest_summary.md")
        print("All runs: uv run python run_evals.py --list-runs")


def _env_with_model_set(base_env: dict[str, str], *, agent_model: Any, judge_model: Any, run_label: str | None) -> dict[str, str]:
    env = dict(base_env)
    env["BEDROCK_MODEL_ID"] = agent_model.model_id
    env["BEDROCK_JUDGE_MODEL_ID"] = judge_model.model_id
    for name in [*cost_env_names_for_role("agent"), *cost_env_names_for_role("judge")]:
        env.pop(name, None)
    env.update(cost_env_for_role("agent", agent_model.pricing))
    env.update(cost_env_for_role("judge", judge_model.pricing))
    if run_label:
        env["EVALS_RUN_LABEL"] = run_label
    else:
        env.pop("EVALS_RUN_LABEL", None)
    return env


def _run_model_batch(args: argparse.Namespace, cmd: list[str]) -> int:
    model_set = load_model_batch_config(args.model_set)
    base_env = dict(os.environ)
    run_summaries: list[dict[str, Any]] = []
    exit_codes: list[int] = []

    print(f"Model set: {model_set.path}")
    print(f"Judge model: {model_set.judge.model_id}")
    print(f"Evaluated models: {len(model_set.evaluated_models)}")
    _print_description_mode()

    for index, agent_model in enumerate(model_set.evaluated_models, start=1):
        model_label = agent_model.label
        if len(model_set.evaluated_models) == 1:
            run_label = args.run_label
        else:
            run_label = "__".join(part for part in [args.run_label, model_set.name, model_label] if part)
        env = _env_with_model_set(base_env, agent_model=agent_model, judge_model=model_set.judge, run_label=run_label)
        print("")
        print(f"[{index}/{len(model_set.evaluated_models)}] Evaluating {agent_model.model_id}")
        result = _run_deepeval(cmd, env=env)
        exit_codes.append(result.returncode)

        pointer = load_latest_pointer()
        if pointer:
            pointer = dict(pointer)
            pointer["agent_model_id"] = agent_model.model_id
            pointer["judge_model_id"] = model_set.judge.model_id
            pointer["model_label"] = agent_model.label
            run_summaries.append(pointer)
            print(f"Summary: results/{pointer.get('summary_md')}")

        if result.returncode not in {0, 1}:
            print(f"Stopping batch after deepeval exited with {result.returncode}.")
            return result.returncode

    if len(model_set.evaluated_models) == 1:
        _print_latest_run()
    else:
        pointer = write_batch_summary(
            model_set=model_set,
            module_filter=args.module or "all",
            case_type_filter=args.case_type or "all",
            run_label=args.run_label,
            runs=run_summaries,
        )
        print("")
        print(f"Eval batch: {pointer.get('batch_id')}")
        print(f"Batch directory: results/{pointer.get('batch_dir')}")
        print(f"Batch summary: results/{pointer.get('summary_md')}")
        print("Latest batch copy: results/latest_batch_summary.md")

    return 1 if any(code == 1 for code in exit_codes) else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Teradata MCP evals via deepeval + pytest")
    parser.add_argument("--module", help="Run evals for a specific module only (base, sec, dba, ...)")
    parser.add_argument(
        "--type",
        dest="case_type",
        help=(
            "Filter by case type (happy_path, ambiguous_selection, missing_parameter, "
            "multi_tool, multi_turn). Matches substrings in pytest case IDs."
        ),
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose pytest output")
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip Teradata eval-table check (not recommended for live eval runs)",
    )
    parser.add_argument(
        "--with-description-overrides",
        action="store_true",
        help=(
            "Patch tool descriptions from description_overrides.json before routing "
            "(default: use live MCP server descriptions as baseline)"
        ),
    )
    parser.add_argument(
        "--description-overrides-file",
        help="Path to overrides JSON (enables overrides; default: description_overrides.json)",
    )
    parser.add_argument(
        "--run-label",
        help="Optional label appended to the run directory name (e.g. after-tablelist-fix)",
    )
    parser.add_argument(
        "--model-set",
        help="YAML file defining one judge model and one or more evaluated models with optional cost parameters",
    )
    parser.add_argument(
        "--list-runs",
        action="store_true",
        help="List recent eval runs from results/index.json and exit",
    )
    args = parser.parse_args()

    if args.list_runs:
        print(format_run_index())
        pointer = load_latest_pointer()
        if pointer:
            print("")
            print(f"Latest run: {pointer.get('run_id')}")
            print(f"  dir: results/{pointer.get('run_dir')}")
            print(f"  summary: results/{pointer.get('summary_md')}")
        sys.exit(0)

    if not args.skip_preflight:
        run_preflight()

    _configure_common_env(args)
    cmd = _pytest_command(args)

    if args.model_set:
        sys.exit(_run_model_batch(args, cmd))

    _print_description_mode()
    result = _run_deepeval(cmd)
    if result.returncode in {0, 1}:
        _print_latest_run()
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
