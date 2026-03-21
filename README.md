# Kimi Morph Plugin

Morph-backed context compaction for Kimi Code.

## What It Does

This plugin replaces Kimi's default compaction step with Morph's native `POST /v1/compact` endpoint using the `morph-compactor` model.

The plugin keeps Kimi's existing preserve-tail behavior and only swaps the compaction implementation.

## Install

One-line install plus activation:

```bash
kimi plugin install git@github.com:CanerKocak/kimi-morph-plugin.git && bash ~/.kimi/plugins/morph-plugin/activate.sh
```

From a local checkout:

```bash
kimi plugin install /Users/caner/kimi-morph-plugin && bash ~/.kimi/plugins/morph-plugin/activate.sh
```

## Uninstall

Clean deactivation plus removal:

```bash
bash ~/.kimi/plugins/morph-plugin/deactivate.sh && kimi plugin remove morph-plugin
```

If you installed from a local checkout and want to test against a temporary config file, both helpers support `KIMI_CONFIG_PATH`.

## Configure Morph

Set these environment variables before running Kimi:

```bash
export MORPH_API_KEY="your-key"
export MORPH_API_URL="https://api.morphllm.com/v1"
```

`MORPH_API_URL` is optional. If omitted, the plugin uses `https://api.morphllm.com/v1`.

## Notes

- This plugin uses Morph's native `/v1/compact` endpoint.
- The plugin reads Morph credentials directly from environment variables.
- The plugin does not modify Kimi's main chat model. It only replaces context compaction.
- `activate.py` adds `compaction_plugin = "morph-plugin"` to Kimi config.
- `deactivate.py` removes that exact config entry and leaves other Kimi settings untouched.
