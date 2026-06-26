"""Run single-turn and shallow multi-turn eval cases."""

from __future__ import annotations

import os
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import Any

from deepeval import evaluate
from deepeval.evaluate import AsyncConfig, CacheConfig, DisplayConfig, ErrorConfig
from deepeval.test_case import ConversationalTestCase, LLMTestCase, ToolCall, Turn

from agent.client import run_agent, run_agent_turns
from judge.checks import EXACT_VALUE_KEYS, PRESENCE_ONLY_KEYS, ToolCallRecord, run_deterministic_checks
from judge.metrics import (
    conversational_clarification_metric,
    get_metrics,
    tool_correctness_metric,
)
from judge.report import CaseEvalResult, build_recommendation, record_case_result
from judge.usage import begin_case_usage, end_case_usage

MAX_TURNS = 7


def _extract_exception_detail(exc: Exception) -> str:
    """Extract detailed error message from exception, unwrapping ExceptionGroup if needed."""
    # For ExceptionGroup (TaskGroup errors), extract the first exception
    if hasattr(exc, 'exceptions') and exc.exceptions:
        # ExceptionGroup / TaskGroup
        first_exc = exc.exceptions[0]
        return _extract_exception_detail(first_exc)
    # For regular exceptions, include traceback context if available
    if hasattr(exc, '__cause__') and exc.__cause__:
        return f"{type(exc).__name__}: {str(exc)} (caused by {type(exc.__cause__).__name__}: {str(exc.__cause__)})"
    return f"{type(exc).__name__}: {str(exc)}"


def validate_multi_turn_case(case: dict) -> None:
    """Validate a shallow multi-turn case schema."""
    turns = case.get("turns")
    if turns is None:
        return

    if not isinstance(turns, list):
        raise ValueError(f"[{case.get('id')}] turns must be a list")

    if len(turns) < 2:
        raise ValueError(f"[{case.get('id')}] multi-turn cases need at least 2 turns")

    if len(turns) > MAX_TURNS:
        raise ValueError(f"[{case.get('id')}] multi-turn cases allow at most {MAX_TURNS} turns")

    for index, turn in enumerate(turns, start=1):
        is_clarification = turn.get("expect") == "clarification"
        has_tools = bool(turn.get("expected_tools"))
        if is_clarification == has_tools:
            raise ValueError(
                f"[{case.get('id')}] turn {index} must set exactly one of "
                "'expect': 'clarification' or non-empty 'expected_tools'",
            )
        if "input" not in turn:
            raise ValueError(f"[{case.get('id')}] turn {index} is missing 'input'")


def _to_tool_calls(records: list[ToolCallRecord]) -> list[ToolCall]:
    return [ToolCall(name=tc.name, input_parameters=tc.input_parameters) for tc in records]


def _tool_dicts(records: list[ToolCallRecord]) -> list[dict[str, Any]]:
    return [{"name": tc.name, "params": tc.input_parameters} for tc in records]


def _normalize_tool_params(
    expected_params: dict[str, Any],
    actual_params: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Normalize params for DeepEval's exact matcher without requiring exact SQL text."""
    expected_normalized: dict[str, Any] = {}
    actual_normalized: dict[str, Any] = {}

    for key, expected_value in expected_params.items():
        if key in PRESENCE_ONLY_KEYS:
            if expected_value:
                expected_normalized[key] = "__present__"
                actual_normalized[key] = "__present__" if actual_params.get(key) else "__missing__"
            continue

        if key in EXACT_VALUE_KEYS and expected_value not in ("", None):
            expected_normalized[key] = expected_value
            actual_normalized[key] = actual_params.get(key)
            continue

        expected_normalized[key] = expected_value
        actual_normalized[key] = actual_params.get(key)

    for key, actual_value in actual_params.items():
        if key not in expected_params:
            actual_normalized[key] = actual_value

    return expected_normalized, actual_normalized


def _make_tool_correctness_test_case(
    *,
    user_input: str,
    response: str,
    tools_called: list[ToolCallRecord],
    expected_tools_raw: list[dict[str, Any]],
) -> LLMTestCase:
    expected_tools: list[ToolCall] = []
    normalized_calls: list[ToolCall] = []

    for index, expected_tool in enumerate(expected_tools_raw):
        expected_name = expected_tool["name"]
        expected_params = expected_tool.get("params", {})
        actual_params = tools_called[index].input_parameters if index < len(tools_called) else {}
        expected_normalized, actual_normalized = _normalize_tool_params(expected_params, actual_params)
        expected_tools.append(ToolCall(name=expected_name, input_parameters=expected_normalized))

        if index < len(tools_called):
            normalized_calls.append(
                ToolCall(name=tools_called[index].name, input_parameters=actual_normalized),
            )

    for extra_call in tools_called[len(expected_tools_raw):]:
        normalized_calls.append(
            ToolCall(name=extra_call.name, input_parameters=extra_call.input_parameters),
        )

    return LLMTestCase(
        input=user_input,
        actual_output=response,
        tools_called=normalized_calls,
        expected_tools=expected_tools,
    )


def _make_conversational_test_case(
    *,
    previous_turns: list[Turn],
    user_input: str,
    response: str,
    case_id: str,
) -> ConversationalTestCase:
    return ConversationalTestCase(
        turns=[
            *previous_turns,
            Turn(role="user", content=user_input),
            Turn(role="assistant", content=response),
        ],
        scenario=f"{case_id}: missing required information before an MCP tool can be called",
        expected_outcome="The latest assistant turn asks the user for the missing information.",
    )


def _evaluate_metrics(
    test_case: LLMTestCase | ConversationalTestCase,
    metrics,
) -> tuple[list[str], bool]:
    stdout = StringIO()
    stderr = StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        evaluation = evaluate(
            test_cases=[test_case],
            metrics=metrics,
            error_config=ErrorConfig(ignore_errors=False, skip_on_missing_params=False),
            display_config=DisplayConfig(
                verbose_mode=False,
                show_indicator=False,
                print_results=False,
                inspect_after_run=False,
            ),
            cache_config=CacheConfig(write_cache=False, use_cache=False),
            async_config=AsyncConfig(run_async=False),
            identifier="eval",
        )
    test_result = evaluation.test_results[0]

    if test_result.success:
        return [], True

    reasons: list[str] = []
    for metric_data in test_result.metrics_data or []:
        if metric_data.error is not None or not metric_data.success:
            detail = metric_data.reason or metric_data.error or "metric failed"
            reasons.append(f"{metric_data.name}: {detail}")
    return reasons, False


def _failure_result(
    case: dict,
    *,
    case_input: str,
    failure_stage: str,
    failure_detail: str,
    expected_tools: list[dict[str, Any]] | None = None,
    actual_tools: list[dict[str, Any]] | None = None,
    actual_output: str | None = None,
    metric_reasons: list[str] | None = None,
    turn_details: list[dict[str, Any]] | None = None,
) -> CaseEvalResult:
    expected = expected_tools if expected_tools is not None else case.get("expected_tools", [])
    metric_reasons = metric_reasons or []
    recommendation = build_recommendation(
        case,
        failure_stage=failure_stage,
        failure_detail=failure_detail,
        expected_tools=expected,
        actual_tools=actual_tools,
        metric_reasons=metric_reasons,
    )
    return CaseEvalResult(
        case_id=case.get("id", "<unknown>"),
        case_type=case.get("type", "happy_path"),
        description=case.get("description", ""),
        input=case_input,
        expected_tools=expected,
        passed=False,
        failure_stage=failure_stage,
        failure_detail=failure_detail,
        actual_tools=actual_tools,
        actual_output=actual_output,
        metric_reasons=metric_reasons,
        recommendation=recommendation,
        turn_details=turn_details,
    )


def _success_result(
    case: dict,
    *,
    case_input: str,
    expected_tools: list[dict[str, Any]],
    actual_tools: list[dict[str, Any]],
    actual_output: str,
    turn_details: list[dict[str, Any]] | None = None,
) -> CaseEvalResult:
    return CaseEvalResult(
        case_id=case.get("id", "<unknown>"),
        case_type=case.get("type", "happy_path"),
        description=case.get("description", ""),
        input=case_input,
        expected_tools=expected_tools,
        passed=True,
        actual_tools=actual_tools,
        actual_output=actual_output,
        turn_details=turn_details,
    )


def run_single_turn_case(case: dict, bedrock_client, agent_model_id: str, judge_llm) -> CaseEvalResult:
    """Run a single-turn case and return a structured result."""
    validate_multi_turn_case(case)
    if "turns" in case:
        raise ValueError(f"[{case.get('id')}] use run_eval_case() for multi-turn cases")

    try:
        agent_result = run_agent(
            prompt=case["input"],
            model_id=agent_model_id,
            bedrock_client=bedrock_client,
        )
    except Exception as exc:
        return _failure_result(
            case,
            case_input=case["input"],
            failure_stage="agent",
            failure_detail=_extract_exception_detail(exc),
        )

    raw_calls = [
        ToolCallRecord(name=tc.name, input_parameters=tc.input_parameters)
        for tc in agent_result.tool_calls
    ]
    actual_tools = _tool_dicts(raw_calls)
    det_errors = run_deterministic_checks(case, raw_calls)
    if det_errors:
        return _failure_result(
            case,
            case_input=case["input"],
            failure_stage="deterministic",
            failure_detail="; ".join(det_errors),
            actual_tools=actual_tools,
            actual_output=agent_result.final_response,
        )

    test_case = _make_tool_correctness_test_case(
        user_input=case["input"],
        response=agent_result.final_response,
        tools_called=raw_calls,
        expected_tools_raw=case.get("expected_tools", []),
    )
    metric_reasons, passed = _evaluate_metrics(test_case, get_metrics(case, judge_llm))
    if not passed:
        return _failure_result(
            case,
            case_input=case["input"],
            failure_stage="metric",
            failure_detail="; ".join(metric_reasons),
            actual_tools=actual_tools,
            actual_output=agent_result.final_response,
            metric_reasons=metric_reasons,
        )

    return _success_result(
        case,
        case_input=case["input"],
        expected_tools=case.get("expected_tools", []),
        actual_tools=actual_tools,
        actual_output=agent_result.final_response,
    )


def run_multi_turn_case(case: dict, bedrock_client, agent_model_id: str, judge_llm) -> CaseEvalResult:
    """Run and score a shallow multi-turn case (2–7 turns)."""
    validate_multi_turn_case(case)
    turns = case["turns"]
    prompts = [turn["input"] for turn in turns]
    case_input = " | ".join(f"Turn {index}: {turn['input']}" for index, turn in enumerate(turns, start=1))

    max_steps_per_turn = int(os.environ.get("AGENT_MAX_STEPS_PER_TURN", "3"))
    try:
        turn_results = run_agent_turns(
            prompts=prompts,
            model_id=agent_model_id,
            bedrock_client=bedrock_client,
            max_steps_per_turn=max_steps_per_turn,
        )
    except Exception as exc:
        return _failure_result(
            case,
            case_input=case_input,
            failure_stage="agent",
            failure_detail=_extract_exception_detail(exc),
            expected_tools=[],
        )

    previous_turns: list[Turn] = []
    conversation_prefix = ""
    turn_details: list[dict[str, Any]] = []

    for turn_number, (turn_spec, turn_result) in enumerate(zip(turns, turn_results, strict=True), start=1):
        raw_calls = [
            ToolCallRecord(name=tc.name, input_parameters=tc.input_parameters)
            for tc in turn_result.tool_calls
        ]
        actual_tools = _tool_dicts(raw_calls)
        turn_label = f"{case.get('id')} turn {turn_number}"
        turn_input = f"{conversation_prefix}User: {turn_spec['input']}"

        if turn_spec.get("expect") == "clarification":
            pseudo_case = {"id": turn_label, "type": "missing_parameter", "expected_tools": []}
            det_errors = run_deterministic_checks(pseudo_case, raw_calls)
            if det_errors:
                turn_details.append(
                    {
                        "turn": turn_number,
                        "input": turn_spec["input"],
                        "mode": "clarification",
                        "passed": False,
                        "failure_stage": "deterministic",
                        "failure_detail": "; ".join(det_errors),
                        "actual_tools": actual_tools,
                    }
                )
                return _failure_result(
                    case,
                    case_input=case_input,
                    failure_stage="deterministic",
                    failure_detail=f"turn {turn_number}: {'; '.join(det_errors)}",
                    expected_tools=[],
                    actual_tools=actual_tools,
                    actual_output=turn_result.final_response,
                    turn_details=turn_details,
                )

            test_case = _make_conversational_test_case(
                previous_turns=previous_turns,
                user_input=turn_spec["input"],
                response=turn_result.final_response,
                case_id=case.get("id", "<unknown>"),
            )
            metric_reasons, passed = _evaluate_metrics(test_case, [conversational_clarification_metric(judge_llm)])
        else:
            expected_tools = turn_spec.get("expected_tools", [])
            pseudo_case = {
                "id": turn_label,
                "type": "happy_path",
                "expected_tools": expected_tools,
            }
            det_errors = run_deterministic_checks(pseudo_case, raw_calls)
            if det_errors:
                turn_details.append(
                    {
                        "turn": turn_number,
                        "input": turn_spec["input"],
                        "mode": "tool",
                        "passed": False,
                        "failure_stage": "deterministic",
                        "failure_detail": "; ".join(det_errors),
                        "expected_tools": expected_tools,
                        "actual_tools": actual_tools,
                    }
                )
                return _failure_result(
                    case,
                    case_input=case_input,
                    failure_stage="deterministic",
                    failure_detail=f"turn {turn_number}: {'; '.join(det_errors)}",
                    expected_tools=expected_tools,
                    actual_tools=actual_tools,
                    actual_output=turn_result.final_response,
                    turn_details=turn_details,
                )

            test_case = _make_tool_correctness_test_case(
                user_input=turn_input,
                response=turn_result.final_response,
                tools_called=raw_calls,
                expected_tools_raw=expected_tools,
            )
            metric_reasons, passed = _evaluate_metrics(test_case, [tool_correctness_metric(judge_llm)])

        if not passed:
            turn_details.append(
                {
                    "turn": turn_number,
                    "input": turn_spec["input"],
                    "mode": "clarification" if turn_spec.get("expect") == "clarification" else "tool",
                    "passed": False,
                    "failure_stage": "metric",
                    "failure_detail": "; ".join(metric_reasons),
                    "expected_tools": turn_spec.get("expected_tools", []),
                    "actual_tools": actual_tools,
                }
            )
            return _failure_result(
                case,
                case_input=case_input,
                failure_stage="metric",
                failure_detail=f"turn {turn_number}: {'; '.join(metric_reasons)}",
                expected_tools=turn_spec.get("expected_tools", []),
                actual_tools=actual_tools,
                actual_output=turn_result.final_response,
                metric_reasons=metric_reasons,
                turn_details=turn_details,
            )

        turn_details.append(
            {
                "turn": turn_number,
                "input": turn_spec["input"],
                "mode": "clarification" if turn_spec.get("expect") == "clarification" else "tool",
                "passed": True,
                "actual_tools": actual_tools,
            }
        )
        previous_turns.extend(
            [
                Turn(role="user", content=turn_spec["input"]),
                Turn(role="assistant", content=turn_result.final_response, tools_called=_to_tool_calls(raw_calls)),
            ],
        )
        conversation_prefix += f"User: {turn_spec['input']}\nAssistant: {turn_result.final_response}\n"

    last_turn = turn_results[-1]
    last_tools = [
        ToolCallRecord(name=tc.name, input_parameters=tc.input_parameters)
        for tc in last_turn.tool_calls
    ]
    return _success_result(
        case,
        case_input=case_input,
        expected_tools=turns[-1].get("expected_tools", []),
        actual_tools=_tool_dicts(last_tools),
        actual_output=last_turn.final_response,
        turn_details=turn_details,
    )


def run_eval_case(case: dict, bedrock_client, agent_model_id: str, judge_llm) -> CaseEvalResult:
    """Run any eval case and return a structured result."""
    validate_multi_turn_case(case)
    if "turns" in case:
        return run_multi_turn_case(case, bedrock_client, agent_model_id, judge_llm)
    return run_single_turn_case(case, bedrock_client, agent_model_id, judge_llm)


def build_test_case(case: dict, bedrock_client, agent_model_id: str) -> LLMTestCase:
    """Run a single-turn case and return a deepeval LLMTestCase (metrics not scored)."""
    validate_multi_turn_case(case)
    if "turns" in case:
        raise ValueError(f"[{case.get('id')}] use assert_eval_case() for multi-turn cases")

    agent_result = run_agent(
        prompt=case["input"],
        model_id=agent_model_id,
        bedrock_client=bedrock_client,
    )
    raw_calls = [
        ToolCallRecord(name=tc.name, input_parameters=tc.input_parameters)
        for tc in agent_result.tool_calls
    ]
    det_errors = run_deterministic_checks(case, raw_calls)
    if det_errors:
        case_id = case.get("id", "<unknown>")
        raise AssertionError(f"[{case_id}] deterministic check failed: {'; '.join(det_errors)}")

    return _make_tool_correctness_test_case(
        user_input=case["input"],
        response=agent_result.final_response,
        tools_called=raw_calls,
        expected_tools_raw=case.get("expected_tools", []),
    )


def assert_eval_case(case: dict, bedrock_client, agent_model_id: str, judge_llm) -> None:
    """Run and score any eval case (single- or multi-turn)."""
    usage_token = begin_case_usage()
    try:
        result = run_eval_case(case, bedrock_client, agent_model_id, judge_llm)
    finally:
        usage_summary = end_case_usage(usage_token)
    result.token_usage = usage_summary.to_dict()
    record_case_result(result)
    if not result.passed:
        detail = result.failure_detail or "; ".join(result.metric_reasons) or "eval case failed"
        raise AssertionError(f"[{result.case_id}] {result.failure_stage} check failed: {detail}")
