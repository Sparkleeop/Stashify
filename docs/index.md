# Stash

**Stash** is a privacy-focused CLI storage system that uses third-party platforms (Telegram, Discord) as encrypted storage backends.

## Quick Start

```bash
# Install
pip install stash

# Initialize repository
stash init

# Add storage provider
stash provider add telegram --token <bot_token> --chat-id <chat_id>

# Store a file
stash put file.txt

# Retrieve a file
stash get file.txt
```

## Documentation

- [Installation](installation.md)
- [Configuration](configuration.md)
- [Providers](providers/README.md)
- [CLI Reference](cli-reference.md)
- [Architecture](architecture.md)
- [Security](security.md)
- [Troubleshooting](troubleshooting.md)

## Features

- **Client-side encryption**: AES-256-GCM with per-file keys
- **Multi-provider support**: Telegram, Discord (S3, B2, Google Drive planned)
- **Chunked storage**: Automatic chunking for large files
- **Multi-provider distribution**: Single, split, balanced, replicated strategies
- **Resumable uploads**: Resume interrupted transfers
- **Integrity verification**: SHA-256 checksums per chunk
- **Privacy-first**: Encryption happens locally, providers only see ciphertext

## Providers

| Provider | Max File Size | Chunk Size | Status |
|----------|---------------|------------|--------|
| Telegram | 20 MB         | 10 MB      | ✅ Stable |
| Discord  | 25 MB         | 10 MB      | ✅ Stable |
| S3/MinIO | Unlimited     | Configurable | 🚧 Planned |
| Google Drive | Unlimited  | Configurable | 🚧 Planned |

## Security

- **AES-256-GCM** encryption per chunk
- **HKDF-SHA256** key derivation per chunk
- Per-file encryption keys with HKDF-SHA256 derivation
- Zero-knowledge: providers never see plaintext

## License

MIT License - see [LICENSE](../LICENSE) for details.