from tests.generated_cases import iter_module_case_specs
from tests.case_runner import _evaluate_metrics, _make_tool_correctness_test_case
from judge.checks import ToolCallRecord
from judge.metrics import tool_correctness_metric
from deepeval.models.base_model import DeepEvalBaseLLM


class DummyLLM(DeepEvalBaseLLM):
    def load_model(self):
        return None

    def generate(self, prompt: str, schema=None):
        return "{}"

    async def a_generate(self, prompt: str, schema=None):
        return "{}"

    def get_model_name(self) -> str:
        return "dummy"


def test_iter_module_case_specs_includes_base_cases():
    specs = list(iter_module_case_specs("base"))
    assert specs
    assert all(spec["module"] == "base" for spec in specs)


def test_iter_module_case_specs_filters_by_type():
    specs = list(iter_module_case_specs("base", case_type="ambiguous_selection"))
    assert specs
    assert all(spec["case"].get("type") == "ambiguous_selection" for spec in specs)


def test_tool_correctness_rejects_wrong_params_and_extra_tools():
    expected_tools = [
        {
            "name": "base_tableList",
            "params": {
                "database_name": "evals_db",
                "sql": "SELECT * FROM evals_db.evals_employees",
            },
        }
    ]
    metric = tool_correctness_metric(DummyLLM())

    matching_case = _make_tool_correctness_test_case(
        user_input="List tables",
        response="Called table list.",
        tools_called=[
            ToolCallRecord(
                name="base_tableList",
                input_parameters={"database_name": "evals_db", "sql": "SELECT database_name FROM dbc.tablesv"},
            )
        ],
        expected_tools_raw=expected_tools,
    )
    reasons, passed = _evaluate_metrics(matching_case, [metric])
    assert passed, reasons

    wrong_param_case = _make_tool_correctness_test_case(
        user_input="List tables",
        response="Called table list.",
        tools_called=[
            ToolCallRecord(
                name="base_tableList",
                input_parameters={"database_name": "wrong_db", "sql": "SELECT database_name FROM dbc.tablesv"},
            )
        ],
        expected_tools_raw=expected_tools,
    )
    assert _evaluate_metrics(wrong_param_case, [metric])[1] is False

    extra_tool_case = _make_tool_correctness_test_case(
        user_input="List tables",
        response="Called table list.",
        tools_called=[
            ToolCallRecord(
                name="base_tableList",
                input_parameters={"database_name": "evals_db", "sql": "SELECT database_name FROM dbc.tablesv"},
            ),
            ToolCallRecord(name="base_databaseList", input_parameters={}),
        ],
        expected_tools_raw=expected_tools,
    )
    assert _evaluate_metrics(extra_tool_case, [metric])[1] is False
