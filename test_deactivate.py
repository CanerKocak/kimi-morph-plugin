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


def test_deactivate_removes_all_morph_config() -> None:
    existing = _configure_morph_compaction(
        (
            "[providers.other]\nbase_url = \"https://example.com\"\n\n"
            "[models.other]\nprovider = \"other\"\n\n"
            "[loop_control]\nreserved_context_size = 50000\n"
        ),
        _bootstrap_args(),
    )

    updated, removed = _deactivate_config(existing)

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


def test_deactivate_also_removes_provider_when_other_models_reference_it() -> None:
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

    updated, removed = _deactivate_config(existing)

    assert '[providers.morph]' not in updated
    assert '[models.morph-compaction]' not in updated
    assert '[models.morph-chat]' in updated
    assert '[providers.morph]' in removed


def test_deactivate_noop_on_clean_config() -> None:
    updated, removed = _deactivate_config("[loop_control]\nreserved_context_size = 50000\n")

    assert removed == []
    assert 'reserved_context_size = 50000' in updated
