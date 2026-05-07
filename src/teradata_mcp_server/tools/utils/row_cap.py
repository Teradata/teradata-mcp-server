"""Row-cap helpers for tool outputs (issue #249).

The wrapper layer caps result-set size before rows reach the LLM. This module
houses the pure logic so it can be unit-tested without the FastMCP runtime.

Resolution order (highest precedence first):
    1. YAML ``bypass_row_cap: true``        -> no cap (handled by ``is_bypassed``)
    2. Hard-coded bypass list               -> no cap (handled by ``is_bypassed``)
    3. YAML ``row_limit:`` (YAML tools)
    4. ``profiles.yml`` ``tool_row_limits.<tool_name>`` (Python ``handle_*``)
    5. ``Settings.default_row_limit``

Ceiling: YAML ``max_row_limit:`` if present, else ``Settings.max_row_limit``.
"""

from __future__ import annotations

import inspect
import re
from typing import Any

# Tool families that should never receive a row-cap. These either don't return
# tabular result sets, materialize their own contracts, or have curated SQL.
DEFAULT_BYPASS_PREFIXES: tuple[str, ...] = (
    "plot_",
    "fs_",
    "tdvs_",
    "bar_",
    "rag_",
    "sql_opt_",
    "chat_",
    "tmpl_",
    "tdml_",
    "graph_",
)

DEFAULT_BYPASS_NAMES: frozenset[str] = frozenset(
    {
        "base_columnMetadata",  # has its own object-level pagination contract
        "base_tableDDL",  # single-row DDL
        "base_saveDDL",  # writes to disk
        "base_writeQuery",  # DDL/DML
        "base_dynamicQuery",  # DDL/DML
    }
)

# Parameters that are *never* useful for narrowing a result set. Excluded
# from the dynamic hint that suggests refinement parameters to the LLM.
NEVER_NARROWING: frozenset[str] = frozenset(
    {
        "persist",
        "output_table_name",
        "database_name",
        "format",
        "max_workers",
        "max_payload_kb",
        "max_execution_seconds",
        "fields",
        "exclude_objects",
        "tool_name",
        "get_all",
        "conn",
        "fs_config",
    }
)

_LOCKING_PREFIX_RE = re.compile(
    r"^\s*(?:LOCKING\s+(?:ROW|TABLE)\s+FOR\s+ACCESS\s*)+",
    re.IGNORECASE,
)


def is_bypassed(tool_name: str, yaml_meta: dict[str, Any] | None = None) -> bool:
    """Return True when this tool should not receive a row-cap."""
    if yaml_meta and yaml_meta.get("bypass_row_cap") is True:
        return True
    if tool_name in DEFAULT_BYPASS_NAMES:
        return True
    return any(tool_name.startswith(prefix) for prefix in DEFAULT_BYPASS_PREFIXES)


def resolve_row_limit(
    tool_name: str,
    *,
    get_all: bool,
    settings_default: int,
    settings_max: int,
    yaml_row_limit: int | None = None,
    yaml_max_row_limit: int | None = None,
    profile_tool_row_limits: dict[str, int] | None = None,
) -> tuple[int, int, bool]:
    """Resolve the effective row-cap for a tool call.

    Returns ``(limit, ceiling, get_all_used)`` where ``limit`` is the
    effective row count cap and ``ceiling`` is the hard upper bound that
    ``get_all=True`` would raise toward.
    """
    ceiling = yaml_max_row_limit if yaml_max_row_limit is not None else settings_max

    base_limit: int
    if yaml_row_limit is not None:
        base_limit = yaml_row_limit
    elif profile_tool_row_limits and tool_name in profile_tool_row_limits:
        base_limit = profile_tool_row_limits[tool_name]
    else:
        base_limit = settings_default

    if get_all:
        return ceiling, ceiling, True
    return min(base_limit, ceiling), ceiling, False


# Matches the ``SELECT [DISTINCT|ALL]`` head of a SQL statement. Group 1 is the
# whole prefix (including any DISTINCT/ALL keyword and trailing whitespace).
_SELECT_HEAD_RE = re.compile(r"^(SELECT(?:\s+(?:DISTINCT|ALL))?\s+)", re.IGNORECASE)
# Matches an existing ``TOP n`` immediately after SELECT.
_EXISTING_TOP_RE = re.compile(r"^TOP\s+\d", re.IGNORECASE)


def _strip_for_analysis(sql: str) -> str:
    """Lift ``LOCKING ... FOR ACCESS`` prefix, strip trailing semicolons/whitespace."""
    stripped = _LOCKING_PREFIX_RE.sub("", sql).strip()
    while stripped.endswith(";"):
        stripped = stripped[:-1].rstrip()
    return stripped


def _has_top_level_keyword(sql: str, keyword: str) -> bool:
    """Return True when ``keyword`` (uppercase, word-boundaried) appears at paren depth 0."""
    keyword_upper = keyword.upper()
    klen = len(keyword_upper)
    depth = 0
    upper = sql.upper()
    n = len(upper)
    i = 0
    while i < n:
        ch = upper[i]
        if ch == "(":
            depth += 1
            i += 1
            continue
        if ch == ")":
            depth -= 1
            i += 1
            continue
        if depth == 0 and upper[i : i + klen] == keyword_upper:
            before_ok = i == 0 or not (upper[i - 1].isalnum() or upper[i - 1] == "_")
            after = i + klen
            after_ok = after >= n or not (upper[after].isalnum() or upper[after] == "_")
            if before_ok and after_ok:
                return True
        i += 1
    return False


def can_inject_top(sql: str | None) -> bool:
    """Return True when ``TOP n`` can be safely inserted after the SELECT keyword.

    Teradata-specific constraints (errors 3706, 6916) that force a Python-side
    trim fallback instead:
      - SHOW commands and CTEs (``WITH ...``)
      - Statements that already specify ``TOP n``
      - ``TOP N select requires a FROM clause`` — skip when no top-level FROM
      - ``Top N option is not supported with QUALIFY clause`` — skip when top-level QUALIFY
    """
    if not sql:
        return False
    stripped = _strip_for_analysis(sql)
    if not stripped:
        return False

    head = stripped[:6].upper()
    if head.startswith("SHOW "):
        return False
    if stripped[:5].upper() == "WITH ":
        return False
    if not head.startswith("SELECT"):
        return False

    select_match = _SELECT_HEAD_RE.match(stripped)
    if not select_match:
        return False
    rest = stripped[select_match.end() :]
    if _EXISTING_TOP_RE.match(rest):
        return False

    if not _has_top_level_keyword(stripped, "FROM"):
        return False
    return not _has_top_level_keyword(stripped, "QUALIFY")


def wrap_with_top(sql: str, n: int) -> str:
    """Inject ``TOP n`` after the leading ``SELECT`` (and optional DISTINCT/ALL).

    Inline injection avoids derived-table restrictions (Teradata 3706: ORDER BY
    in subqueries, all expressions must have explicit names). The leading
    ``LOCKING ... FOR ACCESS`` prefix is preserved at the start. Trailing
    semicolons are stripped. Caller is responsible for passing ``row_limit + 1``
    when sentinel detection is desired.

    Falls back to returning the cleaned SQL unchanged when no SELECT head is
    found (caller should have gated on ``can_inject_top``).
    """
    locking_match = _LOCKING_PREFIX_RE.match(sql)
    locking_prefix = ""
    body = sql
    if locking_match:
        locking_prefix = locking_match.group(0).strip() + " "
        body = sql[locking_match.end() :]

    body = body.strip()
    while body.endswith(";"):
        body = body[:-1].rstrip()

    select_match = _SELECT_HEAD_RE.match(body)
    if not select_match:
        return locking_prefix + body
    head = body[: select_match.end()]
    rest = body[select_match.end() :]
    return f"{locking_prefix}{head}TOP {n} {rest}"


def compute_narrowing_params(
    signature: inspect.Signature | None,
    yaml_meta: dict[str, Any] | None = None,
) -> list[str]:
    """Identify parameters that meaningfully narrow this tool's result.

    Resolution order:
        1. YAML ``narrowing_parameters: [...]`` explicit override
        2. YAML ``parameters:`` map keys (for YAML-defined tools)
        3. Signature parameter names (for Python ``handle_*`` tools)
    Names in ``NEVER_NARROWING`` and any ``_``-prefixed reserved names are filtered out.
    """
    if yaml_meta and isinstance(yaml_meta.get("narrowing_parameters"), list):
        return [str(p) for p in yaml_meta["narrowing_parameters"]]

    candidates: list[str] = []
    if yaml_meta and isinstance(yaml_meta.get("parameters"), dict):
        candidates = list(yaml_meta["parameters"].keys())
    elif signature is not None:
        candidates = [
            name
            for name, param in signature.parameters.items()
            if param.kind
            in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
        ]

    return [name for name in candidates if name not in NEVER_NARROWING and not name.startswith("_")]


def build_truncation_metadata(
    *,
    rows_returned: int,
    row_limit: int,
    hard_ceiling: int,
    get_all_used: bool,
    tool_name: str,
    narrowing_params: list[str],
) -> dict[str, Any]:
    """Build the ``metadata.truncation`` block stamped onto truncated responses."""
    return {
        "truncated": True,
        "rows_returned": rows_returned,
        "row_limit": row_limit,
        "hard_ceiling": hard_ceiling,
        "get_all_used": get_all_used,
        "hint": _build_hint(tool_name, narrowing_params, hard_ceiling, get_all_used),
    }


def _build_hint(
    tool_name: str,
    narrowing_params: list[str],
    hard_ceiling: int,
    get_all_used: bool,
) -> str:
    if get_all_used:
        return (
            f"Result still truncated at the hard ceiling of {hard_ceiling} rows. "
            "Refine the query — get_all cannot raise the limit further. "
            "For full results, use persist=true and query the volatile table directly."
        )

    if tool_name == "base_readQuery":
        return (
            "Result truncated. Add a TOP, SAMPLE, or WHERE clause to your SQL, "
            f"or pass get_all=true to raise the limit to {hard_ceiling} rows."
        )

    if narrowing_params:
        params_str = ", ".join(narrowing_params)
        return (
            f"Result truncated. Refine using parameters [{params_str}] to narrow "
            f"the result, or pass get_all=true to raise the limit to {hard_ceiling} rows."
        )

    return f"Result truncated. Pass get_all=true to raise the limit to {hard_ceiling} rows."
