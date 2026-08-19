# Architecture

## Overview

Stash is a privacy-focused CLI storage system that uses third-party platforms as encrypted storage backends. The architecture is designed around a provider-agnostic core with pluggable storage backends.

## Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Stash CLI                              │
├─────────────────────────────────────────────────────────────┤
│  Commands (put, get, ls, info, rm, verify, status, etc.)    │
├─────────────────────────────────────────────────────────────┤
│                    Storage Engine                             │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │   Crypto    │  │   Chunking   │  │     Manifest       │  │
│  │   Engine    │  │   Manager    │  │     Manager        │  │
│  └─────────────┘  └──────────────┘  └────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│              Provider Abstraction Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │   Telegram   │  │   Discord    │  │  S3 / B2 / GDrive  │ │
│  │   Provider   │  │   Provider   │  │     (Planned)      │ │
│  └──────────────┘  └──────────────┘  └────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Core Modules

### Crypto Engine (`src/stash/core/crypto.py`)
- **AES-256-GCM** encryption for chunks
- **HKDF-SHA256** key derivation
- Per-file encryption keys with HKDF-SHA256 derivation
- Per-chunk keys derived via HKDF from file key
- Password-based key wrapping with Argon2id (planned)

### Chunking Manager (`src/stash/core/chunking.py`)
- Configurable chunk sizes (default 10MB)
- Streaming chunking for memory efficiency
- Automatic chunk boundary alignment
- Checksum verification (SHA-256)

### Manifest Manager (`src/stash/core/manifest.py`)
- File metadata: ID, name, size, chunk list
- Chunk mapping: index → provider, remote_id, checksum
- Encryption parameters (algorithm, key size, nonce size)
- Distribution strategy tracking
- JSON serialization with binary data as hex

### Metadata Store (`src/stash/core/metadata.py`)
- JSON-based local metadata storage
- SQLite backend (planned)
- Provider configuration management
- File indexing and lookup

### Provider Abstraction (`src/stash/core/storage.py`)
- `StorageProvider` protocol defines interface
- `BaseStorageProvider` base class
- Provider registry for dynamic loading
- Automatic provider discovery

## Provider Architecture

Each provider implements `StorageProvider` interface:

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

### Provider Implementation Structure
```
src/stash/providers/
├── __init__.py           # Provider registry
├── base.py               # BaseStorageProvider abstract class
├── discord/
│   ├── __init__.py
│   ├── auth.py           # Discord OAuth/bot auth
│   ├── limits.py         # Discord-specific limits
│   └── provider.py       # DiscordProvider implementation
├── telegram/
│   ├── __init__.py
│   ├── auth.py           # Telegram bot auth
│   ├── limits.py         # Telegram-specific limits
│   └── provider.py       # TelegramProvider implementation
└── ...
```

## Data Flow

### Upload Flow
```
File → Encrypt → Chunk → Per-chunk encrypt → Upload to providers → Save manifest
```

1. **File Input** → Read file stream
2. **Encryption** → Generate file key, encrypt filename
4. **Chunking** → Split into configurable chunks (default 10MB)
5. **Per-Chunk Encryption** → HKDF-derived per-chunk key + AES-256-GCM
5. **Provider Upload** → Parallel upload to configured providers
7. **Manifest Creation** → Store metadata, chunk mappings, encryption params
8. **Persist** → Save manifest to local metadata store

### Download Flow
```
Manifest → Decrypt filename → Resolve chunks → Download from providers → Decrypt → Reconstruct
```

1. **Manifest Lookup** → Load file metadata
4. **Key Derivation** → Decrypt file key with password
4. **Filename Decryption** → Decrypt original filename
5. **Chunk Resolution** → Determine providers for each chunk
6. **Parallel Download** → Fetch chunks from providers
7. **Decrypt & Verify** → Decrypt chunks, verify checksums
8. **Reconstruction** → Stream decrypted chunks to output file

## Distribution Strategies

| Strategy | Description |
|----------|-------------|
| **Single** | All chunks on one provider |
| **Split** | Round-robin chunks across providers |
| **Balanced** | Distribute based on provider capacity |
| **Replicated** | Store each chunk on multiple providers |

## Concurrency Model

- **Async/await** throughout for I/O operations
- **Semaphore-based** concurrency control per provider
- **AsyncIO** for HTTP requests
- **ThreadPoolExecutor** for CPU-bound crypto operations
- Configurable concurrency per provider

## Security Model

### Threat Model
- **Trusted**: Local machine, user password
- **Untrusted**: Storage providers, network
- **Assumption**: Provider may be malicious/curious

### Security Guarantees
- **Confidentiality**: AES-256-GCM encryption
- **Integrity**: GCM authentication tags + SHA-256 checksums
- **Forward Secrecy**: Per-file keys, per-chunk keys
- **Provider Isolation**: Providers cannot decrypt without user password

### Key Hierarchy
```
User Password
    ↓ Argon2id (planned) / PBKDF2
Master Key
    ↓ HKDF-SHA256
File Key (per file)
    ↓ HKDF-SHA256
Chunk Key (per chunk)
```

## Error Handling

- **Retry Logic**: Exponential backoff with jitter
- **Circuit Breaker**: Per-provider failure tracking
- **Graceful Degradation**: Continue with available providers
- **Validation**: Input validation, checksum verification