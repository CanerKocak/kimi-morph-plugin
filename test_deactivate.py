from __future__ import annotations

from types import SimpleNamespace

from activate import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL_ALIAS,
    DEFAULT_MODEL_NAME,
    DEFAULT_PROVIDER_NAME,
    _configure_morph_compaction,
)
from deactivate import _deactivate_config


def _bootstrap_args() -> SimpleNamespace:
    return SimpleNamespace(
        api_key="test-key",
        api_key_env=None,
        provider_name=DEFAULT_PROVIDER_NAME,
        model_alias=DEFAULT_MODEL_ALIAS,
        model_name=DEFAULT_MODEL_NAME,
        base_url=DEFAULT_BASE_URL,
        max_context_size=128000,
    )


def _cleanup_args(*, cleanup_morph: bool) -> SimpleNamespace:
    return SimpleNamespace(
        cleanup_morph=cleanup_morph,
        provider_name=DEFAULT_PROVIDER_NAME,
        model_alias=DEFAULT_MODEL_ALIAS,
    )


def test_plain_deactivate_only_removes_plugin_switch() -> None:
    existing = _configure_morph_compaction(
        "[loop_control]\nreserved_context_size = 50000\n",
        _bootstrap_args(),
    )

    updated, removed = _deactivate_config(existing, _cleanup_args(cleanup_morph=False))

    assert 'compaction_plugin = "morph-plugin"' not in updated
    assert 'compaction_model = "morph-compaction"' in updated
    assert '[models.morph-compaction]' in updated
    assert '[providers.morph]' in updated
    assert 'reserved_context_size = 50000' in updated
    assert removed == ['compaction_plugin = "morph-plugin"']


def test_cleanup_morph_removes_bootstrap_sections_and_preserves_unrelated_config() -> None:
    existing = _configure_morph_compaction(
        (
            "[providers.other]\nbase_url = \"https://example.com\"\n\n"
            "[models.other]\nprovider = \"other\"\n\n"
            "[loop_control]\nreserved_context_size = 50000\n"
        ),
        _bootstrap_args(),
    )

    updated, removed = _deactivate_config(existing, _cleanup_args(cleanup_morph=True))

    assert 'compaction_plugin = "morph-plugin"' not in updated
    assert 'compaction_model = "morph-compaction"' not in updated
    assert '[models.morph-compaction]' not in updated
    assert '[providers.morph]' not in updated
    assert '[providers.other]' in updated
    assert '[models.other]' in updated
    assert 'reserved_context_size = 50000' in updated
    assert removed == [
        'compaction_plugin = "morph-plugin"',
        'compaction_model = "morph-compaction"',
        '[models.morph-compaction]',
        '[providers.morph]',
    ]


def test_cleanup_morph_respects_custom_aliases() -> None:
    bootstrap_args = SimpleNamespace(
        api_key="test-key",
        api_key_env=None,
        provider_name="custom-morph",
        model_alias="custom-compaction",
        model_name=DEFAULT_MODEL_NAME,
        base_url=DEFAULT_BASE_URL,
        max_context_size=128000,
    )
    cleanup_args = SimpleNamespace(
        cleanup_morph=True,
        provider_name="custom-morph",
        model_alias="custom-compaction",
    )

    existing = _configure_morph_compaction("", bootstrap_args)
    updated, removed = _deactivate_config(existing, cleanup_args)

    assert '[providers.custom-morph]' not in updated
    assert '[models.custom-compaction]' not in updated
    assert 'compaction_model = "custom-compaction"' not in updated
    assert removed[-2:] == ['[models.custom-compaction]', '[providers.custom-morph]']


def test_cleanup_morph_keeps_provider_when_other_models_still_reference_it() -> None:
    existing = _configure_morph_compaction(
        (
            '[models.morph-chat]\n'
            'provider = "morph"\n'
            'model = "kimi-k2.5"\n'
            'max_context_size = 262144\n\n'
            '[loop_control]\n'
            'reserved_context_size = 50000\n'
        ),
        _bootstrap_args(),
    )

    updated, removed = _deactivate_config(existing, _cleanup_args(cleanup_morph=True))

    assert 'compaction_plugin = "morph-plugin"' not in updated
    assert 'compaction_model = "morph-compaction"' not in updated
    assert '[models.morph-compaction]' not in updated
    assert '[providers.morph]' in updated
    assert '[models.morph-chat]' in updated
    assert 'provider = "morph"' in updated
    assert '[providers.morph]' not in removed
