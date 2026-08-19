# Storage Providers

Stash uses a provider abstraction to support multiple storage backends. Each provider implements the `StorageProvider` interface.

## Supported Providers

| Provider | Status | Max File | Max Chunk | Rate Limit |
|----------|--------|----------|-----------|------------|
| [Telegram](telegram.md) | ✅ Stable | 20 MB | 10 MB | 30 req/s |
| [Discord](discord.md) | ✅ Stable | 25 MB | 10 MB | 5 req/s |
| S3/MinIO | 🚧 Planned | Unlimited | Configurable | AWS limits |
| Google Drive | 🚧 Planned | Unlimited | Configurable | API limits |
| S3/MinIO | 🚧 Planned | Unlimited | Configurable | AWS limits |
| Backblaze B2 | 🚧 Planned | Unlimited | Configurable | B2 limits |
| WebDAV | 🚧 Planned | Unlimited | Configurable | Server limits |
| Local FS | 🚧 Planned | Unlimited | Configurable | Disk I/O |

## Adding a Provider

```bash
stash provider add <name> --type <type> [options]
```

### List Providers
```bash
stash provider list
```

### Remove Provider
```bash
stash provider remove <name> [--force]
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
    "telegram": {
      "type": "telegram",
      "credentials": {
        "token": "bot_token",
        "chat_id": "-1001234567890"
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
3. Register in `src/stash/providers/__init__.py`
4. Update CLI provider command
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