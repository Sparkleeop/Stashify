# Stashify Documentation

**Stashify** is a privacy-focused CLI storage system that uses third-party platforms (Discord, Telegram) as encrypted storage backends.

## Quick Start

```bash
# Install
pip install stashify

# Initialize repository
stashify --repo /path/to/repo init

# Add storage provider
stashify --repo /path/to/repo provider add tg --type telegram --token <bot_token> --chat-id <chat_id>

# Store a file
stashify --repo /path/to/repo put file.txt --password secret

# Retrieve a file
stashify --repo /path/to/repo get file.txt --password secret
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
- **Multi-provider support**: Discord, Telegram (S3, B2, Google Drive planned)
- **Chunked storage**: Automatic chunking for large files
- **Multi-provider distribution**: Single, split, balanced, replicated strategies
- **Resumable uploads**: Resume interrupted transfers
- **Integrity verification**: SHA-256 checksums per chunk
- **Privacy-first**: Encryption happens locally, providers only see ciphertext

## Providers

| Provider | Max File Size | Chunk Size | Status |
|----------|---------------|------------|--------|
| Discord  | 25 MB         | 10 MB      | ✅ Stable |
| Telegram | 20 MB         | 10 MB      | ✅ Stable |
| S3/MinIO | Unlimited     | Configurable | 🚧 Planned |
| Google Drive | Unlimited  | Configurable | 🚧 Planned |

## Security

- **AES-256-GCM** encryption per chunk
- **HKDF-SHA256** key derivation per chunk
- Per-file encryption keys with HKDF-SHA256 derivation
- Argon2id password-based key derivation (planned)
- Zero-knowledge: providers never see plaintext

## License

MIT License - see [LICENSE](../LICENSE) for details.