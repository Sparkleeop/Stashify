# Troubleshooting

## Installation

### `pip install` fails on Windows
Ensure you have the latest `pip` and Python 3.12+:

```bash
python -m pip install --upgrade pip
python -m pip install stashify
```

If cryptography fails to build, install the precompiled wheel:

```bash
python -m pip install cryptography --only-binary :all:
```

### `stash` command not found
Ensure the Python Scripts directory is on your PATH:

```bash
python -m pip show stashify   # shows install location
where stash                     # Windows
```

Add the Scripts directory to your PATH if needed.

## Provider Configuration

### "No providers configured"
You haven't added any providers. Add at least one:

```bash
stash provider add <name> --type <type> ...
```

### "Provider not found"
The provider type is misspelled. Check the name with:

```bash
stash provider list
```

Supported types: `telegram`, `discord`.

## Telegram

### "Invalid Telegram bot token"
1. Token format: `1234567890:AA...` (numbers colon letters)
2. Check with @BotFather → `/mybots` → your bot → API Token
3. Token must not contain spaces or quotes

### "Chat not found or bot is not a member"
1. Add bot to the chat/channel as admin
2. For channels, Chat ID is negative: `-1001234567890`
3. Message the bot at least once before using it
4. Verify Chat ID with @userinfobot

### "Request entity too large"
File exceeds the Telegram Bot API limit (20 MB). Stash handles this automatically by chunking, but if you set a custom chunk size above the limit:

```bash
stash put <file> --chunk-size 10485760   # 10 MB chunks
```

## Discord

### "Invalid Discord token"
1. Token format: `MTE2...` (base64-like)
2. Check Discord Developer Portal → Bot → Token
3. Token must not include the "Bot " prefix when using `--token`

### "No permission to access channel"
1. Bot must have `Send Messages` and `Attach Files` permissions
2. If using a channel in a server, invite the bot to that server
3. Bot can only access channels it has been granted access to

### "Request entity too large"
Discord limit is 25 MB. Stash chunks files by default, but reduce the chunk size if you get this:

```bash
stash put <file> --chunk-size 10485760   # 10 MB chunks
```

### "Rate limited"
Discord rate limits are strict. Reduce concurrency:

```bash
stash provider add discord --max-concurrent 2
```

## Key Management (RMK)

### "RMK not found in keyring" / "Repository locked or key unavailable"
The Repository Master Key (RMK) is not in the OS keyring. This happens when:
- You're on a new device and haven't run `stash unlock`
- You ran `stash key-commands lock` and haven't unlocked
- The keyring entry was deleted

**Fix:** Run `stash unlock --recovery-key <hex>` with your recovery key.

### "Recovery key required" / "Invalid recovery key format"
You must provide a valid 64-character hex recovery key (32 bytes = 64 hex chars):
```bash
stash key-commands unlock --recovery-key <64-char-hex>
```

### "Repository already unlocked"
The RMK is already in the keyring. No action needed.

### Lost recovery key
**There is no recovery.** The RMK is the only way to unlock the repository. If you lose the recovery key and the RMK is not in the keyring, you cannot decrypt existing files. You must re-initialize the repository and re-upload files.

## Provider Authentication

### "Authentication failed" on get
1. Provider credentials may have changed (token revoked/rotated)
2. Re-add the provider:
   ```bash
   stash provider remove <name> --force
   stash provider add <name> --type <type> ...
   ```

## Storage

### "Chunk not found" on get
Chunks may have been deleted from the provider. Check:
1. The chat/channel hasn't been cleared
2. Message IDs in the manifest still exist
3. No cleanup bot has deleted messages

### Manifest file corrupted
Stash stores manifests in `.stash/metadata/`. If corrupted:
1. Check the JSON is valid
2. Restore from backup if you have one
3. Re-upload the file if all backups are gone

## Networking

### "Connection timeout"
1. Check your internet connection
2. Stash uses HTTPS to Telegram/Discord APIs
3. Firewall/proxy may be blocking connections

### "SSL certificate verification failed"
1. Check your system clock is correct
2. Update CA certificates:
   ```bash
   python -m pip install --upgrade certifi
   ```

## Docker

### `stash` not found in container
Make sure you're using the image correctly:

```bash
docker run --rm -v ${PWD}:/data stashify:latest --help
```

The `stash` binary is on the container PATH.

### Docker build fails
The image requires `rich` (dependency). Run:

```bash
docker build --no-cache -t stashify .
```

## Performance

### Uploads are slow
1. Reduce `--max-concurrent` (provider rate limiting)
2. Increase chunk size for large files (fewer requests)
3. Check network bandwidth

### Downloads are slow
1. Reduce concurrency to avoid rate limits
2. Larger chunk sizes mean fewer requests

## Getting Help

- Check the [GitHub Issues](https://github.com/Sparkleeop/Stashify/issues)
- Include the output of `stash status`
- Include the full error message
- Describe the exact commands you ran