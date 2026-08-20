"""Repository Master Key management using OS keyring."""

import contextlib
import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

import keyring
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from stash.core.exceptions import KeyManagementError

SERVICE_NAME = "stash"
RMK_KEY_SIZE = 32


@dataclass(frozen=True, slots=True)
class RepositoryIdentity:
    """Non-secret repository identity information."""
    repository_id: str
    created_at: float
    version: int = 1


class KeyManager:
    """Manages the Repository Master Key (RMK) using OS keyring."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.metadata_dir = repo_path / ".stash"
        self.identity_file = self.metadata_dir / "identity.json"

    def _get_keyring_username(self) -> str:
        """Get a unique username for this repository in keyring."""
        repo_id = self._get_repo_id()
        return f"stash:{repo_id}"

    def _get_repo_id(self) -> str:
        """Get or generate a unique repository ID."""
        if self.identity_file.exists():
            try:
                with self.identity_file.open("r") as f:
                    data: dict[str, str] = json.load(f)
                return data.get("repository_id", "")
            except (json.JSONDecodeError, OSError):
                pass
        return ""

    def has_repository_identity(self) -> bool:
        """Check if this repository has an identity (and thus RMK)."""
        return self.identity_file.exists()

    def get_repository_identity(self) -> RepositoryIdentity | None:
        """Get the repository identity if it exists."""
        if not self.identity_file.exists():
            return None
        try:
            with self.identity_file.open("r") as f:
                data = json.load(f)
            return RepositoryIdentity(
                repository_id=data["repository_id"],
                created_at=data["created_at"],
                version=data.get("version", 1),
            )
        except (json.JSONDecodeError, OSError, KeyError):
            return None

    def initialize_repository(self) -> RepositoryIdentity:
        """Initialize a new repository with a new RMK."""
        if self.has_repository_identity():
            raise KeyManagementError("Repository already initialized")

        repo_id = secrets.token_hex(16)

        rmk = secrets.token_bytes(32)
        username = f"stash:{repo_id}"

        try:
            keyring.set_password(SERVICE_NAME, username, rmk.hex())
        except Exception as e:
            raise KeyManagementError(f"Failed to store RMK in keyring: {e}") from e

        identity = RepositoryIdentity(
            repository_id=repo_id,
            created_at=time.time(),
            version=1,
        )

        self._save_identity(identity)
        return identity

    def _save_identity(self, identity: RepositoryIdentity) -> None:
        """Save repository identity to disk."""
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "repository_id": identity.repository_id,
            "created_at": identity.created_at,
            "version": identity.version,
        }
        with self.identity_file.open("w") as f:
            json.dump(data, f)

    def get_rmk(self) -> bytes:
        """Retrieve the RMK from keyring."""
        identity = self.get_repository_identity()
        if identity is None:
            raise KeyManagementError(
                "Repository not initialized. Run 'stash init' first."
            )

        username = f"stash:{identity.repository_id}"
        rmk_hex = keyring.get_password(SERVICE_NAME, username)

        if rmk_hex is None:
            raise KeyManagementError(
                f"RMK not found in keyring for repository {identity.repository_id}. "
                "Run 'stash unlock' to recover."
            )

        try:
            return bytes.fromhex(rmk_hex)
        except ValueError as e:
            raise KeyManagementError(f"Invalid RMK format in keyring: {e}") from e

    def derive_file_key(self, rmk: bytes, file_id: bytes) -> bytes:
        """Derive a file encryption key from RMK and file ID."""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=file_id,
            info=b"stash-file-key",
        )
        return hkdf.derive(rmk)

    def derive_chunk_key(self, file_key: bytes, chunk_index: int) -> bytes:
        """Derive a chunk encryption key from file key and chunk index."""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"",
            info=f"stash-chunk-{chunk_index}".encode(),
        )
        return hkdf.derive(file_key)

    def lock_repository(self) -> None:
        """Remove RMK from keyring (lock the repository)."""
        identity = self.get_repository_identity()
        if identity is None:
            return

        username = f"stash:{identity.repository_id}"
        with contextlib.suppress(keyring.errors.PasswordDeleteError):
            keyring.delete_password(SERVICE_NAME, username)

    def unlock_repository(self, recovery_key: bytes) -> RepositoryIdentity:
        """Unlock repository using a recovery key."""
        if self.has_repository_identity():
            raise KeyManagementError("Repository already initialized")

        repo_id = secrets.token_hex(16)

        username = f"stash:{repo_id}"

        try:
            keyring.set_password(SERVICE_NAME, username, recovery_key.hex())
        except Exception as e:
            raise KeyManagementError(f"Failed to store RMK in keyring: {e}") from e

        identity = RepositoryIdentity(
            repository_id=repo_id,
            created_at=time.time(),
            version=1,
        )
        self._save_identity(identity)
        return identity

    def change_repository_id(self, new_repo_id: str) -> None:
        """Change the repository ID (and thus the keyring entry)."""
        old_identity = self.get_repository_identity()
        if old_identity is None:
            raise KeyManagementError("Repository not initialized")

        old_username = f"stash:{old_identity.repository_id}"
        rmk_hex = keyring.get_password(SERVICE_NAME, old_username)
        if rmk_hex is None:
            raise KeyManagementError("RMK not found in keyring")

        new_username = f"stash:{new_repo_id}"
        try:
            keyring.set_password(SERVICE_NAME, new_username, rmk_hex)
            keyring.delete_password(SERVICE_NAME, old_username)
        except Exception as e:
            raise KeyManagementError(f"Failed to change repository ID: {e}") from e

        self._save_identity(RepositoryIdentity(
            repository_id=new_repo_id,
            created_at=old_identity.created_at,
            version=old_identity.version,
        ))