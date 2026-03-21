from __future__ import annotations

import os
from pathlib import Path

PLUGIN_NAME = "morph-plugin"
DEFAULT_CONFIG_PATH = Path.home() / ".kimi" / "config.toml"
TARGET_LINE = f'compaction_plugin = "{PLUGIN_NAME}"'


def _clear_compaction_plugin(text: str) -> tuple[str, bool]:
    lines = text.splitlines()
    result: list[str] = []
    in_loop_control = False
    removed = False

    for line in lines:
        stripped = line.strip()
        is_header = stripped.startswith("[") and stripped.endswith("]")

        if is_header:
            in_loop_control = stripped == "[loop_control]"
            result.append(line)
            continue

        if in_loop_control and stripped == TARGET_LINE:
            removed = True
            continue

        result.append(line)

    return "\n".join(result).rstrip() + "\n", removed


def main() -> None:
    config_path = Path(os.environ.get("KIMI_CONFIG_PATH", DEFAULT_CONFIG_PATH))
    if not config_path.exists():
        print(f"No config file at {config_path}; nothing to deactivate.")
        return

    existing = config_path.read_text(encoding="utf-8")
    updated, removed = _clear_compaction_plugin(existing)
    if not removed:
        print(f"No {TARGET_LINE!r} entry found in {config_path}.")
        return

    config_path.write_text(updated, encoding="utf-8")
    print(f"Removed {TARGET_LINE!r} from {config_path}")


if __name__ == "__main__":
    main()
