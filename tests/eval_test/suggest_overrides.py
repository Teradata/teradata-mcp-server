"""
Draft description_overrides.json entries from failed eval cases.

Usage:
    uv run python suggest_overrides.py
    uv run python suggest_overrides.py --type missing_parameter
    uv run python suggest_overrides.py --summary results/latest_summary.json
    uv run python suggest_overrides.py --dry-run
    uv run python suggest_overrides.py --apply
    uv run python suggest_overrides.py --apply --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent.client import DEFAULT_OVERRIDES_FILE
from judge.report import resolve_default_summary_path, resolve_suggestion_output_path
from judge.suggest_overrides import (
    DEFAULT_CASE_TYPES,
    apply_suggestions_to_overrides,
    generate_suggestions,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Suggest description_overrides.json entries from failed eval cases",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=None,
        help="Eval summary JSON to read (default: latest run from results/latest.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Where to write the draft (default: alongside the source run, plus results/suggested_overrides.json)",
    )
    parser.add_argument(
        "--overrides-file",
        type=Path,
        default=DEFAULT_OVERRIDES_FILE,
        help="Existing overrides file to include as context (default: description_overrides.json)",
    )
    parser.add_argument(
        "--type",
        dest="case_type",
        help=(
            "Case type(s) to process — comma-separated subset of "
            "ambiguous_selection, happy_path, missing_parameter, multi_tool "
            f"(default: all)"
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Generate: print prompts only. Apply: preview merge only.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Merge reviewed suggestions into description_overrides.json (replaces existing tool entries)",
    )
    parser.add_argument(
        "--suggestions",
        type=Path,
        default=None,
        help="Draft to apply when using --apply (default: latest run draft or results/suggested_overrides.json)",
    )
    parser.add_argument(
        "--tools",
        help="Comma-separated tool names to apply when using --apply (default: all suggestions in the draft)",
    )
    args = parser.parse_args()

    summary_path = args.summary or resolve_default_summary_path()
    output_path = args.output or resolve_suggestion_output_path(summary_path)
    suggestions_path = args.suggestions or output_path

    if args.apply:
        only_tools = None
        if args.tools:
            only_tools = {part.strip() for part in args.tools.split(",") if part.strip()}
        try:
            result = apply_suggestions_to_overrides(
                suggestions_path=suggestions_path,
                overrides_path=args.overrides_file,
                only_tools=only_tools,
                dry_run=args.dry_run,
            )
        except FileNotFoundError as exc:
            print(exc, file=sys.stderr)
            sys.exit(1)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)

        if result.get("message"):
            print(result["message"])
            sys.exit(0)

        applied = result.get("applied", [])
        removed = result.get("removed", [])
        target = result["overrides_path"]
        if args.dry_run:
            print(f"Dry run — would write {result['applied_count']} tool(s) → {target}")
        else:
            print(f"Applied {result['applied_count']} tool(s) → {target}")
        if applied:
            print(f"  applied: {', '.join(applied)}")
        if removed:
            print(f"  removed: {', '.join(removed)}")
        if not args.dry_run:
            print("Re-run evals with overrides:")
            print("  uv run python run_evals.py --with-description-overrides")
        sys.exit(0)

    try:
        payload = generate_suggestions(
            summary_path=summary_path,
            output_path=output_path,
            overrides_path=args.overrides_file,
            case_type=args.case_type,
            dry_run=args.dry_run,
        )
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if payload.get("message"):
        print(payload["message"])
        if payload.get("skipped"):
            for entry in payload["skipped"]:
                print(f"  skipped {entry['case_id']}: {entry['reason']}")
        sys.exit(0)

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        sys.exit(0)

    suggestion_count = len(payload.get("suggestions", {}))
    case_count = len(payload.get("cases", []))
    skipped_count = len(payload.get("skipped", []))
    print(f"Wrote {suggestion_count} tool suggestion(s) from {case_count} case(s) → {output_path}")
    if output_path.name == "suggested_overrides.json" and output_path.parent.name != "results":
        print(f"Also copied to results/suggested_overrides.json")
    if skipped_count:
        print(f"Skipped {skipped_count} case(s) — see 'skipped' in {output_path}")
    print("Review the draft, then apply accepted entries:")
    print("  uv run python suggest_overrides.py --apply")
    print("  uv run python run_evals.py --with-description-overrides")


if __name__ == "__main__":
    main()
