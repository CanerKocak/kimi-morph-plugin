# Kimi Morph Plugin


Replaces Kimi's default context compaction with [Morph Compact](https://www.morphllm.com/products/compact) -- verbatim context compaction at 33,000 tok/s.

## Why Morph?

<img width="1110" height="407" alt="image" src="https://github.com/user-attachments/assets/07e8c0a9-2664-4d6a-b39c-6ad6b7c198e7" />

## Demo

https://github.com/user-attachments/assets/cd9ab927-74ff-46a9-bfab-69e3cde75d03

## Install

Get your API key from the [Morph dashboard](https://www.morphllm.com/dashboard/api-keys), then:

```bash
export MORPH_API_KEY="YOUR_MORPH_API_KEY"
kimi plugin install git@github.com:CanerKocak/kimi-morph-plugin.git
bash ~/.kimi/plugins/morph-plugin/activate.sh
```

You can also pass the key indirectly:

```bash
bash ~/.kimi/plugins/morph-plugin/activate.sh --api-key-env MORPH_API_KEY
```

This writes the following into `~/.kimi/config.toml`:

```toml
[providers.morph]
type = "openai_legacy"
base_url = "https://api.morphllm.com/v1"
api_key = "YOUR_MORPH_API_KEY"

[models.morph-compaction]
provider = "morph"
model = "morph-compactor"

[loop_control]
compaction_model = "morph-compaction"
```

The activation script derives `max_context_size` from your current `default_model` entry and writes that value for you.

## Uninstall

```bash
bash ~/.kimi/plugins/morph-plugin/deactivate.sh && kimi plugin remove morph-plugin
```

Both scripts support `KIMI_CONFIG_PATH` for custom config locations.

## Verify

```bash
kimi plugin list
```

You should see `morph-plugin` listed, and your `~/.kimi/config.toml` should contain the `[providers.morph]`, `[models.morph-compaction]`, and `compaction_model` entries shown above.

## How it works

Kimi's compaction system is pluggable. This plugin registers itself as the compaction handler and routes compaction requests through Morph's API instead of the default provider.
