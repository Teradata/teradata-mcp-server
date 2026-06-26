"""deepeval metrics for the Teradata MCP eval suite."""

from __future__ import annotations

from deepeval.metrics import GEval, ToolCorrectnessMetric
from deepeval.test_case import LLMTestCaseParams


def tool_correctness_metric(judge_llm) -> ToolCorrectnessMetric:
    """Evaluates tool selection accuracy and parameter correctness via LLM judge."""
    return ToolCorrectnessMetric(
        threshold=0.5,
        model=judge_llm,
        include_reason=True,
    )


def clarification_metric(judge_llm) -> GEval:
    """For missing_parameter cases: checks the agent asked for clarification rather than hallucinating."""
    return GEval(
        name="Clarification Check",
        criteria=(
            "The agent was given a prompt that is missing a required parameter. "
            "The agent should ask the user for the missing information rather than "
            "inventing a value or proceeding with a guess. "
            "Score 1.0 if the response contains a clear request for the missing information. "
            "Score 0.0 if the agent fabricated a parameter value or called a tool without asking."
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        model=judge_llm,
        threshold=0.5,
    )


def get_metrics(case: dict, judge_llm) -> list:
    """Return the appropriate metric set for a given test case type."""
    metrics = [tool_correctness_metric(judge_llm)]
    if case.get("type") == "missing_parameter":
        metrics.append(clarification_metric(judge_llm))
    return metrics
