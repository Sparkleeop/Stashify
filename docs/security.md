# Security

## Overview

Stashify is designed with a **zero-knowledge** security model. The storage providers (Telegram, Discord, etc.) only ever receive encrypted, opaque data blobs. They cannot decrypt, inspect, or modify your data.

## Encryption

### Algorithm
- **AES-256-GCM** for all data encryption
- Authenticated encryption with associated data (AEAD)
- 12-byte nonce per chunk (randomly generated)
- 16-byte authentication tag per chunk

### Key Hierarchy

```
Repository Master Key (RMK)
    │
    ├── File Encryption Key 1 (derived from RMK + file_id)
    ├── File Encryption Key 2
    └── File Encryption Key N
        │
        ├── Chunk Key 0 (derived from file_key + chunk_index)
        ├── Chunk Key 1
        └── Chunk Key N
```

### Chunk Encryption

Each chunk is independently encrypted:
1. Derive chunk key from file key: `HKDF-SHA256(file_key, "stash-chunk-{index}")`
2. Generate random 12-byte nonce
3. Encrypt with AES-256-GCM: `ciphertext = AES-GCM(chunk_key, nonce, plaintext, aad=None)`
4. Store: `nonce (12 bytes) + ciphertext + tag (16 bytes)`

### File Key Derivation

Per-file encryption keys are derived from the RMK:
1. Derive file key: `HKDF-SHA256(RMK, salt=file_id, info="stash-file-key")`
2. File key is 32 bytes (AES-256)

### Filename Encryption

Filenames are encrypted using the file key:
1. Derive filename key: `HKDF-SHA256(file_key, info="stash-filename")`
2. Encrypt with AES-256-GCM

## Integrity

### Chunk-Level
- AES-GCM authentication tag (16 bytes) per chunk
- SHA-256 checksum stored in manifest
- Verified on every download

### File-Level
- Manifest includes SHA-256 of original file
- Verified after reconstruction

### Manifest Integrity
- JSON serialization with deterministic ordering
- File IDs are SHA-256 hashes
- Manifest versioning for forward compatibility

## Key Management

### Repository Master Key (RMK)

The RMK is the root key for the repository:
- Generated once during `stash init` (32 random bytes)
- Stored in OS credential store (Windows Credential Manager, macOS Keychain, Linux secret-service)
- Never written to disk
- Accessed via `keyring` library

### Recovery Key

The RMK itself serves as the **recovery key**:
- Displayed once during `stash init`
- Must be saved securely by the user
- Used to unlock repository on new devices via `stash key-commands unlock --recovery-key <hex>`

### Key Storage

| Component | Storage | Encryption |
|-----------|---------|------------|
| RMK | OS keyring (CredMan/Keychain/secret-service) | Encrypted by OS |
| File keys | Derived on-the-fly from RMK + file_id | Not stored |
| Chunk keys | Derived on-the-fly from file_key + chunk_index | Not stored |
| Provider credentials | `.stash/config.json` | Plaintext (OS file permissions) |
| Recovery key | User-managed (offline) | User responsibility |

### Lock / Unlock

- `stash key-commands lock` — removes RMK from keyring
- `stash key-commands unlock --recovery-key <hex>` — restores RMK
- `stash key-commands status` — shows current lock state

## Provider Security

### Data at Rest (Provider Side)
- Providers only receive encrypted blobs
- No metadata about file contents
- Chunk filenames are opaque (`<file_id>/chunk-<index>.bin`)
- Message content only contains chunk index

### Provider Compromise
- Provider compromise = encrypted blobs only
- No plaintext, keys, or metadata leaked
- Re-encryption possible with new providers
- Forward secrecy: compromise doesn't affect past/future files

## Network Security

- All provider communication over HTTPS/TLS
- Certificate validation enforced
- No plaintext credentials in transit
- Token storage: local config (OS file permissions)

## Threat Model

### Trusted
- Local machine (user's device)
- User recovery key (if backed up)
- Stashify binary (if verified)

### Untrusted
- Storage providers (Telegram, Discord, etc.)
- Network infrastructure
- Compromised provider infrastructure

### Out of Scope
- Local malware/keyloggers
- Physical device access
- Side-channel attacks

## Provider Compromise Scenarios

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Provider reads files | Sees encrypted blobs only | Encryption |
| Provider modifies files | Checksum fails on download | Integrity checks |
| Provider deletes files | Local manifest has references | Replication strategy |
| Provider analyzes metadata | Only sees chunk sizes/timing | Fixed chunk sizes, padding (planned) |

## Key Rotation (Planned)

1. Generate new RMK
2. Re-wrap all file keys with new RMK
3. Re-encrypt filenames
5. Atomic manifest update
6. Old keys zeroized

## Compliance Considerations

- **GDPR**: Data minimization, right to deletion
- **HIPAA**: Encryption at rest/in transit
- **SOC 2**: Encryption, access controls, audit logging

## Reporting Security Issues

Report security vulnerabilities to: security@stashify.io

Include:
- Description of vulnerability
- Steps to reproduce
- Impact assessment
- Suggested fix (if any)