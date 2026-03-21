# Kimi Morph Plugin

Replaces Kimi's default context compaction with Morph's `POST /v1/compact` endpoint using the `morph-compactor` model.

## Install

```bash
kimi plugin install git@github.com:CanerKocak/kimi-morph-plugin.git && bash ~/.kimi/plugins/morph-plugin/activate.sh
```

From a local checkout:

```bash
kimi plugin install /path/to/kimi-morph-plugin && bash ~/.kimi/plugins/morph-plugin/activate.sh
```

## Uninstall

```bash
bash ~/.kimi/plugins/morph-plugin/deactivate.sh && kimi plugin remove morph-plugin
```

Both `activate.sh` and `deactivate.sh` support `KIMI_CONFIG_PATH` for custom config locations.

## Configuration

Preferred: configure Morph as a normal Kimi provider in `~/.kimi/config.toml`. The plugin will reuse the provider's API key, base URL, and custom headers automatically.

Fallback: set environment variables instead:

```bash
export MORPH_API_KEY="your-key"
export MORPH_API_URL="https://api.morphllm.com/v1"  # optional, this is the default
```

## How it works

- `activate.py` sets `compaction_plugin = "morph-plugin"` in Kimi config.
- `deactivate.py` removes that entry, leaving other settings untouched.
- The plugin prefers Kimi's configured Morph provider and falls back to environment variables.
