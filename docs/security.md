# Security

## Overview

Stash is designed with a **zero-knowledge** security model. The storage providers (Telegram, Discord, etc.) only ever receive encrypted, opaque data blobs. They cannot decrypt, inspect, or modify your data.

## Encryption

### Algorithm
- **AES-256-GCM** for all data encryption
- Authenticated encryption with associated data (AEAD)
- 12-byte nonce per chunk (randomly generated)
- 16-byte authentication tag per chunk

### Key Hierarchy

```
User Password
    ↓ PBKDF2 (100,000 iterations) / Argon2id (planned)
Master Key (32 bytes)
    ↓ HKDF-SHA256 (salt: file_key_salt)
File Key (32 bytes per file)
    ↓ HKDF-SHA256 (info: "stash-chunk-{index}")
Chunk Key (32 bytes per chunk)
```

### Chunk Encryption

Each chunk is independently encrypted:
1. Derive chunk key from file key: `HKDF-SHA256(file_key, "stash-chunk-{index}")`
2. Generate random 12-byte nonce
3. Encrypt with AES-256-GCM: `ciphertext = AES-GCM(chunk_key, nonce, plaintext, aad=None)`
4. Store: `nonce (12 bytes) + ciphertext + tag (16 bytes)`

### Key Wrapping

File keys are wrapped with the user's password:
1. Derive wrapping key: `HKDF-SHA256(password, salt=16_bytes, info="stash-key-wrap")`
2. Encrypt file key: `AES-GCM(wrapping_key, nonce, file_key)`
3. Store: `salt (16) + nonce (12) + ciphertext + tag (16)`

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

### Password Handling
- Never stored, only used for key derivation
- Zeroized from memory after use
- Minimum 8 characters recommended

### Key Rotation (Planned)
- Periodic master key rotation
- Re-encryption of file keys
- Automatic re-encryption on access

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
- Token storage: encrypted in local config

## Threat Model

### Trusted
- Local machine (user's device)
- User password/credentials
- Stash binary (if verified)

### Untrusted
- Storage providers (Telegram, Discord, etc.)
- Network infrastructure
- Compromised provider infrastructure

### Out of Scope
- Local malware/keyloggers
- Physical device access
- Side-channel attacks
- Password brute force (mitigated by strong passwords)

## Provider Compromise Scenarios

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Provider reads files | Sees encrypted blobs only | Encryption |
| Provider modifies files | Checksum fails on download | Integrity checks |
| Provider deletes files | Local manifest has references | Replication strategy |
| Provider analyzes metadata | Only sees chunk sizes/timing | Fixed chunk sizes, padding (planned) |

## Key Rotation (Planned)

1. Generate new master key
2. Re-wrap all file keys
3. Re-encrypt filenames
4. Atomic manifest update
5. Old keys zeroized

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