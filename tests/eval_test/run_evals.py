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

from preflight import run_preflight
from agent.client import description_overrides_enabled, resolve_description_overrides_file
from judge.report import format_run_index, load_latest_pointer


CASE_TYPE_FILTERS = {
    "happy_path": "happy",
    "ambiguous_selection": "ambiguous",
    "missing_parameter": "missing",
    "multi_tool": "multi_tool",
    "multi_turn": "clarify_then_call",
}


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

    if description_overrides_enabled():
        overrides_file = resolve_description_overrides_file()
        print(f"Tool descriptions: overrides from {overrides_file}")
    else:
        print("Tool descriptions: live MCP server (baseline)")

    print(f"Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    if result.returncode in {0, 1}:
        pointer = load_latest_pointer()
        if pointer:
            print("")
            print(f"Eval run: {pointer.get('run_id')}")
            print(f"Run directory: results/{pointer.get('run_dir')}")
            print(f"Summary: results/{pointer.get('summary_md')}")
            print("Latest copy: results/latest_summary.md")
            print("All runs: uv run python run_evals.py --list-runs")
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
