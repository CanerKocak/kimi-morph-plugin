from __future__ import annotations

import os
from pathlib import Path

PLUGIN_NAME = "morph-plugin"
DEFAULT_CONFIG_PATH = Path.home() / ".kimi" / "config.toml"


def _set_compaction_plugin(text: str) -> str:
    lines = text.splitlines()
    result: list[str] = []
    in_loop_control = False
    loop_control_found = False
    key_written = False

    for line in lines:
        stripped = line.strip()
        is_header = stripped.startswith("[") and stripped.endswith("]")

        if is_header:
            if in_loop_control and not key_written:
                result.append(f'compaction_plugin = "{PLUGIN_NAME}"')
                key_written = True
            in_loop_control = stripped == "[loop_control]"
            loop_control_found = loop_control_found or in_loop_control
            result.append(line)
            continue

        if in_loop_control and stripped.startswith("compaction_plugin"):
            result.append(f'compaction_plugin = "{PLUGIN_NAME}"')
            key_written = True
            continue

        result.append(line)

    if loop_control_found:
        if in_loop_control and not key_written:
            result.append(f'compaction_plugin = "{PLUGIN_NAME}"')
    else:
        if result and result[-1] != "":
            result.append("")
        result.append("[loop_control]")
        result.append(f'compaction_plugin = "{PLUGIN_NAME}"')

    return "\n".join(result).rstrip() + "\n"


def main() -> None:
    config_path = Path(os.environ.get("KIMI_CONFIG_PATH", DEFAULT_CONFIG_PATH))
    config_path.parent.mkdir(parents=True, exist_ok=True)
    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    updated = _set_compaction_plugin(existing)
    config_path.write_text(updated, encoding="utf-8")
    print(f"Enabled compaction_plugin = \"{PLUGIN_NAME}\" in {config_path}")


if __name__ == "__main__":
    main()
