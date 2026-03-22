# Kimi Morph Plugin

Replaces Kimi's default context compaction with Morph's `POST /v1/compact` endpoint using the `morph-compactor` model.

## Demo

https://github.com/user-attachments/assets/cd9ab927-74ff-46a9-bfab-69e3cde75d03

## Install

This plugin only configures Morph-backed compaction. It assumes Kimi already has a normal chat model configured.

For most users, install the plugin and let activation add the Morph compaction provider/model for you:

```bash
export MORPH_API_KEY="YOUR_MORPH_API_KEY"
kimi plugin install git@github.com:CanerKocak/kimi-morph-plugin.git
bash ~/.kimi/plugins/morph-plugin/activate.sh --setup-morph
```

If you already manage a Morph-backed compaction model in `~/.kimi/config.toml`, plain activation still works:

```bash
kimi plugin install git@github.com:CanerKocak/kimi-morph-plugin.git
bash ~/.kimi/plugins/morph-plugin/activate.sh
```

You can also avoid putting the key directly on the command line:

```bash
export MORPH_API_KEY="YOUR_MORPH_API_KEY"
bash ~/.kimi/plugins/morph-plugin/activate.sh --setup-morph --api-key-env MORPH_API_KEY
```

The bootstrap path writes a Morph-backed provider/model into `~/.kimi/config.toml` using these defaults:

Example:

```toml
[providers.morph]
type = "openai_legacy"
base_url = "https://api.morphllm.com/v1"
api_key = "YOUR_MORPH_API_KEY"

[models.morph-compaction]
provider = "morph"
model = "morph-compactor"
max_context_size = 128000

[loop_control]
compaction_model = "morph-compaction"
```

If your normal default Kimi model already uses Morph, you can skip bootstrap and just run `activate.sh` with no extra flags.

From a local checkout, the same flow works:

```bash
export MORPH_API_KEY="YOUR_MORPH_API_KEY"
kimi plugin install /path/to/kimi-morph-plugin
bash ~/.kimi/plugins/morph-plugin/activate.sh --setup-morph
```

## Uninstall

```bash
bash ~/.kimi/plugins/morph-plugin/deactivate.sh --cleanup-morph && kimi plugin remove morph-plugin
```

Both `activate.sh` and `deactivate.sh` support `KIMI_CONFIG_PATH` for custom config locations.

If you only want to disable the plugin but keep your Morph provider/model entries, omit `--cleanup-morph`.

`--cleanup-morph` now removes the bootstrap-created Morph provider only when no other remaining model still references it.

## Configuration

`activate.sh` now supports two modes:

- plain activation: only sets `compaction_plugin = "morph-plugin"`
- bootstrap activation: with `--setup-morph`, also writes a Morph provider/model plus `loop_control.compaction_model`

Bootstrap activation accepts:

- `--api-key <key>`
- `--api-key-env <ENV_VAR_NAME>`
- `MORPH_API_KEY` from the environment

`deactivate.sh --cleanup-morph` removes:

- `compaction_plugin = "morph-plugin"`
- `compaction_model = "morph-compaction"` by default
- `[models.morph-compaction]` by default
- `[providers.morph]` only when no other remaining model still references it

You can override the bootstrap aliases with `--model-alias` and `--provider-name` during cleanup if you used custom names.

Configure Morph as a normal Kimi provider in `~/.kimi/config.toml` if you prefer to manage provider/model entries yourself. The plugin reuses the provider's API key, base URL, and custom headers directly from Kimi.

The plugin now requires those credentials to be configured in Kimi; it does not fall back to standalone `MORPH_API_KEY` or `MORPH_API_URL` environment variables.

The plugin does not choose the provider itself. Kimi passes the plugin either:

- the dedicated compaction model/provider selected by `loop_control.compaction_model`, or
- the normal active Kimi model/provider when no dedicated compaction model is set.

So if you want compaction to hit Morph reliably, make sure compaction is routed to a Morph-backed provider/model in Kimi config before activating the plugin.

## Verify

```bash
kimi plugin list
rg -n 'compaction_(plugin|model)|\[providers\.morph\]|\[models\.morph-compaction\]' ~/.kimi/config.toml
```

You should see:

- `morph-plugin` in `kimi plugin list`
- `compaction_plugin = "morph-plugin"`
- `compaction_model = "morph-compaction"`
- `[providers.morph]`
- `[models.morph-compaction]`

## How it works

- `activate.py` can either just set `compaction_plugin = "morph-plugin"` or bootstrap a Morph provider/model and set `compaction_model` at the same time.
- `deactivate.py` can either just remove `compaction_plugin` or, with `--cleanup-morph`, also remove the bootstrap-created provider/model entries and `compaction_model` routing.
- `morph_compaction.py` reads the Morph API key, base URL, and custom headers from Kimi's configured provider, then posts compaction requests to `/v1/compact`.
