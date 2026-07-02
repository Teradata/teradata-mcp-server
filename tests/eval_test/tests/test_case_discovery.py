from tests.generated_cases import iter_module_case_specs
from tests.case_runner import _evaluate_metrics, _make_tool_correctness_test_case
from judge.checks import ToolCallRecord
from judge.metrics import tool_correctness_metric
from deepeval.models.base_model import DeepEvalBaseLLM
import pytest
from judge.report import CaseEvalResult, EvalRunReport, _summary_payload, render_markdown
from judge.usage import calculate_bedrock_cost_usd
from judge.model_batch import _render_batch_markdown, cost_env_for_role, load_model_batch_config


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


def test_token_usage_summary_includes_case_and_run_totals(monkeypatch):
    monkeypatch.setenv("BEDROCK_AGENT_INPUT_COST_PER_1M_TOKENS", "3")
    monkeypatch.setenv("BEDROCK_AGENT_OUTPUT_COST_PER_1M_TOKENS", "15")

    cost = calculate_bedrock_cost_usd(
        "agent-model",
        "agent",
        {
            "inputTokens": 100,
            "outputTokens": 20,
            "cacheReadInputTokens": 5,
            "cacheWriteInputTokens": 7,
            "totalTokens": 132,
        },
    )
    assert cost == pytest.approx(0.0006)

    case_usage = {
        "total": {
            "model_id": None,
            "role": "all",
            "calls": 1,
            "input_tokens": 100,
            "output_tokens": 20,
            "cache_read_input_tokens": 5,
            "cache_write_input_tokens": 7,
            "total_tokens": 132,
            "cost_usd": cost,
        },
        "by_model": [
            {
                "model_id": "agent-model",
                "role": "agent",
                "calls": 1,
                "input_tokens": 100,
                "output_tokens": 20,
                "cache_read_input_tokens": 5,
                "cache_write_input_tokens": 7,
                "total_tokens": 132,
                "cost_usd": cost,
            }
        ],
    }
    report = EvalRunReport(
        started_at="2026-06-26T00:00:00+00:00",
        module_filter="base",
        case_type_filter="all",
        agent_model_id="agent-model",
        judge_model_id="judge-model",
        evals_database="evals",
    )
    report.results.append(
        CaseEvalResult(
            case_id="case1",
            case_type="happy_path",
            description="description",
            input="prompt",
            expected_tools=[],
            passed=True,
            token_usage=case_usage,
        )
    )

    payload = _summary_payload(report)
    assert payload["cases"][0]["token_usage"]["total"]["input_tokens"] == 100
    assert payload["token_usage"]["total"]["total_tokens"] == 132
    assert payload["token_usage"]["total"]["cost_usd"] == pytest.approx(0.0006)
    assert "| agent | `agent-model` | 1 | 100 | 20 | 5 | 7 | 132 | $0.000600 |" in render_markdown(report)


def test_model_batch_config_loads_models_and_costs(tmp_path):
    config_path = tmp_path / "models.yml"
    config_path.write_text(
        """
name: bedrock-comparison
judge:
  model: judge-model
  cost:
    input_cost_per_1m_tokens: 3
    output_cost_per_1m_tokens: 15
models:
  - label: sonnet
    model: agent-sonnet
    cost:
      input_cost_per_1m_tokens: 2
      output_cost_per_1m_tokens: 10
  - model_name: agent-haiku
""",
        encoding="utf-8",
    )

    config = load_model_batch_config(config_path)

    assert config.name == "bedrock-comparison"
    assert config.judge.model_id == "judge-model"
    assert config.evaluated_models[0].label == "sonnet"
    assert config.evaluated_models[1].model_id == "agent-haiku"
    assert cost_env_for_role("agent", config.evaluated_models[0].pricing) == {
        "BEDROCK_AGENT_INPUT_COST_PER_1M_TOKENS": "2.0",
        "BEDROCK_AGENT_OUTPUT_COST_PER_1M_TOKENS": "10.0",
    }


def test_batch_markdown_links_runs_and_ranks_by_pass_ratio():
    markdown = _render_batch_markdown(
        {
            "started_at": "2026-06-26T00:00:00+00:00",
            "model_set": "models.yml",
            "judge_model_id": "judge-model",
            "module_filter": "base",
            "case_type_filter": "all",
            "runs": [
                {
                    "run_id": "run-a",
                    "summary_md": "../runs/run-a/summary.md",
                    "agent_model_id": "agent-a",
                    "passed": 8,
                    "failed": 2,
                    "total": 10,
                    "token_usage": {"cost_usd": 0.12, "total_tokens": 1000, "calls": 20},
                },
                {
                    "run_id": "run-b",
                    "summary_md": "../runs/run-b/summary.md",
                    "agent_model_id": "agent-b",
                    "passed": 9,
                    "failed": 1,
                    "total": 10,
                    "token_usage": {"cost_usd": 0.25, "total_tokens": 2000, "calls": 25},
                },
            ],
        }
    )

    assert "[run-a](../runs/run-a/summary.md)" in markdown
    assert "| `agent-b` | [run-b](../runs/run-b/summary.md) | 9 | 1 | 10 | 90.0% | $0.250000 |" in markdown
    assert "| 1 | `agent-b` | 90.0% | $0.250000 | 2000 | 25 |" in markdown
