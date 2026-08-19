# Installation

## Prerequisites

- Python 3.11+
- pip (Python package manager)

## Install from PyPI

```bash
pip install stash
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
docker pull ghcr.io/sparkleeop/stash:latest
docker run --rm -v /path/to/repo:/repo ghcr.io/sparkleeop/stash:latest --repo /repo init
```

## Requirements

- Python 3.11+
- Dependencies are automatically installed via pip
- Optional: Docker for containerized deployment

## Platform Support

| OS | Status |
|------|--------|
| Linux | ✅ Fully supported |
| macOS | ✅ Fully supported |
| Windows | ✅ Fully supported |
| Docker | ✅ Supported |