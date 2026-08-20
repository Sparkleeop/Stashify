# Installation

## Prerequisites

- Python 3.12+
- pip (Python package manager)

## Install from PyPI

```bash
pip install stashify
```

## Install from Source

```bash
git clone https://github.com/Sparkleeop/Stashify
cd Stashify
pip install -e .
```

## Development Install

```bash
git clone https://github.com/Sparkleeop/Stashify
cd Stashify
pip install -e ".[dev]"
```

## Verify Installation

```bash
stash --help
stash --version
```

## Shell Completion

```bash
# Bash
stash --install-completion bash

# Zsh
stash --install-completion zsh

# Fish
stash --install-completion fish
```

## Docker

```bash
docker pull ghcr.io/sparkleeop/stashify:latest
docker run --rm -v /path/to/repo:/repo ghcr.io/sparkleeop/stashify:latest --repo /repo init
```

## Requirements

- Python 3.12+
- Dependencies are automatically installed via pip
- Optional: Docker for containerized deployment

## Platform Support

| OS | Status |
|------|--------|
| Linux | ✅ Fully supported |
| macOS | ✅ Fully supported |
| Windows | ✅ Fully supported |
| Docker | ✅ Supported |

## First Run: Initialize Repository

After installation, you need to initialize a repository:

```bash
stash init
```

This will:
1. Generate a cryptographically random **Repository Master Key (RMK)**
2. Store the RMK securely in your OS credential store (Windows Credential Manager, macOS Keychain, Linux secret-service)
3. Display a **recovery key (RMK hex)** — **SAVE THIS SECURELY!**

The recovery key is the only way to unlock the repository on a new device or if the keyring entry is lost.

## Configure a Provider

After initialization, add at least one storage provider:

```bash
# Telegram
stash provider add telegram --token <bot_token> --chat-id <chat_id>

# Discord
stash provider add discord --token <bot_token> --channel-id <channel_id>
```

See [Providers](providers/README.md) for detailed setup instructions.