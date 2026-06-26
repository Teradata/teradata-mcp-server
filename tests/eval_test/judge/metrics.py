"""deepeval metrics for the Teradata MCP eval suite."""

from __future__ import annotations

from deepeval.metrics import ConversationalGEval, GEval, ToolCorrectnessMetric
from deepeval.test_case import MultiTurnParams, SingleTurnParams, ToolCallParams


def _enable_custom_cost_tracking(metric, judge_llm):
    if getattr(judge_llm, "returns_token_cost", False):
        metric.using_native_model = True
    return metric


def tool_correctness_metric(judge_llm) -> ToolCorrectnessMetric:
    """Evaluates tool selection accuracy and parameter correctness via LLM judge."""
    return _enable_custom_cost_tracking(ToolCorrectnessMetric(
        threshold=1.0,
        evaluation_params=[ToolCallParams.INPUT_PARAMETERS],
        model=judge_llm,
        include_reason=True,
        should_exact_match=True,
    ), judge_llm)


def clarification_metric(judge_llm) -> GEval:
    """For missing_parameter cases: checks the agent asked for clarification rather than hallucinating."""
    return _enable_custom_cost_tracking(GEval(
        name="Clarification Check",
        criteria=(
            "The agent was given a prompt that is missing a required parameter. "
            "The agent should ask the user for the missing information rather than "
            "inventing a value or proceeding with a guess. "
            "Score 1.0 if the response contains a clear request for the missing information. "
            "Score 0.0 if the agent fabricated a parameter value or called a tool without asking."
        ),
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
        ],
        model=judge_llm,
        threshold=0.5,
    ), judge_llm)


def conversational_clarification_metric(judge_llm) -> ConversationalGEval:
    """For multi-turn clarification turns: checks the latest assistant turn asks for missing info."""
    return _enable_custom_cost_tracking(ConversationalGEval(
        name="Clarification Check",
        criteria=(
            "Evaluate the latest assistant turn in the conversation. The user request is missing "
            "required information for a tool call, so the assistant should ask a clear clarification "
            "question for the missing information instead of inventing a value or proceeding with a guess. "
            "Score 1.0 if the latest assistant turn asks for the missing information. "
            "Score 0.0 if it fabricates a parameter value or proceeds without asking."
        ),
        evaluation_params=[
            MultiTurnParams.CONTENT,
            MultiTurnParams.ROLE,
            MultiTurnParams.SCENARIO,
            MultiTurnParams.EXPECTED_OUTCOME,
        ],
        model=judge_llm,
        threshold=0.5,
    ), judge_llm)


def get_metrics(case: dict, judge_llm) -> list:
    """Return the appropriate metric set for a given test case type."""
    metrics = [tool_correctness_metric(judge_llm)]
    if case.get("type") == "missing_parameter":
        metrics.append(clarification_metric(judge_llm))
    return metrics
