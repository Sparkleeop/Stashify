# Stashify

<p align="center">
  <strong>Encrypted storage. Your providers. Your keys.</strong>
</p>

<p align="center">
  An open-source, privacy-focused storage system that turns third-party platforms into encrypted storage backends.
</p>

<p align="center">
  <a href="https://github.com/Sparkleeop/Stashify">
    <img src="https://img.shields.io/github/stars/Sparkleeop/Stashify?style=flat-square" alt="GitHub Stars">
  </a>
  <a href="https://github.com/Sparkleeop/Stashify">
    <img src="https://img.shields.io/github/license/Sparkleeop/Stashify?style=flat-square" alt="License">
  </a>
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Status-Early%20Development-ee8695?style=flat-square" alt="Status">
</p>

---

## What is Stashify?

**Stashify** is an open-source, provider-agnostic storage system designed around one simple idea:

> **Your storage provider shouldn't have to be your storage system.**

Stashify lets you use services such as **Telegram and Discord as storage backends**, while encryption and file management remain under your control.

Files are encrypted locally, split into chunks, and uploaded as ciphertext. Chunks can be stored on one provider or distributed across multiple providers depending on your configuration.

```text
                         STASHIFY
                            │
                     Storage Engine
                            │
              ┌─────────────┴─────────────┐
              │                           │
          Encryption                  Chunking
              │                           │
              └─────────────┬─────────────┘
                            │
                     Storage Router
                            │
              ┌─────────────┴─────────────┐
              │                           │
          Telegram                     Discord
              │                           │
       encrypted chunks            encrypted chunks
```

Stashify does **not** provide the underlying storage.

It provides the abstraction that lets you use storage you already have access to.

---

## Why Stashify?

Traditional cloud storage usually means trusting one provider with both your data and your storage.

Stashify separates those concepts.

| Problem                    | Stashify                              |
| -------------------------- | ------------------------------------- |
| Vendor lock-in             | Provider-agnostic storage abstraction |
| Provider sees plaintext    | Files are encrypted before upload     |
| Large files                | Automatic chunking                    |
| Provider-specific limits   | Provider-aware chunking and routing   |
| Single provider dependency | Multi-provider storage                |
| Interrupted uploads        | Resumable operations                  |
| Manual file management     | Unified CLI/TUI                       |
| Provider-specific APIs     | One consistent interface              |

---

## Features

### Client-side encryption

Your files are encrypted **before they leave your device**.

```text
                    YOUR DEVICE
                         │
                    Plaintext
                         │
                         ▼
                    Encryption
                         │
                         ▼
                      Chunking
                         │
                         ▼
               Encrypted ciphertext
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
          Telegram               Discord
```

Storage providers should only receive ciphertext.

Stashify is designed around:

* Client-side encryption
* Authenticated encryption (AEAD)
* Per-file cryptographic keys
* Proper key derivation
* Cryptographically secure randomness
* No custom cryptographic primitives
* Authenticated chunk integrity
* Local key management

Stashify uses established cryptographic libraries rather than implementing cryptography from scratch.

> **Security note:** Stashify does not claim that multi-provider storage makes encryption stronger. Confidentiality comes from the cryptographic design and key management. Multi-provider storage primarily provides distribution, redundancy, and provider independence.

---

### Chunked storage

Large files are automatically split into manageable chunks.

```text
movie.mkv
    │
    ▼
 encrypted data
    │
    ▼
┌────────┬────────┬────────┬────────┐
│ chunk0 │ chunk1 │ chunk2 │ chunk3 │
└────────┴────────┴────────┴────────┘
    │         │        │        │
    ▼         ▼        ▼        ▼
 encrypted encrypted encrypted encrypted
```

Each chunk is independently tracked and authenticated.

The storage engine can account for provider-specific upload limitations without exposing those implementation details to the rest of the application.

---

### Multi-provider storage

Stashify can distribute a file across multiple storage providers.

For example:

```text
100 encrypted chunks

Telegram:
  0  2  4  6  8  10  12  ...

Discord:
  1  3  5  7  9  11  13  ...
```

Multiple storage strategies are planned:

| Strategy       | Description                                           |
| -------------- | ----------------------------------------------------- |
| **Single**     | Store all chunks on one provider                      |
| **Split**      | Distribute chunks across multiple providers           |
| **Balanced**   | Dynamically distribute chunks based on provider state |
| **Replicated** | Store copies across multiple providers                |

This allows Stashify to build storage around the providers available to you instead of forcing you into a single backend.

---

### Provider abstraction

Providers are implementations of the same storage interface.

```text
                    Storage Provider
                           │
          ┌────────────────┼────────────────┐
          │                │                │
      Telegram          Discord          S3 / B2
          │                │                │
          └────────────────┼────────────────┘
                           │
                     Storage Engine
```

The core engine does not need to know how Telegram or Discord works.

This makes it possible to add new providers without rewriting the storage system.

Planned providers include:

* S3-compatible storage
* Backblaze B2
* Google Drive
* Local filesystem
* WebDAV
* Other community-built providers

---

### Asynchronous transfers

Stashify is designed around asynchronous I/O.

Large uploads can consist of hundreds or thousands of chunks, so operations should run concurrently with bounded workers.

```text
                    Upload Queue
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
          Worker 1    Worker 2    Worker 3
             │           │           │
          Telegram     Discord     Telegram
```

The transfer system is designed to support:

* Concurrent uploads
* Concurrent downloads
* Bounded concurrency
* Retries
* Exponential backoff
* Provider-aware rate limiting
* Cancellation
* Progress reporting
* Failed-job tracking
* Resumable operations

---

### Resumable uploads

Interrupted transfers shouldn't mean starting from zero.

```text
200 chunks

chunk 000   ✓
chunk 001   ✓
chunk 002   ✓
...
chunk 147   ✓
chunk 148   ✗
chunk 149   ✗
...
```

Stashify keeps track of individual chunks so completed work can be preserved across interruptions.

---

### Integrity verification

Encrypted chunks are authenticated and tracked using local metadata.

Stashify is designed to detect:

* Missing chunks
* Corrupted chunks
* Modified ciphertext
* Incomplete downloads
* Invalid manifests
* Incorrect chunk ordering
* Failed reconstruction

The final reconstructed file can also be verified against file-level integrity information.

---

### Manifest-based storage

Every stored file has a manifest describing how it can be reconstructed.

Conceptually:

```text
File
├── ID
├── Original name
├── Original size
├── Chunk size
├── Chunk count
├── Encryption metadata
├── Integrity information
│
└── Chunks
    ├── 0 → Telegram → remote ID
    ├── 1 → Discord  → remote ID
    ├── 2 → Telegram → remote ID
    └── ...
```

Local metadata is stored in SQLite.

---

# Terminal UI

Stashify is designed to have a full interactive terminal interface rather than being limited to traditional commands.

Run:

```bash
stashify
```

to launch the TUI.

The interface is designed around a keyboard-first workflow with:

* Local file explorer
* Remote storage explorer
* Multi-file selection
* Upload/download controls
* Live transfer progress
* Provider status
* Transfer queue
* Provider management
* Configuration
* Search
* Command palette
* Keyboard shortcuts

Conceptually:

```text
┌──────────────────────────────────────────────────────────────────────┐
│ STASHIFY                                      Telegram ● Discord ●    │
├──────────────────────────────┬───────────────────────────────────────┤
│ LOCAL                        │ REMOTE STORAGE                         │
│                              │                                       │
│ ~/                           │ Stash                                 │
│                              │                                       │
│ > Documents/                 │ > Documents/                           │
│   Downloads/                 │   Projects/                            │
│   Pictures/                  │   Backups/                             │
│                              │                                       │
│ [x] project.zip              │ project.zip    2.4 GB    T+D    ✓     │
│ [ ] README.md                │ backup.tar     14 GB     T      ✓     │
│ [ ] photo.png                │ movie.mkv      8.1 GB    T+D    ✓     │
│                              │                                       │
├──────────────────────────────┴───────────────────────────────────────┤
│ TRANSFERS                                                            │
│ project.zip  ↑ 78%  ███████████████░░░░  Telegram + Discord         │
├──────────────────────────────────────────────────────────────────────┤
│ ↑↓ Navigate   Tab Pane   Space Select   U Upload   D Download   ?    │
└──────────────────────────────────────────────────────────────────────┘
```

The TUI and traditional CLI share the same underlying storage engine.

---

# CLI

Stashify can also be used without the interactive interface.

```bash
# Initialize
stashify init

# Configure providers
stashify provider add telegram
stashify provider add discord

# List providers
stashify provider list

# Upload
stashify put ./movie.mkv

# List stored files
stashify ls

# Inspect a file
stashify info movie.mkv

# Download
stashify get movie.mkv

# Delete
stashify rm movie.mkv

# Verify
stashify verify movie.mkv

# Check status
stashify status
```

The exact command set may evolve during development.

---

# Provider Support

| Provider         | Status         |
| ---------------- | -------------- |
| Telegram         | In development |
| Discord          | Planned        |
| S3-compatible    | Planned        |
| Backblaze B2     | Planned        |
| Google Drive     | Planned        |
| Local filesystem | Planned        |
| WebDAV           | Planned        |

Provider availability and capabilities are subject to the APIs, limits, and policies of the respective services.

### About "unlimited storage"

Stashify does **not** provide unlimited storage.

It does not bypass provider limits or guarantee unlimited capacity.

Actual storage capacity, file-size limits, rate limits, retention policies, and availability depend on the underlying provider.

Stashify's job is to abstract those providers and make the best use of the storage available to the user.

---

# Security & Privacy

Stashify is designed around a simple trust model:

```text
             Trusted
                │
                ▼
          ┌───────────┐
          │ User Device│
          └─────┬─────┘
                │
          encrypted data
                │
        ┌───────┴───────┐
        ▼               ▼
    Telegram          Discord
    untrusted         untrusted
     storage           storage
```

### Principles

**Local-first encryption**

Plaintext files are processed locally before being uploaded.

**Untrusted providers**

Storage providers are treated as storage infrastructure, not trusted holders of plaintext data.

**No custom cryptography**

Stashify uses established cryptographic implementations.

**Authenticated data**

Encrypted chunks should provide confidentiality and integrity.

**Minimal exposure**

Provider APIs should receive only the information required to store and retrieve encrypted data.

**Open source**

The codebase is intended to remain publicly auditable.

> Stashify is early-stage software. Do not rely on it for critical backups until the security model, implementation, and recovery mechanisms have been thoroughly reviewed.

---

# Architecture

At a high level:

```text
                         ┌───────────────┐
                         │   Stashify    │
                         │      TUI      │
                         └───────┬───────┘
                                 │
                         ┌───────▼───────┐
                         │      CLI      │
                         └───────┬───────┘
                                 │
                         ┌───────▼───────┐
                         │  Core Engine  │
                         └───────┬───────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
          Encryption          Chunking           Metadata
              │                  │                  │
              └──────────────────┼──────────────────┘
                                 │
                         ┌───────▼───────┐
                         │ Storage Router│
                         └───────┬───────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
                Telegram      Discord       Future
                                             Providers
```

The architecture intentionally separates:

* User interface
* Core storage logic
* Cryptography
* Chunking
* Metadata
* Job execution
* Provider implementations

This allows the system to evolve without coupling the entire codebase to a specific provider.

---

# Project Status

> **Stashify is currently in early development.**

The architecture is being actively developed and APIs may change significantly.

| Component              | Status      |
| ---------------------- | ----------- |
| Project architecture   | In progress |
| Python CLI             | In progress |
| TUI                    | In progress |
| Encryption             | In progress |
| Chunking               | In progress |
| Manifest / metadata    | In progress |
| Provider abstraction   | In progress |
| Telegram provider      | In progress |
| Discord provider       | Planned     |
| Async job engine       | In progress |
| Resumable transfers    | Planned     |
| Multi-provider routing | Planned     |
| Verification           | Planned     |
| Repair / recovery      | Future      |
| Additional providers   | Future      |

Features marked **Planned** or **Future** should not be considered implemented.

---

# Development

Stashify is built with Python and is designed around asynchronous I/O.

The project aims to keep the core storage engine independent from its user interfaces and provider implementations.

A typical architecture is:

```text
UI
 │
 ├── TUI
 └── CLI
      │
      ▼
Core Storage Engine
      │
 ├── Crypto
 ├── Chunking
 ├── Metadata
 ├── Jobs
 └── Storage Router
      │
      ├── Telegram
      ├── Discord
      └── Future Providers
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

---

# Contributing

Contributions are welcome.

Some areas where contributions will be especially useful:

* Storage providers
* Encryption and security review
* Chunking and transfer reliability
* TUI/UX improvements
* Testing
* Documentation
* Performance
* Cross-platform support

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

If you discover a potential security vulnerability, please follow the project's security reporting process rather than publicly disclosing the issue immediately.

---

# Roadmap

The long-term goal is to turn Stashify into a flexible encrypted storage layer that can sit on top of almost any suitable storage provider.

### Near term

* [x] Core encryption pipeline
* [x] Chunking
* [ ] SQLite metadata
* [x] Telegram provider
* [x] Discord provider
* [x] Async transfer system
* [ ] Resumable uploads

### Medium term

* [ ] Multi-provider routing
* [ ] Replication
* [ ] Integrity verification
* [ ] Recovery/repair
* [ ] Provider health monitoring

### Long term

* [ ] S3-compatible providers
* [ ] Backblaze B2
* [ ] Google Drive
* [ ] WebDAV
* [ ] Local filesystem backend
* [ ] Additional community providers
* [ ] Advanced redundancy strategies

The roadmap is intentionally flexible and will evolve as the project matures.

---

# License

Stashify is released under the **MIT License**.

See [LICENSE](LICENSE) for the full license text.

---

<p align="center">
  <strong>Stashify</strong><br>
  <sub>Your files. Your keys. Your storage.</sub>
</p>
