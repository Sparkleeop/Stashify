# Configuration

## Repository Configuration

Each Stashify repository stores its configuration in `.stash/config.json`:

```json
{
  "version": 1,
  "created_at": 1699999999.123,
  "providers": {
    "telegram": {
      "type": "telegram",
      "credentials": {
        "token": "bot_token_here",
        "chat_id": "-1001234567890"
      },
      "settings": {
        "max_concurrent": "3"
      }
    }
  }
}
```

The repository identity (including RMK reference) is stored in `.stash/identity.json`:

```json
{
  "repository_id": "abc123...",
  "created_at": 1699999999.123,
  "version": 1
}
```

The **Repository Master Key (RMK)** is stored in the OS credential store, not in config files.

## Global Options

| Option | Description | Default |
|--------|-------------|---------|
| `--repo, -r` | Repository path | Current directory |
| `--verbose, -v` | Verbose output | false |

## Provider Configuration

Each provider has specific credentials and settings:

### Discord

```bash
stash provider add discord \
  --token <bot_token> \
  --channel-id <channel_id> \
  --is-bot true \
  --max-concurrent 3
```

| Setting | Description | Required | Default |
|---------|-------------|----------|---------|
| `token` | Bot token from Discord Developer Portal | Yes | - |
| `channel_id` | Channel ID to store files | Yes | - |
| `is_bot` | Use bot token (vs user token) | No | `true` |
| `max_concurrent` | Max concurrent uploads | No | `3` |

### Telegram

```bash
stash provider add telegram \
  --token <bot_token> \
  --chat-id <chat_id> \
  --max-concurrent 3
```

| Setting | Description | Required | Default |
|---------|-------------|----------|---------|
| `token` | Bot token from @BotFather | Yes | - |
| `chat_id` | Chat/channel ID for storage | Yes | - |
| `max_concurrent` | Max concurrent uploads | No | `3` |

## Global Settings

Create `.stash/config.toml` for global defaults:

```toml
[storage]
default_provider = "telegram"
default_chunk_size = 10485760  # 10MB
replication_factor = 1

[transfers]
upload_concurrency = 3
download_concurrency = 3
retry_count = 3
retry_backoff = 1.0

[security]
auto_lock_timeout = 0  # 0 = never
key_derivation_iterations = 100000

[ui]
compact_mode = false
animations = true
progress_style = "bar"
```

## Key Management

The **Repository Master Key (RMK)** is managed by the OS keyring:

| Command | Description |
|---------|-------------|
| `stash key-commands status` | Show key management status |
| `stash key-commands lock` | Remove RMK from keyring (lock repo) |
| `stash key-commands unlock --recovery-key <hex>` | Restore RMK from recovery key |
| `stash key-commands recovery` | Show RMK for backup |

The RMK is stored in the OS credential store:
- **Windows**: Credential Manager
- **macOS**: Keychain
- **Linux**: secret-service (GNOME Keyring, KWallet, etc.)

No passwords or raw keys are stored in configuration files.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `STASH_REPO` | Default repository path |
| `STASH_VERBOSE` | Enable verbose output |
| `DISCORD_TOKEN` | Default Discord bot token |
| `TELEGRAM_TOKEN` | Default Telegram bot token |

## Provider Limits

Each provider has built-in limits:

| Provider | Max File Size | Max Chunk Size | Rate Limit |
|----------|---------------|----------------|------------|
| Discord  | 25 MB         | 10 MB          | 5 req/s    |
| Telegram | 20 MB         | 10 MB          | 30 req/s   |

## Encryption Settings

| Setting | Default | Description |
|---------|---------|-------------|
| Algorithm | AES-256-GCM | Encryption algorithm |
| Key Size | 256 bits | Encryption key size |
| Chunk Key Derivation | HKDF-SHA256 | Per-chunk key derivation |
| File Key Derivation | HKDF-SHA256 | Per-file key derivation from RMK |
| RMK Derivation | HKDF-SHA256 | File key derivation from RMK + file_id |