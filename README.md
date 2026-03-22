# Kimi Morph Plugin

Replaces Kimi's default context compaction with [Morph Compact](https://morphllm.com) -- verbatim context compaction at 33,000 tok/s.

## Why Morph?

Kimi's default compaction summarizes your context, which means file paths, error codes, and decisions can get paraphrased away. Morph Compact **deletes filler and keeps every surviving line byte-for-byte identical to the original** -- no rewriting, no paraphrasing.

- **Fast**: 100K tokens compressed in under 3 seconds
- **50-70% token reduction** on typical agent sessions
- **Query-aware**: pass the next objective and Morph keeps what's relevant, drops the rest

## Demo

https://github.com/user-attachments/assets/cd9ab927-74ff-46a9-bfab-69e3cde75d03

## Install

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
max_context_size = 128000

[loop_control]
compaction_model = "morph-compaction"
```

## Uninstall

```bash
bash ~/.kimi/plugins/morph-plugin/deactivate.sh --cleanup-morph && kimi plugin remove morph-plugin
```

Omit `--cleanup-morph` to keep your Morph provider/model entries while disabling the plugin.

Both scripts support `KIMI_CONFIG_PATH` for custom config locations.

## Verify

```bash
kimi plugin list
```

You should see `morph-plugin` listed, and your `~/.kimi/config.toml` should contain the `[providers.morph]`, `[models.morph-compaction]`, and `compaction_model` entries shown above.

## How it works

Kimi's compaction system is pluggable. This plugin registers itself as the compaction handler and routes compaction requests through Morph's API instead of the default provider. The plugin reads credentials from Kimi's configured provider -- no standalone env vars needed at runtime.
