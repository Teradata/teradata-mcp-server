#!/usr/bin/env python3
"""Unit tests for the row-cap helper module (issue #249).

Exhaustive coverage of pure-logic helpers and the test runner's expectation
engine. No DB, no network. Run with::

    uv run python tests/unit/test_row_cap.py

Each test is a top-level ``test_*`` function. ``main()`` discovers them, runs
them all, and reports pass/fail. Exit code is non-zero on any failure.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

# Make src/ and tests/ importable when invoked as a script.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from run_mcp_tests import _check_expectations, _resolve_dot_path  # noqa: E402

from teradata_mcp_server.tools.utils.row_cap import (  # noqa: E402
    DEFAULT_BYPASS_NAMES,
    DEFAULT_BYPASS_PREFIXES,
    NEVER_NARROWING,
    _has_top_level_keyword,
    build_truncation_metadata,
    can_inject_top,
    compute_narrowing_params,
    is_bypassed,
    resolve_row_limit,
    wrap_with_top,
)

# --------------------------------------------------------------------------
# is_bypassed
# --------------------------------------------------------------------------


def test_is_bypassed_prefixes():
    for prefix in DEFAULT_BYPASS_PREFIXES:
        assert is_bypassed(f"{prefix}example") is True, prefix
    assert is_bypassed("plot_line_chart") is True
    assert is_bypassed("chat_completeChat") is True
    assert is_bypassed("tdml_KMeans") is True
    assert is_bypassed("graph_traceLineage") is True


def test_is_bypassed_names():
    for name in DEFAULT_BYPASS_NAMES:
        assert is_bypassed(name) is True, name
    assert is_bypassed("base_columnMetadata") is True
    assert is_bypassed("base_tableDDL") is True
    assert is_bypassed("base_writeQuery") is True


def test_is_bypassed_capped_tools_are_not_bypassed():
    assert is_bypassed("base_readQuery") is False
    assert is_bypassed("base_tableList") is False
    assert is_bypassed("dba_userSqlList") is False
    assert is_bypassed("dba_featureUsage") is False
    assert is_bypassed("sec_userDbPermissions") is False
    assert is_bypassed("qlty_missingValues") is False


def test_is_bypassed_yaml_override_takes_precedence():
    assert is_bypassed("dba_userSqlList", yaml_meta={"bypass_row_cap": True}) is True
    # Explicit False should NOT resurrect a hard-coded bypass.
    assert is_bypassed("base_columnMetadata", yaml_meta={"bypass_row_cap": False}) is True
    # Empty / None metadata → defer to defaults.
    assert is_bypassed("dba_userSqlList", yaml_meta=None) is False
    assert is_bypassed("dba_userSqlList", yaml_meta={}) is False


# --------------------------------------------------------------------------
# resolve_row_limit
# --------------------------------------------------------------------------


def test_resolve_uses_settings_default():
    limit, ceiling, used = resolve_row_limit("foo", get_all=False, settings_default=1000, settings_max=50000)
    assert (limit, ceiling, used) == (1000, 50000, False)


def test_resolve_get_all_raises_to_ceiling():
    limit, ceiling, used = resolve_row_limit("foo", get_all=True, settings_default=1000, settings_max=50000)
    assert (limit, ceiling, used) == (50000, 50000, True)


def test_resolve_yaml_row_limit_overrides_default():
    limit, _, _ = resolve_row_limit("foo", get_all=False, settings_default=1000, settings_max=50000, yaml_row_limit=200)
    assert limit == 200


def test_resolve_yaml_max_overrides_settings_max():
    limit, ceiling, _ = resolve_row_limit(
        "foo",
        get_all=True,
        settings_default=1000,
        settings_max=50000,
        yaml_row_limit=200,
        yaml_max_row_limit=5000,
    )
    assert (limit, ceiling) == (5000, 5000)


def test_resolve_profile_map_overrides_settings_default():
    limit, _, _ = resolve_row_limit(
        "foo",
        get_all=False,
        settings_default=1000,
        settings_max=50000,
        profile_tool_row_limits={"foo": 250},
    )
    assert limit == 250


def test_resolve_yaml_wins_over_profile_map():
    """YAML row_limit (per-tool) outranks profile-level tool_row_limits."""
    limit, _, _ = resolve_row_limit(
        "foo",
        get_all=False,
        settings_default=1000,
        settings_max=50000,
        yaml_row_limit=10,
        profile_tool_row_limits={"foo": 250},
    )
    assert limit == 10


def test_resolve_clamps_yaml_row_limit_to_ceiling():
    """Even an aggressive YAML row_limit cannot exceed the effective ceiling."""
    limit, ceiling, _ = resolve_row_limit(
        "foo",
        get_all=False,
        settings_default=1000,
        settings_max=50000,
        yaml_row_limit=999_999,
    )
    assert limit == ceiling == 50000


# --------------------------------------------------------------------------
# _has_top_level_keyword
# --------------------------------------------------------------------------


def test_top_level_keyword_finds_simple():
    assert _has_top_level_keyword("SELECT * FROM t", "FROM") is True
    assert _has_top_level_keyword("SELECT * FROM t", "WHERE") is False


def test_top_level_keyword_skips_inside_parens():
    # Window function: ORDER BY is inside OVER(...).
    assert _has_top_level_keyword("SELECT ROW_NUMBER() OVER (ORDER BY x) FROM t", "ORDER BY") is False
    # Subquery: FROM inside parens is at depth>0.
    assert _has_top_level_keyword("SELECT (SELECT 1 FROM t)", "FROM") is False


def test_top_level_keyword_word_boundaries():
    # QUALIFY_COL contains QUALIFY but is not the keyword.
    assert _has_top_level_keyword("SELECT a FROM t WHERE QUALIFY_COL = 1", "QUALIFY") is False
    # MyORDER is not ORDER.
    assert _has_top_level_keyword("SELECT MyORDER FROM t", "ORDER BY") is False


def test_top_level_keyword_case_insensitive():
    assert _has_top_level_keyword("select a from t qualify ROW_NUMBER() OVER (order by x) <= 5", "QUALIFY") is True
    assert _has_top_level_keyword("Select * From t Order By x", "ORDER BY") is True


# --------------------------------------------------------------------------
# can_inject_top
# --------------------------------------------------------------------------


def test_can_inject_simple_select():
    assert can_inject_top("SELECT * FROM t") is True
    assert can_inject_top("select a, b from t where c=1") is True


def test_can_inject_with_order_by_works_inline():
    """Inline TOP injection is compatible with ORDER BY (unlike the old derived-table wrap)."""
    assert can_inject_top("SELECT * FROM t ORDER BY x DESC") is True


def test_can_inject_with_qualify_skipped():
    """Teradata 6916: TOP and QUALIFY are mutually exclusive — must skip injection."""
    assert can_inject_top("SELECT a FROM t QUALIFY ROW_NUMBER() OVER (ORDER BY x) <= 5") is False


def test_can_inject_no_from_skipped():
    """Teradata 3706: 'Top N select requires a FROM clause'."""
    assert can_inject_top("SELECT CURRENT_TIMESTAMP") is False
    assert can_inject_top("SELECT 1 + 2") is False


def test_can_inject_show_skipped():
    assert can_inject_top("SHOW TABLE foo") is False
    assert can_inject_top("show view bar") is False


def test_can_inject_cte_skipped():
    """CTEs disallow ORDER BY in their inner SELECTs and complicate injection — skip."""
    assert can_inject_top("WITH x AS (SELECT 1 FROM t) SELECT * FROM x") is False
    assert can_inject_top("with t1 as (select * from t) select * from t1") is False


def test_can_inject_existing_top_skipped():
    assert can_inject_top("SELECT TOP 5 * FROM t") is False
    assert can_inject_top("SELECT TOP 50 a, b FROM t WHERE c = 1") is False
    assert can_inject_top("select top 5 * from t") is False


def test_can_inject_distinct_with_top_skipped():
    assert can_inject_top("SELECT DISTINCT TOP 5 a FROM t") is False


def test_can_inject_distinct_alone_works():
    assert can_inject_top("SELECT DISTINCT a FROM t") is True


def test_can_inject_locking_prefix_lifted():
    assert can_inject_top("LOCKING ROW FOR ACCESS SELECT * FROM t") is True
    assert can_inject_top("LOCKING TABLE FOR ACCESS SELECT * FROM t WHERE x = 1") is True
    assert can_inject_top("LOCKING ROW FOR ACCESS\nLOCKING TABLE FOR ACCESS\nSELECT * FROM t") is True


def test_can_inject_trailing_semicolons_stripped():
    assert can_inject_top("SELECT * FROM t;") is True
    assert can_inject_top("SELECT * FROM t;;;") is True


def test_can_inject_non_select_skipped():
    assert can_inject_top("INSERT INTO t VALUES (1)") is False
    assert can_inject_top("UPDATE t SET a = 1") is False
    assert can_inject_top("DELETE FROM t") is False
    assert can_inject_top("CREATE TABLE t (a INT)") is False
    assert can_inject_top("DROP TABLE t") is False


def test_can_inject_empty_skipped():
    assert can_inject_top("") is False
    assert can_inject_top(None) is False
    assert can_inject_top("   \n  \t  ") is False
    assert can_inject_top(";") is False


# --------------------------------------------------------------------------
# wrap_with_top
# --------------------------------------------------------------------------


def test_wrap_inline_injection_simple():
    assert wrap_with_top("SELECT * FROM t", 1001) == "SELECT TOP 1001 * FROM t"


def test_wrap_preserves_order_by():
    """ORDER BY remains in place — inline injection doesn't move it."""
    assert wrap_with_top("SELECT * FROM t ORDER BY x DESC", 100) == "SELECT TOP 100 * FROM t ORDER BY x DESC"


def test_wrap_distinct_top_after_distinct():
    """Teradata grammar: SELECT [DISTINCT|ALL] [TOP n] cols. TOP follows DISTINCT."""
    assert wrap_with_top("SELECT DISTINCT a FROM t", 50) == "SELECT DISTINCT TOP 50 a FROM t"
    assert wrap_with_top("SELECT ALL a FROM t", 50) == "SELECT ALL TOP 50 a FROM t"


def test_wrap_locking_prefix_preserved():
    sql = "LOCKING ROW FOR ACCESS SELECT * FROM t"
    assert wrap_with_top(sql, 10) == "LOCKING ROW FOR ACCESS SELECT TOP 10 * FROM t"


def test_wrap_locking_prefix_with_order_by():
    sql = "LOCKING ROW FOR ACCESS SELECT * FROM t ORDER BY x DESC;"
    assert wrap_with_top(sql, 10) == "LOCKING ROW FOR ACCESS SELECT TOP 10 * FROM t ORDER BY x DESC"


def test_wrap_strips_trailing_semicolons():
    assert wrap_with_top("SELECT * FROM t;", 10) == "SELECT TOP 10 * FROM t"
    assert wrap_with_top("SELECT * FROM t;;;", 10) == "SELECT TOP 10 * FROM t"


def test_wrap_real_dba_userSqlList_shape():
    """Reproduces the issue-#249 query shape that originally hit Teradata 3706."""
    sql = (
        "SELECT t1.QueryID, t1.ProcID, t1.CollectTimeStamp, t1.SqlTextInfo, t2.UserName\n"
        "FROM DBC.QryLogSqlV t1\n"
        "JOIN DBC.QryLogV t2 ON t1.QueryID = t2.QueryID\n"
        "WHERE CAST(t1.CollectTimeStamp AS DATE) >= CURRENT_DATE - 7\n"
        "ORDER BY t1.CollectTimeStamp DESC;"
    )
    wrapped = wrap_with_top(sql, 1001)
    # TOP injected after SELECT, ORDER BY preserved as-is, no derived table.
    assert wrapped.startswith("SELECT TOP 1001 t1.QueryID")
    assert wrapped.rstrip().endswith("ORDER BY t1.CollectTimeStamp DESC")
    assert "_td_capped" not in wrapped


# --------------------------------------------------------------------------
# compute_narrowing_params
# --------------------------------------------------------------------------


def test_narrowing_yaml_explicit_override_wins():
    yaml_meta = {"parameters": {"a": {}}, "narrowing_parameters": ["x", "y"]}
    assert compute_narrowing_params(None, yaml_meta) == ["x", "y"]


def test_narrowing_yaml_parameters_fallback():
    yaml_meta = {"parameters": {"user_name": {}, "no_days": {}}}
    assert compute_narrowing_params(None, yaml_meta) == ["user_name", "no_days"]


def test_narrowing_filters_never_narrowing_from_yaml():
    yaml_meta = {"parameters": {"persist": {}, "database_name": {}, "user_name": {}}}
    assert compute_narrowing_params(None, yaml_meta) == ["user_name"]


def test_narrowing_signature_fallback():
    def fake(conn, sql: str = "", persist=False, tool_name=None):
        pass

    sig = inspect.signature(fake)
    # conn, persist, tool_name in NEVER_NARROWING — only sql remains.
    assert compute_narrowing_params(sig) == ["sql"]


def test_narrowing_underscore_reserved_filtered():
    """Reserved kwargs prefixed with _ never appear in user-facing hints."""

    def fake(conn, user_name: str = "", _row_limit=None, _hard_ceiling=None):
        pass

    sig = inspect.signature(fake)
    assert compute_narrowing_params(sig) == ["user_name"]


def test_narrowing_empty_inputs():
    assert compute_narrowing_params(None) == []
    assert compute_narrowing_params(None, None) == []
    assert compute_narrowing_params(None, {}) == []


def test_narrowing_never_narrowing_set_complete():
    """NEVER_NARROWING must include every reserved/non-narrowing parameter."""
    expected = {
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
    assert expected.issubset(NEVER_NARROWING)


# --------------------------------------------------------------------------
# build_truncation_metadata
# --------------------------------------------------------------------------


def test_truncation_metadata_shape():
    md = build_truncation_metadata(
        rows_returned=1000,
        row_limit=1000,
        hard_ceiling=50000,
        get_all_used=False,
        tool_name="dba_userSqlList",
        narrowing_params=["user_name", "no_days"],
    )
    assert md["truncated"] is True
    assert md["rows_returned"] == 1000
    assert md["row_limit"] == 1000
    assert md["hard_ceiling"] == 50000
    assert md["get_all_used"] is False
    assert "hint" in md and isinstance(md["hint"], str)


def test_truncation_hint_mentions_narrowing_params():
    md = build_truncation_metadata(
        rows_returned=1000,
        row_limit=1000,
        hard_ceiling=50000,
        get_all_used=False,
        tool_name="dba_userSqlList",
        narrowing_params=["user_name", "no_days"],
    )
    assert "user_name" in md["hint"]
    assert "no_days" in md["hint"]
    assert "get_all=true" in md["hint"]


def test_truncation_hint_for_base_readQuery_is_specialised():
    """base_readQuery has no parameters that narrow — hint must point at SQL fixes."""
    md = build_truncation_metadata(
        rows_returned=1000,
        row_limit=1000,
        hard_ceiling=50000,
        get_all_used=False,
        tool_name="base_readQuery",
        narrowing_params=[],
    )
    assert "TOP" in md["hint"]
    assert "SAMPLE" in md["hint"]
    assert "WHERE" in md["hint"]


def test_truncation_hint_at_ceiling_recommends_persist():
    md = build_truncation_metadata(
        rows_returned=50000,
        row_limit=50000,
        hard_ceiling=50000,
        get_all_used=True,
        tool_name="dba_userSqlList",
        narrowing_params=["user_name"],
    )
    assert "ceiling" in md["hint"]
    assert "persist=true" in md["hint"]


def test_truncation_hint_no_narrowing_params_fallback():
    md = build_truncation_metadata(
        rows_returned=1000,
        row_limit=1000,
        hard_ceiling=50000,
        get_all_used=False,
        tool_name="some_tool_no_params",
        narrowing_params=[],
    )
    assert "get_all=true" in md["hint"]


# --------------------------------------------------------------------------
# _check_expectations (test runner assertion engine)
# --------------------------------------------------------------------------


def test_resolve_dot_path_basic():
    obj = {"a": {"b": {"c": 1}}}
    assert _resolve_dot_path(obj, "a.b.c") == (True, 1)
    assert _resolve_dot_path(obj, "a.b") == (True, {"c": 1})
    assert _resolve_dot_path(obj, "a.x") == (False, None)
    assert _resolve_dot_path(obj, "missing") == (False, None)


def test_check_expectations_pass_when_all_match():
    md = {"truncation": {"truncated": True, "row_limit": 1000, "hint": "pass get_all=true"}}
    err = _check_expectations({"truncation_present": True, "row_limit": 1000}, [{"x": 1}] * 1000, md)
    assert err is None


def test_check_expectations_truncation_present_mismatch():
    err = _check_expectations({"truncation_present": True}, [{"x": 1}], {})
    assert err is not None and "truncation_present" in err


def test_check_expectations_row_limit_mismatch():
    md = {"truncation": {"truncated": True, "row_limit": 500}}
    err = _check_expectations({"row_limit": 1000}, [], md)
    assert err is not None and "row_limit" in err


def test_check_expectations_results_count_strict():
    err = _check_expectations({"results_count": 1000}, [{"x": 1}] * 1000, {})
    assert err is None
    err = _check_expectations({"results_count": 999}, [{"x": 1}] * 1000, {})
    assert err is not None and "results_count" in err


def test_check_expectations_results_count_max():
    err = _check_expectations({"results_count_max": 50000}, [{"x": 1}] * 100, {})
    assert err is None
    err = _check_expectations({"results_count_max": 10}, [{"x": 1}] * 100, {})
    assert err is not None and "results_count_max" in err


def test_check_expectations_results_count_min():
    err = _check_expectations({"results_count_min": 50}, [{"x": 1}] * 100, {})
    assert err is None
    err = _check_expectations({"results_count_min": 200}, [{"x": 1}] * 100, {})
    assert err is not None and "results_count_min" in err


def test_check_expectations_dot_path_equality():
    md = {"truncation": {"row_limit": 1000, "get_all_used": True}}
    err = _check_expectations({"metadata.truncation.row_limit": 1000}, [], md)
    assert err is None
    err = _check_expectations({"metadata.truncation.row_limit": 500}, [], md)
    assert err is not None
    err = _check_expectations({"metadata.truncation.get_all_used": True}, [], md)
    assert err is None


def test_check_expectations_contains():
    md = {"truncation": {"hint": "Refine using parameters [user_name, no_days]"}}
    err = _check_expectations({"metadata.truncation.hint_contains": "user_name"}, [], md)
    assert err is None
    err = _check_expectations({"metadata.truncation.hint_contains": "banana"}, [], md)
    assert err is not None and "banana" in err


def test_check_expectations_absent_path():
    md_clean = {"tool_name": "foo"}
    err = _check_expectations({"metadata.truncation_absent": True}, [], md_clean)
    assert err is None
    md_dirty = {"truncation": {"truncated": True}}
    err = _check_expectations({"metadata.truncation_absent": True}, [], md_dirty)
    assert err is not None and "expected absent" in err


def test_check_expectations_dot_path_missing_with_value_expectation():
    md = {}
    err = _check_expectations({"metadata.truncation.row_limit": 1000}, [], md)
    assert err is not None and "missing" in err


def test_check_expectations_no_expect_block_passes():
    err = _check_expectations({}, [{"x": 1}] * 100, {})
    assert err is None
    err = _check_expectations(None, [{"x": 1}] * 100, {})
    assert err is None


# --------------------------------------------------------------------------
# Test runner
# --------------------------------------------------------------------------


def main() -> int:
    """Discover and run every ``test_*`` function in this module."""
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]
    print(f"Running {len(tests)} unit tests for row_cap helpers…")
    failed: list[tuple[str, str]] = []
    for name, fn in tests:
        try:
            fn()
        except AssertionError as e:
            failed.append((name, f"AssertionError: {e}" if str(e) else "AssertionError"))
            print(f"  ✗ {name}")
        except Exception as e:  # noqa: BLE001
            failed.append((name, f"{type(e).__name__}: {e}"))
            print(f"  ✗ {name}  ({type(e).__name__})")
        else:
            print(f"  ✓ {name}")

    print()
    print(f"Results: {len(tests) - len(failed)}/{len(tests)} passed")
    if failed:
        print()
        print("FAILURES:")
        for name, msg in failed:
            print(f"  - {name}: {msg}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
