from __future__ import annotations

import argparse
import os
import re
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


def _provider_is_still_referenced(text: str, provider_name: str) -> bool:
    pattern = re.compile(r'^provider\s*=\s*"([^"]+)"\s*$')

    for line in text.splitlines():
        match = pattern.match(line.strip())
        if match and match.group(1) == provider_name:
            return True

    return False


def _deactivate_config(text: str, args: argparse.Namespace) -> tuple[str, list[str]]:
    removed: list[str] = []

    updated, removed_plugin = _remove_matching_line_in_table(
        text,
        "loop_control",
        lambda stripped: stripped == TARGET_PLUGIN_LINE,
    )
    if removed_plugin:
        removed.append(TARGET_PLUGIN_LINE)

    if not args.cleanup_morph:
        return updated, removed

    updated, removed_model_ref = _remove_matching_line_in_table(
        updated,
        "loop_control",
        lambda stripped: stripped == f'compaction_model = "{args.model_alias}"',
    )
    if removed_model_ref:
        removed.append(f'compaction_model = "{args.model_alias}"')

    updated, removed_model_table = _remove_table(updated, f"models.{args.model_alias}")
    if removed_model_table:
        removed.append(f"[models.{args.model_alias}]")

    if not _provider_is_still_referenced(updated, args.provider_name):
        updated, removed_provider_table = _remove_table(updated, f"providers.{args.provider_name}")
        if removed_provider_table:
            removed.append(f"[providers.{args.provider_name}]")

    return updated, removed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Disable the Morph compaction plugin and optionally remove bootstrap Morph config."
    )
    parser.add_argument(
        "--cleanup-morph",
        action="store_true",
        help="Also remove bootstrap-created Morph provider/model config and compaction_model routing.",
    )
    parser.add_argument(
        "--provider-name",
        default=DEFAULT_PROVIDER_NAME,
        help=f"Provider alias to remove when using --cleanup-morph. Default: {DEFAULT_PROVIDER_NAME}",
    )
    parser.add_argument(
        "--model-alias",
        default=DEFAULT_MODEL_ALIAS,
        help=f"Model alias to remove when using --cleanup-morph. Default: {DEFAULT_MODEL_ALIAS}",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config_path = Path(os.environ.get("KIMI_CONFIG_PATH", DEFAULT_CONFIG_PATH))
    if not config_path.exists():
        print(f"No config file at {config_path}; nothing to deactivate.")
        return

    existing = config_path.read_text(encoding="utf-8")
    updated, removed = _deactivate_config(existing, args)
    if not removed:
        if args.cleanup_morph:
            print(f"No Morph plugin or bootstrap config entries found in {config_path}.")
        else:
            print(f"No {TARGET_PLUGIN_LINE!r} entry found in {config_path}.")
        return

    config_path.write_text(updated, encoding="utf-8")
    print(f"Removed {', '.join(removed)} from {config_path}")


if __name__ == "__main__":
    main()
