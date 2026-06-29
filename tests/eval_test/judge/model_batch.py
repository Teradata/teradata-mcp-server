"""Model batch configuration and comparative reporting for eval runs."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from judge.report import RESULTS_DIR, _format_cost

BATCHES_DIR = RESULTS_DIR / "batches"
LATEST_BATCH_POINTER_FILE = RESULTS_DIR / "latest_batch.json"
LATEST_BATCH_MARKDOWN = RESULTS_DIR / "latest_batch_summary.md"
LATEST_BATCH_JSON = RESULTS_DIR / "latest_batch_summary.json"

PRICE_FIELDS = (
    "input_cost_per_1m_tokens",
    "output_cost_per_1m_tokens",
    "cache_read_input_cost_per_1m_tokens",
    "cache_write_input_cost_per_1m_tokens",
    "input_cost_per_1k_tokens",
    "output_cost_per_1k_tokens",
    "cache_read_input_cost_per_1k_tokens",
    "cache_write_input_cost_per_1k_tokens",
)


@dataclass
class ModelPricing:
    input_cost_per_1m_tokens: float | None = None
    output_cost_per_1m_tokens: float | None = None
    cache_read_input_cost_per_1m_tokens: float | None = None
    cache_write_input_cost_per_1m_tokens: float | None = None
    input_cost_per_1k_tokens: float | None = None
    output_cost_per_1k_tokens: float | None = None
    cache_read_input_cost_per_1k_tokens: float | None = None
    cache_write_input_cost_per_1k_tokens: float | None = None


@dataclass
class ModelConfig:
    model_id: str
    label: str
    pricing: ModelPricing = field(default_factory=ModelPricing)


@dataclass
class ModelBatchConfig:
    path: Path
    name: str
    judge: ModelConfig
    evaluated_models: list[ModelConfig]


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read --model-set YAML files. Run `uv sync`.") from exc

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w-]+", "-", text.strip().lower()).strip("-")
    return slug[:48] if slug else "model"


def _pricing_from_mapping(data: dict[str, Any]) -> ModelPricing:
    pricing_data = data.get("cost") or data.get("pricing") or {}
    if pricing_data is None:
        pricing_data = {}
    if not isinstance(pricing_data, dict):
        raise ValueError("model cost/pricing must be a mapping")

    merged = {field_name: data.get(field_name) for field_name in PRICE_FIELDS if field_name in data}
    merged.update({field_name: pricing_data.get(field_name) for field_name in PRICE_FIELDS if field_name in pricing_data})

    values: dict[str, float | None] = {}
    for field_name in PRICE_FIELDS:
        value = merged.get(field_name)
        if value is None or value == "":
            values[field_name] = None
            continue
        try:
            values[field_name] = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be numeric") from exc
    return ModelPricing(**values)


def _model_from_mapping(data: Any, *, default_label: str) -> ModelConfig:
    if isinstance(data, str):
        return ModelConfig(model_id=data, label=_slugify(default_label or data))
    if not isinstance(data, dict):
        raise ValueError("model entries must be strings or mappings")

    model_id = data.get("model") or data.get("model_id") or data.get("model_name") or data.get("name")
    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("model entry is missing `model`, `model_id`, or `model_name`")

    label = data.get("label") or data.get("id") or data.get("alias") or default_label
    if not isinstance(label, str) or not label.strip():
        label = model_id
    return ModelConfig(model_id=model_id.strip(), label=_slugify(label), pricing=_pricing_from_mapping(data))


def load_model_batch_config(path: str | Path) -> ModelBatchConfig:
    """Load a model-set YAML file used to run comparative eval batches."""
    config_path = Path(path)
    data = _load_yaml(config_path)

    judge_data = data.get("judge") or data.get("juge") or data.get("judge_model")
    if judge_data is None:
        raise ValueError("model-set YAML must define `judge`")
    judge = _model_from_mapping(judge_data, default_label="judge")

    models_data = data.get("evaluated_models") or data.get("models") or data.get("evaluated")
    if not isinstance(models_data, list) or not models_data:
        raise ValueError("model-set YAML must define a non-empty `evaluated_models` or `models` list")

    evaluated_models = [
        _model_from_mapping(model_data, default_label=f"model-{index}")
        for index, model_data in enumerate(models_data, start=1)
    ]
    name = data.get("name") or config_path.stem
    if not isinstance(name, str) or not name.strip():
        name = config_path.stem

    return ModelBatchConfig(
        path=config_path,
        name=_slugify(name),
        judge=judge,
        evaluated_models=evaluated_models,
    )


def cost_env_for_role(role: str, pricing: ModelPricing) -> dict[str, str]:
    """Return role-specific Bedrock cost env vars for a configured model."""
    prefix = f"BEDROCK_{role.upper()}"
    mapping = {
        f"{prefix}_INPUT_COST_PER_1M_TOKENS": pricing.input_cost_per_1m_tokens,
        f"{prefix}_OUTPUT_COST_PER_1M_TOKENS": pricing.output_cost_per_1m_tokens,
        f"{prefix}_CACHE_READ_INPUT_COST_PER_1M_TOKENS": pricing.cache_read_input_cost_per_1m_tokens,
        f"{prefix}_CACHE_WRITE_INPUT_COST_PER_1M_TOKENS": pricing.cache_write_input_cost_per_1m_tokens,
        f"{prefix}_INPUT_COST_PER_1K_TOKENS": pricing.input_cost_per_1k_tokens,
        f"{prefix}_OUTPUT_COST_PER_1K_TOKENS": pricing.output_cost_per_1k_tokens,
        f"{prefix}_CACHE_READ_INPUT_COST_PER_1K_TOKENS": pricing.cache_read_input_cost_per_1k_tokens,
        f"{prefix}_CACHE_WRITE_INPUT_COST_PER_1K_TOKENS": pricing.cache_write_input_cost_per_1k_tokens,
    }
    return {name: str(value) for name, value in mapping.items() if value is not None}


def cost_env_names_for_role(role: str) -> list[str]:
    prefix = f"BEDROCK_{role.upper()}"
    return [
        f"{prefix}_INPUT_COST_PER_1M_TOKENS",
        f"{prefix}_OUTPUT_COST_PER_1M_TOKENS",
        f"{prefix}_CACHE_READ_INPUT_COST_PER_1M_TOKENS",
        f"{prefix}_CACHE_WRITE_INPUT_COST_PER_1M_TOKENS",
        f"{prefix}_INPUT_COST_PER_1K_TOKENS",
        f"{prefix}_OUTPUT_COST_PER_1K_TOKENS",
        f"{prefix}_CACHE_READ_INPUT_COST_PER_1K_TOKENS",
        f"{prefix}_CACHE_WRITE_INPUT_COST_PER_1K_TOKENS",
    ]


def _pass_ratio(run: dict[str, Any]) -> float:
    total = int(run.get("total") or 0)
    if total == 0:
        return 0.0
    return float(run.get("passed") or 0) / total


def _token_total(run: dict[str, Any]) -> dict[str, Any]:
    token_usage = run.get("token_usage") or {}
    if isinstance(token_usage, dict) and isinstance(token_usage.get("total"), dict):
        return token_usage["total"]
    if isinstance(token_usage, dict):
        return token_usage
    return {}


def _render_batch_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Teradata MCP Eval Batch Summary",
        "",
        f"**Started (UTC):** {payload['started_at']}",
        f"**Model set:** {payload['model_set']}",
        f"**Judge model:** `{payload['judge_model_id']}`",
        f"**Module filter:** {payload['module_filter']}",
        f"**Case type filter:** {payload['case_type_filter']}",
        "",
        "## Runs",
        "",
        "| Evaluated model | Run | Passed | Failed | Total | Pass ratio | Cost |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for run in payload["runs"]:
        token_total = _token_total(run)
        ratio = _pass_ratio(run)
        summary_md = run.get("summary_md") or ""
        run_link = f"[{run.get('run_id', 'run')}]({summary_md})" if summary_md else str(run.get("run_id", "run"))
        lines.append(
            f"| `{run['agent_model_id']}` | {run_link} | {run.get('passed', 0)} | {run.get('failed', 0)} | "
            f"{run.get('total', 0)} | {ratio:.1%} | {_format_cost(token_total.get('cost_usd'))} |"
        )

    lines.extend(
        [
            "",
            "## Comparison",
            "",
            "| Rank | Evaluated model | Pass ratio | Cost | Total tokens | Calls |",
            "| ---: | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    ranked = sorted(
        payload["runs"],
        key=lambda run: (_pass_ratio(run), -float((_token_total(run).get("cost_usd") or 0.0))),
        reverse=True,
    )
    for index, run in enumerate(ranked, start=1):
        token_total = _token_total(run)
        lines.append(
            f"| {index} | `{run['agent_model_id']}` | {_pass_ratio(run):.1%} | "
            f"{_format_cost(token_total.get('cost_usd'))} | {token_total.get('total_tokens', 0)} | "
            f"{token_total.get('calls', 0)} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_batch_summary(
    *,
    model_set: ModelBatchConfig,
    module_filter: str,
    case_type_filter: str,
    run_label: str | None,
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Write comparative batch artifacts and return the batch pointer payload."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    BATCHES_DIR.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc).isoformat()
    timestamp = started_at.replace("+00:00", "Z").replace(":", "-")
    label = _slugify(run_label or model_set.name)
    batch_id = f"{timestamp}__{label}"
    batch_dir = BATCHES_DIR / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)

    normalized_runs = []
    for run in runs:
        normalized = dict(run)
        if isinstance(normalized.get("summary_md"), str):
            normalized["summary_md"] = f"../{normalized['summary_md']}"
        normalized_runs.append(normalized)

    payload = {
        "batch_id": batch_id,
        "started_at": started_at,
        "model_set": str(model_set.path),
        "judge_model_id": model_set.judge.model_id,
        "module_filter": module_filter,
        "case_type_filter": case_type_filter,
        "run_label": run_label,
        "runs": normalized_runs,
    }
    markdown = _render_batch_markdown(payload)

    summary_md = batch_dir / "summary.md"
    summary_json = batch_dir / "summary.json"
    summary_md.write_text(markdown + "\n", encoding="utf-8")
    summary_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    LATEST_BATCH_MARKDOWN.write_text(markdown + "\n", encoding="utf-8")
    LATEST_BATCH_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    pointer = {
        "batch_id": batch_id,
        "started_at": started_at,
        "batch_dir": f"batches/{batch_id}",
        "summary_md": f"batches/{batch_id}/summary.md",
        "summary_json": f"batches/{batch_id}/summary.json",
        "model_set": str(model_set.path),
        "judge_model_id": model_set.judge.model_id,
        "runs": [asdict(run) if hasattr(run, "__dataclass_fields__") else run for run in runs],
    }
    LATEST_BATCH_POINTER_FILE.write_text(json.dumps(pointer, indent=2) + "\n", encoding="utf-8")
    return pointer
