from __future__ import annotations

from types import SimpleNamespace

import pytest

from activate import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL_ALIAS,
    DEFAULT_MODEL_NAME,
    DEFAULT_PROVIDER_NAME,
    _configure_morph_compaction,
    _resolve_api_key,
    _set_compaction_plugin,
)


def test_set_compaction_plugin_preserves_existing_config() -> None:
    existing = '[providers.foo]\nbase_url = "https://example.com"\n\n[loop_control]\nreserved_context_size = 50000\n'

    updated = _set_compaction_plugin(existing)

    assert 'compaction_plugin = "morph-plugin"' in updated
    assert 'reserved_context_size = 50000' in updated
    assert '[providers.foo]' in updated


def test_configure_morph_compaction_adds_provider_model_and_loop_control() -> None:
    args = SimpleNamespace(
        api_key="test-key",
        api_key_env=None,
        provider_name=DEFAULT_PROVIDER_NAME,
        model_alias=DEFAULT_MODEL_ALIAS,
        model_name=DEFAULT_MODEL_NAME,
        base_url=DEFAULT_BASE_URL,
        max_context_size=128000,
    )

    updated = _configure_morph_compaction("", args)

    assert '[providers.morph]' in updated
    assert 'type = "openai_legacy"' in updated
    assert 'base_url = "https://api.morphllm.com/v1"' in updated
    assert 'api_key = "test-key"' in updated
    assert '[models.morph-compaction]' in updated
    assert 'provider = "morph"' in updated
    assert 'model = "morph-compactor"' in updated
    assert 'max_context_size = 128000' in updated
    assert '[loop_control]' in updated
    assert 'compaction_model = "morph-compaction"' in updated
    assert 'compaction_plugin = "morph-plugin"' in updated


def test_configure_morph_compaction_updates_existing_sections_without_duplicates() -> None:
    existing = """[providers.morph]\napi_key = \"old-key\"\n\n[models.morph-compaction]\nmodel = \"old-model\"\n\n[loop_control]\ncompaction_model = \"old-alias\"\ncompaction_plugin = \"old-plugin\"\n"""
    args = SimpleNamespace(
        api_key="new-key",
        api_key_env=None,
        provider_name=DEFAULT_PROVIDER_NAME,
        model_alias=DEFAULT_MODEL_ALIAS,
        model_name=DEFAULT_MODEL_NAME,
        base_url=DEFAULT_BASE_URL,
        max_context_size=128000,
    )

    updated = _configure_morph_compaction(existing, args)

    assert updated.count('[providers.morph]') == 1
    assert updated.count('[models.morph-compaction]') == 1
    assert updated.count('[loop_control]') == 1
    assert 'api_key = "new-key"' in updated
    assert 'model = "morph-compactor"' in updated
    assert 'compaction_model = "morph-compaction"' in updated
    assert 'compaction_plugin = "morph-plugin"' in updated
    assert 'old-key' not in updated
    assert 'old-model' not in updated
    assert 'old-plugin' not in updated


def test_resolve_api_key_prefers_explicit_value(monkeypatch) -> None:
    monkeypatch.setenv("MORPH_API_KEY", "env-key")

    args = SimpleNamespace(api_key="arg-key", api_key_env=None)

    assert _resolve_api_key(args) == "arg-key"


def test_resolve_api_key_reads_custom_env_name(monkeypatch) -> None:
    monkeypatch.delenv("MORPH_API_KEY", raising=False)
    monkeypatch.setenv("PLUGIN_MORPH_KEY", "env-key")

    args = SimpleNamespace(api_key=None, api_key_env="PLUGIN_MORPH_KEY")

    assert _resolve_api_key(args) == "env-key"


def test_configure_morph_compaction_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("MORPH_API_KEY", raising=False)

    args = SimpleNamespace(
        api_key=None,
        api_key_env=None,
        provider_name=DEFAULT_PROVIDER_NAME,
        model_alias=DEFAULT_MODEL_ALIAS,
        model_name=DEFAULT_MODEL_NAME,
        base_url=DEFAULT_BASE_URL,
        max_context_size=128000,
    )

    with pytest.raises(SystemExit, match="requires an API key"):
        _configure_morph_compaction("", args)
