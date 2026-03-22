from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

PLUGIN_NAME = "morph-plugin"
DEFAULT_CONFIG_PATH = Path.home() / ".kimi" / "config.toml"
DEFAULT_PROVIDER_NAME = "morph"
DEFAULT_MODEL_ALIAS = "morph-compaction"
DEFAULT_MODEL_NAME = "morph-v3-large"
DEFAULT_BASE_URL = "https://api.morphllm.com/v1"
DEFAULT_MAX_CONTEXT_SIZE = 128000


def _format_toml_value(value: str | int) -> str:
    if isinstance(value, int):
        return str(value)
    return json.dumps(value)


def _upsert_table(text: str, table_name: str, entries: dict[str, str | int]) -> str:
    lines = text.splitlines()
    result: list[str] = []
    header = f"[{table_name}]"
    found = False
    in_target = False
    written: set[str] = set()

    for line in lines:
        stripped = line.strip()
        is_header = stripped.startswith("[") and stripped.endswith("]")

        if is_header:
            if in_target:
                for key, value in entries.items():
                    if key not in written:
                        result.append(f"{key} = {_format_toml_value(value)}")
                in_target = False
            if stripped == header:
                found = True
                in_target = True
                written.clear()
            result.append(line)
            continue

        if in_target:
            replaced = False
            for key, value in entries.items():
                if stripped.startswith(f"{key} ") or stripped.startswith(f"{key}="):
                    if key not in written:
                        result.append(f"{key} = {_format_toml_value(value)}")
                        written.add(key)
                    replaced = True
                    break
            if replaced:
                continue

        result.append(line)

    if in_target:
        for key, value in entries.items():
            if key not in written:
                result.append(f"{key} = {_format_toml_value(value)}")

    if not found:
        if result and result[-1] != "":
            result.append("")
        result.append(header)
        for key, value in entries.items():
            result.append(f"{key} = {_format_toml_value(value)}")

    return "\n".join(result).rstrip() + "\n"


def _resolve_api_key(args: argparse.Namespace) -> str | None:
    if args.api_key:
        return args.api_key

    if args.api_key_env:
        value = os.environ.get(args.api_key_env)
        if value:
            return value

    value = os.environ.get("MORPH_API_KEY")
    if value:
        return value

    return None


def _configure_morph_compaction(text: str, args: argparse.Namespace) -> str:
    api_key = _resolve_api_key(args)
    if not api_key:
        raise SystemExit(
            "Morph setup requires an API key via --api-key, --api-key-env, or MORPH_API_KEY."
        )

    text = _upsert_table(
        text,
        f"providers.{args.provider_name}",
        {
            "type": "openai_legacy",
            "base_url": args.base_url,
            "api_key": api_key,
        },
    )
    text = _upsert_table(
        text,
        f"models.{args.model_alias}",
        {
            "provider": args.provider_name,
            "model": args.model_name,
            "max_context_size": args.max_context_size,
        },
    )
    return _upsert_table(
        text,
        "loop_control",
        {
            "compaction_model": args.model_alias,
            "compaction_plugin": PLUGIN_NAME,
        },
    )


def _set_compaction_plugin(text: str) -> str:
    return _upsert_table(text, "loop_control", {"compaction_plugin": PLUGIN_NAME})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enable the Morph compaction plugin and optionally bootstrap Morph provider config."
    )
    parser.add_argument(
        "--setup-morph",
        action="store_true",
        help="Also configure a Morph-backed provider/model for compaction.",
    )
    parser.add_argument("--api-key", help="Morph API key to write into Kimi config.")
    parser.add_argument(
        "--api-key-env",
        help="Environment variable name to read the Morph API key from.",
    )
    parser.add_argument(
        "--provider-name",
        default=DEFAULT_PROVIDER_NAME,
        help=f"Provider alias to create or update. Default: {DEFAULT_PROVIDER_NAME}",
    )
    parser.add_argument(
        "--model-alias",
        default=DEFAULT_MODEL_ALIAS,
        help=f"Model alias to create or update. Default: {DEFAULT_MODEL_ALIAS}",
    )
    parser.add_argument(
        "--model-name",
        default=DEFAULT_MODEL_NAME,
        help=f"Morph model name to configure for compaction. Default: {DEFAULT_MODEL_NAME}",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Morph API base URL. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--max-context-size",
        type=int,
        default=DEFAULT_MAX_CONTEXT_SIZE,
        help=f"Configured max context size for the compaction model. Default: {DEFAULT_MAX_CONTEXT_SIZE}",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config_path = Path(os.environ.get("KIMI_CONFIG_PATH", DEFAULT_CONFIG_PATH))
    config_path.parent.mkdir(parents=True, exist_ok=True)
    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""

    if args.setup_morph:
        updated = _configure_morph_compaction(existing, args)
        config_path.write_text(updated, encoding="utf-8")
        print(
            f"Configured Morph provider '{args.provider_name}', model '{args.model_alias}', "
            f"and compaction_plugin = \"{PLUGIN_NAME}\" in {config_path}"
        )
        return

    updated = _set_compaction_plugin(existing)
    config_path.write_text(updated, encoding="utf-8")
    print(f"Enabled compaction_plugin = \"{PLUGIN_NAME}\" in {config_path}")


if __name__ == "__main__":
    main()
