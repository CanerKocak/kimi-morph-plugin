# Kimi Morph Plugin

Replaces Kimi's default context compaction with Morph's `POST /v1/compact` endpoint using the `morph-compactor` model.

## Demo

https://github.com/user-attachments/assets/cd9ab927-74ff-46a9-bfab-69e3cde75d03

## Install

1. Configure a Morph-backed provider in `~/.kimi/config.toml`.

Example:

```toml
[providers.morph]
type = "openai_legacy"
base_url = "https://api.morphllm.com/v1"
api_key = "YOUR_MORPH_API_KEY"

[models.morph-compaction]
provider = "morph"
model = "morph-v3-large"
max_context_size = 128000

[loop_control]
compaction_model = "morph-compaction"
```

If your normal default Kimi model already uses Morph, you can skip `compaction_model`.

2. Install the plugin.

```bash
kimi plugin install git@github.com:CanerKocak/kimi-morph-plugin.git
```

From a local checkout:

```bash
kimi plugin install /path/to/kimi-morph-plugin
```

3. Activate the plugin.

```bash
bash ~/.kimi/plugins/morph-plugin/activate.sh
```

## Uninstall

```bash
bash ~/.kimi/plugins/morph-plugin/deactivate.sh && kimi plugin remove morph-plugin
```

Both `activate.sh` and `deactivate.sh` support `KIMI_CONFIG_PATH` for custom config locations.

## Configuration

Configure Morph as a normal Kimi provider in `~/.kimi/config.toml`. The plugin reuses the provider's API key, base URL, and custom headers directly from Kimi.

The plugin now requires those credentials to be configured in Kimi; it does not fall back to standalone `MORPH_API_KEY` or `MORPH_API_URL` environment variables.

The plugin does not choose the provider itself. Kimi passes the plugin either:

- the dedicated compaction model/provider selected by `loop_control.compaction_model`, or
- the normal active Kimi model/provider when no dedicated compaction model is set.

So if you want compaction to hit Morph reliably, make sure compaction is routed to a Morph-backed provider/model in Kimi config before activating the plugin.

## How it works

- `activate.py` sets `compaction_plugin = "morph-plugin"` in Kimi config.
- `deactivate.py` removes that entry, leaving other settings untouched.
- `morph_compaction.py` reads the Morph API key, base URL, and custom headers from Kimi's configured provider, then posts compaction requests to `/v1/compact`.
