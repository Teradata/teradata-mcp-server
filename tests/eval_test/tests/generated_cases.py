from __future__ import annotations

import os
from typing import Any

import pytest

from tests.case_runner import assert_eval_case as case_runner_assert_eval_case
from tests.conftest import MODULES, _substitute, load_cases


def _case_type_matches(case: dict[str, Any], case_type: str | None) -> bool:
    if not case_type or case_type.lower() in {"all", ""}:
        return True

    normalized_filter = case_type.lower().replace("_", "")
    normalized_type = str(case.get("type", "")).lower().replace("_", "")
    normalized_id = str(case.get("id", "")).lower().replace("_", "")
    return normalized_filter in normalized_type or normalized_filter in normalized_id


def iter_module_case_specs(module: str, case_type: str | None = None) -> list[dict[str, Any]]:
    requested_module = (module or "").strip().lower()
    if requested_module in {"", "all"}:
        modules_to_scan = list(MODULES)
    elif requested_module in MODULES:
        modules_to_scan = [requested_module]
    else:
        raise ValueError(f"Unsupported module {module!r}; expected one of {MODULES}")

    specs: list[dict[str, Any]] = []
    for module_name in modules_to_scan:
        for case in load_cases(module_name):
            if _case_type_matches(case, case_type):
                specs.append({"module": module_name, "case": case})
    return specs


def _register_module_tests() -> None:
    requested_module = os.environ.get("EVALS_RUN_MODULE", "all").strip().lower()
    requested_type = os.environ.get("EVALS_RUN_TYPE", "all").strip()

    modules_to_register = [requested_module] if requested_module not in {"", "all"} else list(MODULES)

    for module_name in modules_to_register:
        if module_name not in MODULES:
            continue

        specs = iter_module_case_specs(module_name, requested_type)
        if not specs:
            @pytest.mark.skip(reason=f"No eval cases exist for module {module_name}")
            def _empty_module_test() -> None:
                return None

            _empty_module_test.__name__ = f"test_{module_name}"
            globals()[f"test_{module_name}"] = _empty_module_test
            continue

        params = [
            pytest.param(
                spec,
                id=f"{spec['module']}:{spec['case'].get('id')}:{spec['case'].get('type')}",
            )
            for spec in specs
        ]

        def _module_test(case_spec, bedrock_client, agent_model_id, judge_llm) -> None:
            evals_db = os.environ.get("EVALS_DATABASE", "").strip()
            resolved_case = _substitute(case_spec["case"], evals_db)
            case_runner_assert_eval_case(resolved_case, bedrock_client, agent_model_id, judge_llm)

        _module_test.__name__ = f"test_{module_name}"
        _module_test = pytest.mark.parametrize("case_spec", params)(_module_test)
        globals()[f"test_{module_name}"] = _module_test


_register_module_tests()
