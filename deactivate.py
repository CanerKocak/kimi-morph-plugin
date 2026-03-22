from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

PLUGIN_NAME = "morph-plugin"
DEFAULT_CONFIG_PATH = Path.home() / ".kimi" / "config.toml"
DEFAULT_PROVIDER_NAME = "morph"
DEFAULT_MODEL_ALIAS = "morph-compaction"
TARGET_PLUGIN_LINE = f'compaction_plugin = "{PLUGIN_NAME}"'


def _remove_matching_line_in_table(
    text: str, table_name: str, predicate: Callable[[str], bool]
) -> tuple[str, bool]:
    lines = text.splitlines()
    result: list[str] = []
    in_target = False
    removed = False
    header = f"[{table_name}]"

    for line in lines:
        stripped = line.strip()
        is_header = stripped.startswith("[") and stripped.endswith("]")

        if is_header:
            in_target = stripped == header
            result.append(line)
            continue

        if in_target and predicate(stripped):
            removed = True
            continue

        result.append(line)

    return "\n".join(result).rstrip() + "\n", removed


def _remove_table(text: str, table_name: str) -> tuple[str, bool]:
    lines = text.splitlines()
    result: list[str] = []
    in_target = False
    removed = False
    header = f"[{table_name}]"

    for line in lines:
        stripped = line.strip()
        is_header = stripped.startswith("[") and stripped.endswith("]")

        if is_header:
            if stripped == header:
                in_target = True
                removed = True
                continue
            in_target = False

        if in_target:
            continue

        result.append(line)

    return "\n".join(result).rstrip() + "\n", removed


def _deactivate_config(text: str) -> tuple[str, list[str]]:
    removed: list[str] = []

    updated, removed_plugin = _remove_matching_line_in_table(
        text,
        "loop_control",
        lambda stripped: stripped == TARGET_PLUGIN_LINE,
    )
    if removed_plugin:
        removed.append(TARGET_PLUGIN_LINE)

    updated, removed_model_ref = _remove_matching_line_in_table(
        updated,
        "loop_control",
        lambda stripped: stripped == f'compaction_model = "{DEFAULT_MODEL_ALIAS}"',
    )
    if removed_model_ref:
        removed.append(f'compaction_model = "{DEFAULT_MODEL_ALIAS}"')

    updated, removed_model_table = _remove_table(updated, f"models.{DEFAULT_MODEL_ALIAS}")
    if removed_model_table:
        removed.append(f"[models.{DEFAULT_MODEL_ALIAS}]")

    updated, removed_provider_table = _remove_table(
        updated, f"providers.{DEFAULT_PROVIDER_NAME}"
    )
    if removed_provider_table:
        removed.append(f"[providers.{DEFAULT_PROVIDER_NAME}]")

    return updated, removed


def main() -> None:
    config_path = Path(os.environ.get("KIMI_CONFIG_PATH", DEFAULT_CONFIG_PATH))
    if not config_path.exists():
        print(f"No config file at {config_path}; nothing to deactivate.")
        return

    existing = config_path.read_text(encoding="utf-8")
    updated, removed = _deactivate_config(existing)
    if not removed:
        print(f"No Morph plugin config found in {config_path}.")
        return

    config_path.write_text(updated, encoding="utf-8")
    print(f"Removed {', '.join(removed)} from {config_path}")


if __name__ == "__main__":
    main()
