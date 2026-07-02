"""Unit tests for deterministic structural checks."""

from judge.checks import ToolCallRecord, assert_deterministic_checks, run_deterministic_checks


def _call(name: str, **params) -> ToolCallRecord:
    return ToolCallRecord(name=name, input_parameters=params)


def test_missing_parameter_rejects_tool_calls():
    case = {"id": "test", "type": "missing_parameter", "expected_tools": []}
    errors = run_deterministic_checks(case, [_call("base_readQuery", sql="SELECT 1")])
    assert len(errors) == 1
    assert "no tool calls" in errors[0]


def test_happy_path_checks_tool_name_and_exact_params():
    case = {
        "id": "test",
        "type": "happy_path",
        "expected_tools": [
            {
                "name": "base_tableList",
                "params": {"database_name": "mydb"},
            }
        ],
    }
    assert not run_deterministic_checks(
        case,
        [_call("base_tableList", database_name="mydb")],
    )
    errors = run_deterministic_checks(
        case,
        [_call("base_tablePreview", database_name="mydb", table_name="t")],
    )
    assert any("base_tableList" in e for e in errors)


def test_multi_tool_enforces_order_and_count():
    case = {
        "id": "test",
        "type": "multi_tool",
        "expected_tools": [
            {"name": "base_tableList", "params": {"database_name": "mydb"}},
            {"name": "base_tablePreview", "params": {"database_name": "mydb", "table_name": "evals_employees"}},
        ],
    }
    ok_calls = [
        _call("base_tableList", database_name="mydb"),
        _call("base_tablePreview", database_name="mydb", table_name="evals_employees"),
    ]
    assert not run_deterministic_checks(case, ok_calls)

    wrong_order = list(reversed(ok_calls))
    errors = run_deterministic_checks(case, wrong_order)
    assert any("step 1" in e for e in errors)


def test_sql_param_presence_only():
    case = {
        "id": "test",
        "type": "happy_path",
        "expected_tools": [
            {
                "name": "base_readQuery",
                "params": {"sql": "SELECT 1"},
            }
        ],
    }
    assert not run_deterministic_checks(
        case,
        [_call("base_readQuery", sql="SELECT 2")],
    )


def test_assert_raises_on_failure():
    case = {"id": "bad", "type": "missing_parameter", "expected_tools": []}
    try:
        assert_deterministic_checks(case, [_call("base_readQuery")])
        raise AssertionError("expected assertion")
    except AssertionError as exc:
        assert "bad" in str(exc)
