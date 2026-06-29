"""Token usage and cost accounting for Bedrock-backed eval runs."""

from __future__ import annotations

import os
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any


_CURRENT_CASE_USAGE: ContextVar["TokenUsageSummary | None"] = ContextVar(
    "eval_case_token_usage",
    default=None,
)


def _env_float(name: str) -> float:
    value = os.environ.get(name, "").strip()
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def _model_env_key(model_id: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in model_id.upper())


def _price_per_token(model_id: str, role: str, token_type: str) -> float:
    """Return configured price per token, accepting per-1K or per-1M env vars."""
    model_key = _model_env_key(model_id)
    role_key = role.upper()
    token_key = token_type.upper()
    per_1m = (
        _env_float(f"BEDROCK_{role_key}_{token_key}_COST_PER_1M_TOKENS")
        or _env_float(f"BEDROCK_{model_key}_{token_key}_COST_PER_1M_TOKENS")
        or _env_float(f"BEDROCK_{token_key}_COST_PER_1M_TOKENS")
    )
    if per_1m:
        return per_1m / 1_000_000

    per_1k = (
        _env_float(f"BEDROCK_{role_key}_{token_key}_COST_PER_1K_TOKENS")
        or _env_float(f"BEDROCK_{model_key}_{token_key}_COST_PER_1K_TOKENS")
        or _env_float(f"BEDROCK_{token_key}_COST_PER_1K_TOKENS")
    )
    return per_1k / 1_000 if per_1k else 0.0


@dataclass
class ModelTokenUsage:
    model_id: str
    role: str
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_write_input_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float | None = None

    def add_usage(self, usage: dict[str, Any], cost_usd: float | None) -> None:
        self.calls += 1
        self.input_tokens += int(usage.get("inputTokens") or 0)
        self.output_tokens += int(usage.get("outputTokens") or 0)
        self.cache_read_input_tokens += int(usage.get("cacheReadInputTokens") or 0)
        self.cache_write_input_tokens += int(usage.get("cacheWriteInputTokens") or 0)
        self.total_tokens += int(usage.get("totalTokens") or 0)
        if cost_usd is not None:
            self.cost_usd = (self.cost_usd or 0.0) + cost_usd


@dataclass
class TokenUsageSummary:
    by_model: dict[str, ModelTokenUsage] = field(default_factory=dict)

    def add(self, *, model_id: str, role: str, usage: dict[str, Any], cost_usd: float | None) -> None:
        key = f"{role}:{model_id}"
        if key not in self.by_model:
            self.by_model[key] = ModelTokenUsage(model_id=model_id, role=role)
        self.by_model[key].add_usage(usage, cost_usd)

    def merge(self, other: "TokenUsageSummary | None") -> None:
        if other is None:
            return
        for item in other.by_model.values():
            self.add(
                model_id=item.model_id,
                role=item.role,
                usage={
                    "inputTokens": item.input_tokens,
                    "outputTokens": item.output_tokens,
                    "cacheReadInputTokens": item.cache_read_input_tokens,
                    "cacheWriteInputTokens": item.cache_write_input_tokens,
                    "totalTokens": item.total_tokens,
                },
                cost_usd=item.cost_usd,
            )
            self.by_model[f"{item.role}:{item.model_id}"].calls += item.calls - 1

    def to_dict(self) -> dict[str, Any]:
        totals = ModelTokenUsage(model_id="__total__", role="all")
        for item in self.by_model.values():
            totals.calls += item.calls
            totals.input_tokens += item.input_tokens
            totals.output_tokens += item.output_tokens
            totals.cache_read_input_tokens += item.cache_read_input_tokens
            totals.cache_write_input_tokens += item.cache_write_input_tokens
            totals.total_tokens += item.total_tokens
            if item.cost_usd is not None:
                totals.cost_usd = (totals.cost_usd or 0.0) + item.cost_usd

        return {
            "total": asdict(totals) | {"model_id": None, "role": "all"},
            "by_model": [asdict(item) for item in sorted(self.by_model.values(), key=lambda usage: (usage.role, usage.model_id))],
        }


def calculate_bedrock_cost_usd(model_id: str, role: str, usage: dict[str, Any]) -> float | None:
    input_cost = int(usage.get("inputTokens") or 0) * _price_per_token(model_id, role, "INPUT")
    output_cost = int(usage.get("outputTokens") or 0) * _price_per_token(model_id, role, "OUTPUT")
    cache_read_cost = int(usage.get("cacheReadInputTokens") or 0) * _price_per_token(model_id, role, "CACHE_READ_INPUT")
    cache_write_cost = int(usage.get("cacheWriteInputTokens") or 0) * _price_per_token(model_id, role, "CACHE_WRITE_INPUT")
    total = input_cost + output_cost + cache_read_cost + cache_write_cost
    return total if total else None


def record_bedrock_usage(*, model_id: str, role: str, response: dict[str, Any]) -> float | None:
    usage = response.get("usage") or {}
    if not isinstance(usage, dict):
        return None
    cost_usd = calculate_bedrock_cost_usd(model_id, role, usage)
    current = _CURRENT_CASE_USAGE.get()
    if current is not None:
        current.add(model_id=model_id, role=role, usage=usage, cost_usd=cost_usd)
    return cost_usd


def begin_case_usage() -> object:
    return _CURRENT_CASE_USAGE.set(TokenUsageSummary())


def end_case_usage(token: object) -> TokenUsageSummary:
    current = _CURRENT_CASE_USAGE.get() or TokenUsageSummary()
    snapshot = deepcopy(current)
    _CURRENT_CASE_USAGE.reset(token)
    return snapshot
