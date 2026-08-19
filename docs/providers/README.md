# Storage Providers

Stashify uses a provider abstraction to support multiple storage backends. Each provider implements the `StorageProvider` interface.

## Supported Providers

| Provider | Status | Max File | Max Chunk | Rate Limit |
|----------|--------|----------|-----------|------------|
| [Discord](discord.md) | ✅ Stable | 25 MB | 10 MB | 5 req/s |
| [Telegram](telegram.md) | ✅ Stable | 20 MB | 10 MB | 30 req/s |
| [S3/MinIO](s3.md) | 🚧 Planned | Unlimited | Configurable | AWS limits |
| [Google Drive](gdrive.md) | 🚧 Planned | Unlimited | Configurable | API limits |
| [S3/MinIO](s3.md) | 🚧 Planned | Unlimited | Configurable | AWS limits |
| [Backblaze B2](b2.md) | 🚧 Planned | Unlimited | Configurable | B2 limits |
| [WebDAV](webdav.md) | 🚧 Planned | Unlimited | Configurable | Server limits |
| [Local FS](local.md) | 🚧 Planned | Unlimited | Configurable | Disk I/O |

## Adding a Provider

```bash
stashify provider add <name> --type <type> [options]
```

### List Providers
```bash
stashify provider list
```

### Remove Provider
```bash
stashify provider remove <name> [--force]
```

## Provider Interface

All providers implement the `StorageProvider` interface:

```python
class StorageProvider(Protocol):
    async def initialize(self, config: ProviderConfig) -> None: ...
    async def upload_chunk(self, chunk: Chunk, remote_path: str) -> RemoteRef: ...
    async def download_chunk(self, remote_ref: RemoteRef) -> bytes: ...
    async def delete_chunk(self, remote_ref: RemoteRef) -> None: ...
    async def list_chunks(self, prefix: str) -> list[RemoteRef]: ...
    def get_limits(self) -> ProviderLimits: ...
    async def close(self) -> None: ...
```

## Provider Configuration

Each provider has specific credentials and settings stored in `.stash/config.json`:

```json
{
  "providers": {
    "discord": {
      "type": "discord",
      "credentials": {
        "token": "bot_token",
        "channel_id": "123456789",
        "is_bot": "true"
      },
      "settings": {
        "max_concurrent": "3"
      }
    }
  }
}
```

## Adding a New Provider

1. Create a new directory under `src/stash/providers/<name>/`
2. Implement `StorageProvider` interface
3. Add auth, limits, and provider modules
4. Register in `src/stash/providers/__init__.py`
5. Update CLI provider command
5. Add tests

## Provider Limits

Each provider defines limits in `ProviderLimits`:

```python
@dataclass(frozen=True)
class ProviderLimits:
    max_file_size: int        # Maximum total file size
    max_chunk_size: int       # Maximum chunk size
    max_concurrent_uploads: int  # Concurrent uploads
    rate_limit_requests: int     # Requests per window
    rate_limit_window: int       # Rate limit window (seconds)
    supports_resumable: bool = False
    supports_multipart: bool = False
```

## Rate Limiting

Each provider implements rate limiting:

- **Discord**: 5 requests/second global, 10/minute for uploads
- **Telegram**: 30 requests/second per bot

Rate limiting is handled automatically with exponential backoff.