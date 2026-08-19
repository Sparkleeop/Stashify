# Telegram Provider

Stash's Telegram provider stores encrypted file chunks as documents in a Telegram chat/channel using a bot.

## Setup

### 1. Create Telegram Bot

1. Go to [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy the **Bot Token** (keep it secret!)

### 2. Get Chat ID

**For Private Chat:**
1. Message your bot
2. Forward message to [@userinfobot](https://t.me/userinfobot)
3. Copy your User ID (Chat ID)

**For Channel/Group:**
1. Add bot to channel/group as admin
2. Forward message from channel to [@userinfobot](https://t.me/userinfobot)
3. Copy the Chat ID (negative number for channels: `-1001234567890`)

### 3. Configure Stash

```bash
stash provider add telegram \
  --token <BOT_TOKEN> \
  --chat-id -1001234567890 \
  --max-concurrent 3
```

## How It Works

1. **File Upload**:
   - File encrypted and chunked (default 10MB chunks)
   - Each chunk uploaded as Telegram document
   - Caption: `stash-chunk:<file_id>:<chunk_index>`
   - Document filename: `<file_id>/chunk-<index>.bin`

2. **Metadata Storage**:
   - File manifest stored locally in `.stash/metadata/`
   - Chunk metadata: `message_id`, `file_id`, `chunk_index`, `size`
   - Encrypted filename stored in manifest

3. **Retrieval**:
   - Read manifest to get chunk list
   - Use `getFile` API to get file path
   - Download file from `https://api.telegram.org/file/bot<token>/<file_path>`
   - Decrypt and reconstruct

## Limits

| Limit | Value |
|-------|-------|
| Max file size | 20 MB (Bot API limit) |
| Max chunk size | 10 MB (safe margin) |
| Rate limit | 30 req/s global |

## Configuration

```bash
stash provider add telegram \
  --token <BOT_TOKEN> \
  --chat-id -1001234567890 \
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
| Global | 30 req/s |
| sendDocument | ~20/s |
| getFile | 20/s |
| getChatHistory | 30/s |

## File Size Limits

| Tier | Limit |
|------|-------|
| Bot API | 20 MB |
| Telegram Premium | 4 GB (not supported by bot API) |

## Chunking Strategy

For files > 20 MB:
1. File is split into 10MB chunks
2. Each chunk uploaded as separate document
3. Manifest tracks chunk order and metadata
4. On retrieval: download all → decrypt → reconstruct

## Configuration

```bash
stash provider add telegram \
  --name my_telegram \
  --token <BOT_TOKEN> \
  --chat-id -1001234567890 \
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
| Global | 30 req/s |
| sendDocument | ~20/s |
| getFile | 20/s |
| getChatHistory | 30/s |

## Troubleshooting

| Error | Solution |
|-------|----------|
| "Invalid Telegram bot token" | Check bot token from @BotFather |
| "Chat not found or bot not a member" | Add bot to chat/channel as admin |
| "Bot not a member of the chat" | Add bot to chat/channel |
| "File not found" | File may have been deleted from Telegram |
| "Request entity too large" | Reduce chunk size, file too big |
| "Rate limited" | Reduce `max_concurrent` |

## Security Notes

- Bot token is stored encrypted in local config
- Files encrypted before upload (AES-256-GCM)
- Bot only sees encrypted blobs
- Use private channel for storage
- Revoke token if compromised
- Telegram Premium doesn't increase bot API limits