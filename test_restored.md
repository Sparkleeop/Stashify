# Stash

**An open-source, privacy-focused command-line storage system that uses third-party platforms as encrypted storage backends.**

---

## What is Stash?

Stash is a storage abstraction layer. It lets you store files on external services — Telegram, Discord, and eventually S3, Backblaze B2, Google Drive, local filesystem, WebDAV, and others — while keeping all encryption strictly client-side.

Stash is **not** a cloud storage provider. It is a CLI tool that turns interchangeable storage backends into a unified, encrypted filesystem-like experience.

```
                    Stash CLI
                        |
              Storage abstraction
                        |
        +---------------+---------------+
        |                               |
    Telegram                          Discord
     backend                           backend
        |                               |
   encrypted chunks                 encrypted chunks
```

---

## Why Stash?

| Problem | Stash Approach |
|---------|----------------|
| Vendor lock-in | Provider-agnostic abstraction |
| No client-side encryption in most platforms | Encrypt locally, upload ciphertext only |
| Single point of failure | Distribute chunks across multiple providers |
| Manual chunk/message management | Automatic chunking, upload, metadata, resumption |
| Platform-specific limits | Chunking adapts to each provider's constraints |

---

## Core Architecture

### Client-Side Encryption

Files are encrypted **before** they leave your device.

```
plaintext → Stash (encrypt + chunk) → ciphertext chunks → providers
```

- Providers only ever receive authenticated ciphertext
- Established cryptographic libraries (no custom primitives)
- Per-file encryption keys with proper key derivation
- Authenticated encryption (AEAD) for every chunk
- Optional double-encryption mode (whole-file + per-chunk)

**Security claims are conservative:** encryption and key management provide confidentiality. Multi-provider distribution provides redundancy and availability — not additional cryptographic security.

### File Chunking

Large files are split into chunks to accommodate provider-specific size limits.

```
original file
     |
     v
encrypt → chunk → chunk 0, chunk 1, chunk 2, ...
```

Each chunk is independently encrypted and tracked. Metadata (manifest) describes how to reconstruct the file.

### Multi-Provider Storage

A single file's chunks can be distributed across providers.

| Strategy | Description |
|----------|-------------|
| **Single** | All chunks on one provider |
| **Split** | Chunks distributed across providers (0→Telegram, 1→Discord, …) |
| **Balanced** | Dynamic distribution based on availability/performance |
| **Replicated** | Each chunk stored on multiple providers for redundancy |

```
100 encrypted chunks

Telegram:  0, 2, 4, 6, 8, ...
Discord:   1, 3, 5, 7, 9, ...
```

Even if an attacker obtains **all chunks from every provider**, the data remains protected by the encryption design.

### Provider Abstraction

The core engine knows nothing about Telegram or Discord specifics.

```
Storage Provider (interface)
    |
    +-- Telegram
    +-- Discord
    +-- S3 / B2 / GDrive / Local / WebDAV (planned)
    +-- Future providers
```

New providers implement a clean interface. The storage engine remains unchanged.

### Asynchronous & Resumable

- Bounded concurrent workers for uploads/downloads
- Retries with exponential backoff
- Provider-aware rate limiting
- Progress reporting
- Cancellation support
- **Resumable operations**: if 75/100 chunks uploaded, interruption resumes at chunk 75

```
Upload Queue
     |
+----+----+----+
|    |    |    |
W1   W2   W3   W4  (bounded workers)
|    |    |    |
TG   DC   TG   S3  (providers)
```

### Manifest & Local Metadata

Each stored file has a manifest containing:

- File ID, original name, size
- Chunk size, count, encryption params
- Chunk indexes → provider assignments → remote identifiers
- Integrity verification data

Local metadata stored in SQLite (initially).

---

## Basic Usage

```bash
# Initialize repository
stash init

# Add providers
stash provider add telegram
stash provider add discord

# List configured providers
stash provider list

# Store a file
stash put ./movie.mkv

# List stored files
stash ls

# Show file metadata
stash info movie.mkv

# Retrieve a file
stash get movie.mkv

# Remove a file
stash rm movie.mkv

# Verify integrity (local metadata + remote)
stash verify movie.mkv

# Repair missing chunks from replicas (planned)
stash repair movie.mkv

# Overall status
stash status
```

The user never manages individual messages, attachments, chunks, or encryption metadata.

---

## Provider Support

| Provider | Status | Notes |
|----------|--------|-------|
| Telegram | Initial | Bot API, channel/group storage |
| Discord | Initial | Bot/user token, channel attachments |
| S3-compatible | Planned | AWS S3, MinIO, R2, etc. |
| Backblaze B2 | Planned | Native B2 API |
| Google Drive | Planned | OAuth, Drive API |
| Local filesystem | Planned | Directory backend |
| WebDAV | Planned | Generic WebDAV servers |

**Important:** Stash does not provide "unlimited storage." Actual limits, rate limits, file-size restrictions, and policies depend entirely on each provider. Stash adapts to those constraints via chunking and provider-specific logic.

---

## Security & Privacy Philosophy

- **Local-first encryption**: Plaintext never leaves your device
- **No custom crypto**: Established libraries (e.g., `cryptography`, `libsodium` bindings)
- **Minimal trust**: Providers are untrusted storage buckets
- **Transparency**: Open source, auditable code paths
- **Provider independence**: No single provider can compromise your data
- **Conservative claims**: We describe what the cryptography actually guarantees

---

## Project Status

**Early development.** Core architecture, provider abstraction, encryption model, and CLI structure are being designed and implemented.

| Area | Status |
|------|--------|
| CLI framework | In progress |
| Provider abstraction | In progress |
| Telegram backend | In progress |
| Discord backend | Planned |
| Encryption/chunking | In progress |
| Manifest/metadata | In progress |
| Async job engine | In progress |
| Resumable uploads | Planned |
| Multi-provider strategies | Planned |
| Verification/repair | Future |

Features described as "planned" or "future" are not yet implemented. This README will be updated as milestones land.

---

## Contributing

We welcome contributions — especially new storage providers, core improvements, testing, and documentation.

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

*Stash: your files, your keys, your choice of storage.*