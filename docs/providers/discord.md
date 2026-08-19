# Discord Provider

Stashify's Discord provider stores encrypted file chunks as message attachments in a Discord channel using a bot.

## Setup

### 1. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" → Give it a name
3. Go to "Bot" tab → "Add Bot"
4. Copy the **Bot Token** (keep it secret!)
5. Enable **Message Content Intent** in Bot settings
6. Invite bot to your server with `Send Messages` and `Attach Files` permissions

### 2. Get Channel ID

1. Enable **Developer Mode** in Discord (User Settings → Advanced → Developer Mode)
2. Right-click the channel → "Copy Channel ID"
7. Channel ID format: `123456789012345678`

### 3. Configure Stashify

```bash
stashify provider add discord \
  --token <BOT_TOKEN> \
  --channel-id 123456789012345678 \
  --is-bot true \
  --max-concurrent 3
```

## How It Works

1. **File Upload**:
   - File is encrypted and chunked (default 10MB chunks)
   - Each chunk uploaded as Discord message attachment
   - Message content: `stash-chunk:<file_id>:<chunk_index>`
   - Attachment filename: `<file_id>/chunk-<index>.bin`

2. **Metadata Storage**:
   - File manifest stored locally in `.stash/metadata/`
   - Chunk metadata: `message_id`, `file_id`, `chunk_index`, `size`
   - Encrypted filename stored in manifest

3. **Retrieval**:
   - Read manifest to get chunk list
   - Fetch messages by ID from Discord
   - Download attachments, decrypt, reconstruct

## Limits

| Limit | Value |
|-------|-------|
| Max file size | 25 MB (Discord limit) |
| Max chunk size | 10 MB (safe margin) |
| Rate limit | 5 req/s global, 10/min uploads |
| Max message size | 8 MB attachment + content |

## Configuration

```bash
stashify provider add discord \
  --name my_discord \
  --token <BOT_TOKEN> \
  --channel-id 123456789012345678 \
  --is-bot true \
  --max-concurrent 3
```

### Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `max_concurrent` | Max concurrent uploads | 3 |
| `chunk_size` | Chunk size in bytes | 10MB |

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| Global | 50 req/s |
| Send Message | 5/s per channel |
| Upload | 10/min per channel |

## Troubleshooting

| Error | Solution |
|-------|----------|
| "Invalid Discord token" | Check bot token is correct |
| "No permission to access channel" | Bot lacks permissions in channel |
| "Channel not found" | Check channel ID is correct |
| "Request entity too large" | File too large, reduce chunk size |
| "Rate limited" | Reduce `max_concurrent` |

## Security Notes

- Bot token is stored encrypted in local config
- Files encrypted before upload (AES-256-GCM)
- Bot only sees encrypted blobs
- Use dedicated channel for storage
- Revoke token if compromised