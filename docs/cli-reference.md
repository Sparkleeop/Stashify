# CLI Reference

## Global Options

| Option | Description |
|--------|-------------|
| `--repo, -r` | Repository path (default: current directory) |
| `--verbose, -v` | Verbose output |
| `--help, -h` | Show help |
| `--version` | Show version |

## Commands

### `stash init`
Initialize a new Stash repository (generates RMK, stores in OS keyring).

```bash
stash init [--repo PATH] [--force]
```

| Option | Description |
|--------|-------------|
| `--repo, -r` | Repository path (default: current directory) |
| `--force, -f` | Overwrite existing repository |

**Output:** Shows Repository ID and Recovery Key (RMK hex) — **save the recovery key!**

### `stash provider`
Manage storage providers.

#### `stash provider add`
Add a storage provider.

```bash
stash provider add <name> --type <type> [options]
```

**Telegram:**
```bash
stash provider add tg --type telegram --token <token> --chat-id <chat_id>
```

**Discord:**
```bash
stash provider add dc --type discord --token <token> --channel-id <id>
```

#### Options

| Option | Description |
|--------|-------------|
| `--type, -t` | Provider type: `telegram`, `discord` |
| `--token` | Bot token (prompt if not provided) |
| `--chat-id` | Telegram chat ID |
| `--channel-id` | Discord channel ID |
| `--is-bot/--is-user` | Discord: bot vs user token |
| `--max-concurrent` | Max concurrent uploads (default: 3) |

#### `stash provider list`
List configured providers.

```bash
stash provider list
```

#### `stash provider remove`
Remove a storage provider.

```bash
stash provider remove <name> [--force]
```

### `stash put`
Store a file in Stash (uses RMK from keyring — no password prompt).

```bash
stash put <file> [options]
```

| Option | Description |
|--------|-------------|
| `--provider, -p` | Specific provider to use |
| `--chunk-size` | Chunk size in bytes (default: provider limit) |
| `--strategy` | Distribution: single, split, balanced, replicated |
| `--confirm/--no-confirm` | Skip confirmation prompt |

### `stash get`
Retrieve a file from Stash (uses RMK from keyring — no password prompt).

```bash
stash get <file_id_or_name> [options]
```

| Option | Description |
|--------|-------------|
| `--output, -o` | Output path (default: current directory) |
| `--overwrite` | Overwrite existing file |

### `stash ls`
List stored files.

```bash
stash ls [options]
```

| Option | Description |
|--------|-------------|
| `--long, -l` | Show detailed information |

### `stash info`
Show file metadata.

```bash
stash info <file_id_or_name>
```

### `stash rm`
Remove a stored file.

```bash
stash rm <file_id_or_name> [options]
```

| Option | Description |
|--------|-------------|
| `--force, -f` | Force removal without confirmation |
| `--remote/--local-only` | Also delete from remote providers |

### `stash verify`
Verify file integrity.

```bash
stash verify <file_id_or_name> [--full]
```

| Option | Description |
|--------|-------------|
| `--full` | Download and verify all chunks |

### `stash status`
Show overall repository status.

```bash
stash status
```

### `stash key-commands`
Repository key management.

#### `stash key-commands lock`
Lock the repository by removing RMK from keyring.

```bash
stash key-commands lock
```

#### `stash key-commands unlock`
Unlock the repository on a new device using a recovery key.

```bash
stash key-commands unlock --recovery-key <hex>
```

| Option | Description |
|--------|-------------|
| `--recovery-key` | Recovery key (RMK hex) to restore RMK |

#### `stash key-commands status`
Show key management status.

```bash
stash key-commands status
```

#### `stash key-commands recovery`
Show the recovery key (RMK) for backup purposes.

```bash
stash key-commands recovery
```

## Global Options

| Option | Description |
|--------|-------------|
| `--repo, -r` | Repository path (default: current directory) |
| `--verbose, -v` | Verbose output |
| `--help, -h` | Show help |
| `--version` | Show version |

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | File not found |
| 4 | Authentication failed |
| 5 | Network error |
| 6 | Storage limit exceeded |

## Key Management Flow

```
First device:                    New device:
stash init                       stash unlock --recovery-key <hex>
  ↓                                 ↓
Generate RMK                     Restore RMK to keyring
  ↓                                 ↓
Store in OS keyring              Ready to use
  ↓
Show recovery key (SAVE!)
```

**Important:** The recovery key (RMK hex) is shown **once** during `stash init`. Save it securely — it's the only way to unlock the repository on a new device.