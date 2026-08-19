# Contributing to Stash

Thank you for your interest in contributing to Stash. This guide explains how the project works and how you can help.

---

## Ways to Contribute

- **New storage providers** — the most impactful contributions
- **Core engine improvements** — encryption, chunking, job scheduling, metadata
- **CLI enhancements** — commands, UX, output formatting
- **Testing** — unit, integration, property-based tests
- **Documentation** — README, docs, provider guides, architecture notes
- **Security review** — cryptographic implementation, threat modeling
- **Issue triage** — reproduction, labeling, prioritization
- **Bug fixes** — from typos to logic errors

---

## Architectural Philosophy

### Provider-Agnostic Core

The storage engine (`stash/core`) contains **no provider-specific logic**.

```
stash/
├── core/              # Provider-agnostic: encryption, chunking, manifests, jobs
│   ├── crypto.py
│   ├── chunking.py
│   ├── manifest.py
│   ├── jobs.py
│   └── storage.py     # Abstract StorageProvider interface
├── providers/         # Provider implementations
│   ├── telegram/
│   ├── discord/
│   └── base.py        # Abstract base class
└── cli/               # Command layer
```

**Rule:** If you find yourself adding `if provider == "telegram":` in `core/`, stop. That logic belongs in the provider implementation.

### Adding a New Provider

1. **Read `providers/base.py`** — the abstract `StorageProvider` interface
2. **Create `providers/<name>/`** with:
   - `provider.py` — implements `StorageProvider`
   - `auth.py` — authentication flow (OAuth, bot token, etc.)
   - `limits.py` — provider-specific constraints (max file size, rate limits)
   - `__init__.py` — exports the provider class
3. **Register in `providers/__init__.py`**
4. **Add tests** in `tests/providers/test_<name>.py`
5. **Document** in `docs/providers/<name>.md`

The interface is intentionally minimal:

```python
class StorageProvider(Protocol):
    async def initialize(self, config: ProviderConfig) -> None: ...
    async def upload_chunk(self, chunk: Chunk, remote_path: str) -> RemoteRef: ...
    async def download_chunk(self, remote_ref: RemoteRef) -> bytes: ...
    async def delete_chunk(self, remote_ref: RemoteRef) -> None: ...
    async def list_chunks(self, prefix: str) -> list[RemoteRef]: ...
    def get_limits(self) -> ProviderLimits: ...
```

Provider-specific complexity (Telegram's message IDs, Discord's attachment handling, S3's multipart uploads) stays inside the provider.

---

## Code Quality Expectations

| Area | Expectation |
|------|-------------|
| **Type hints** | Required on all public functions; mypy clean |
| **Async** | Use `asyncio` properly; no blocking I/O in async functions |
| **Error handling** | Custom exception hierarchy; no bare `except:` |
| **Logging** | Structured logging via `structlog`; appropriate levels |
| **Dependencies** | Minimal; justify each addition in PR |
| **Cryptography** | **Never implement primitives.** Use `cryptography` or `pynacl`. |
| **Tests** | New code needs tests; aim for meaningful coverage |

Run before committing:

```bash
make lint      # ruff, mypy
make test      # pytest
make typecheck # mypy
```

---

## Security Expectations

- **No custom crypto** — ever. Use established libraries.
- **Keys never logged** — not in debug, not in errors, not in structured logs.
- **Constant-time operations** where applicable (comparisons, key derivation).
- **Dependency audit** — `pip-audit` or `cargo audit` in CI.
- **Threat model awareness** — document assumptions in provider READMEs.

If you're unsure about a security implication, open a discussion first.

---

## Testing

```
tests/
├── unit/              # Fast, isolated, no network
│   ├── crypto/
│   ├── chunking/
│   ├── manifest/
│   └── jobs/
├── integration/       # Real providers (opt-in, needs credentials)
│   └── providers/
├── property/          # Hypothesis-based property tests
└── fixtures/          # Shared test data
```

- Unit tests: required for all new core logic
- Integration tests: encouraged for providers (marked `@pytest.mark.integration`)
- Property tests: encouraged for encryption/chunking round-trips
- CI runs unit + property tests on every PR
- Integration tests run on schedule and manual trigger

---

## Documentation

- **Docstrings** on all public classes/functions (Google style)
- **Architecture decisions** recorded in `docs/adr/` (Architecture Decision Records)
- **Provider docs** in `docs/providers/<name>.md` — auth, limits, quirks, troubleshooting
- **CLI help text** stays in sync with command implementation
- Update README/CHANGELOG for user-visible changes

---

## Issue Reporting

### Bug Reports

Include:

- Stash version (`stash --version`)
- Python version
- OS
- Provider(s) involved
- Minimal reproduction steps
- Expected vs actual behavior
- Relevant logs (redact sensitive data)

### Security Issues

**Do not open public issues** for suspected vulnerabilities.

Report to: `[project maintainers / security contact]`

Include:

- Description of the vulnerability
- Impact assessment
- Reproduction steps (if safe)
- Suggested fix (if any)

We aim to acknowledge within 48 hours.

---

## Pull Request Process

1. **Fork & branch** — `feature/...`, `fix/...`, `docs/...`, `provider/...`
2. **Small, focused PRs** — one logical change per PR
3. **Descriptive title** — `feat(provider): add S3 multipart upload support`
4. **Description** — what, why, how; link related issues
5. **Tests pass** — CI must be green
6. **Review** — at least one maintainer approval
7. **Squash & merge** — maintainers handle merge strategy

### Commit Messages

Follow conventional commits loosely:

```
feat(core): add resumable upload checkpointing
fix(telegram): handle 429 rate limit on chunk upload
docs: update provider development guide
refactor(jobs): simplify worker pool logic
test(chunking): add property tests for chunk boundaries
```

---

## Branch Practices

| Branch | Purpose |
|--------|---------|
| `main` | Latest stable release |
| `develop` | Integration branch for next release |
| `feature/*` | New functionality |
| `fix/*` | Bug fixes |
| `provider/*` | New provider implementations |
| `release/*` | Release preparation |

Direct pushes to `main`/`develop` are disabled. All changes via PR.

---

## Community Guidelines

- **Be respectful** — technical disagreement ≠ personal conflict
- **Assume good intent** — ask clarifying questions before criticizing
- **Help newcomers** — link docs, explain concepts, don't gatekeep
- **Credit contributors** — in PRs, changelogs, release notes
- **No vendor promotion** — Stash is provider-neutral

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for full expectations.

---

## First-Time Contributors

Look for issues labeled `good first issue` or `help wanted`.

Good starting points:

- Add a missing unit test
- Improve CLI help text
- Document a provider quirk
- Fix a typo in docs
- Add a provider limit constant

Ask questions in the PR or issue — we'd rather clarify than have you guess.

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License (same as the project).

---

*Stash is built by contributors who believe in private, portable, provider-independent storage. Welcome.*