"""Unit tests for opt-in description override loading."""

import json

from agent.client import (
    _apply_description_overrides,
    _load_description_overrides,
    description_overrides_enabled,
    get_description_override_status,
    resolve_description_overrides_file,
)


class _FakeTool:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.inputSchema = {}

    def model_copy(self, *, update: dict):
        return _FakeTool(self.name, update.get("description", self.description))


def test_overrides_disabled_by_default(monkeypatch, tmp_path):
    overrides_file = tmp_path / "description_overrides.json"
    overrides_file.write_text(json.dumps({"base_readQuery": "override text"}))
    monkeypatch.delenv("USE_DESCRIPTION_OVERRIDES", raising=False)
    monkeypatch.delenv("DESCRIPTION_OVERRIDES_FILE", raising=False)

    assert description_overrides_enabled() is False
    assert _load_description_overrides() == {}
    assert get_description_override_status()["mode"] == "mcp_server"


def test_overrides_enabled_with_flag(monkeypatch, tmp_path):
    overrides_file = tmp_path / "description_overrides.json"
    overrides_file.write_text(json.dumps({"base_readQuery": "override text"}))
    monkeypatch.setenv("USE_DESCRIPTION_OVERRIDES", "1")
    monkeypatch.setenv("DESCRIPTION_OVERRIDES_FILE", str(overrides_file))

    assert description_overrides_enabled() is True
    assert _load_description_overrides() == {"base_readQuery": "override text"}
    status = get_description_override_status()
    assert status["mode"] == "overrides"
    assert status["tool_count"] == 1


def test_apply_description_overrides_patches_matching_tools():
    tools = [_FakeTool("base_readQuery", "live description")]
    patched = _apply_description_overrides(tools, {"base_readQuery": "patched description"})
    assert patched[0].description == "patched description"


def test_resolve_description_overrides_file_requires_enablement(monkeypatch):
    monkeypatch.delenv("USE_DESCRIPTION_OVERRIDES", raising=False)
    monkeypatch.delenv("DESCRIPTION_OVERRIDES_FILE", raising=False)
    assert resolve_description_overrides_file() is None
