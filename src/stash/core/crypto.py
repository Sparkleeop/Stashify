"""Client-side encryption using AES-GCM (cryptography library)."""

import secrets
from dataclasses import dataclass
from typing import Final

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from stash.core.exceptions import CryptoError

NONCE_SIZE: Final[int] = 12
KEY_SIZE: Final[int] = 32
TAG_SIZE: Final[int] = 16
SALT_SIZE: Final[int] = 16


@dataclass(frozen=True, slots=True)
class EncryptionConfig:
    """Encryption configuration."""
    algorithm: str = "AES-256-GCM"
    key_size: int = KEY_SIZE
    nonce_size: int = NONCE_SIZE
    chunk_key_derivation: str = "HKDF-SHA256"


@dataclass(frozen=True, slots=True)
class EncryptedChunk:
    """An encrypted chunk with its metadata."""
    ciphertext: bytes
    nonce: bytes
    chunk_index: int


@dataclass(frozen=True, slots=True)
class FileKey:
    """Per-file encryption key with derivation info."""
    key: bytes
    salt: bytes
    config: EncryptionConfig


class CryptoEngine:
    """Handles all encryption/decryption operations."""

    def __init__(self, config: EncryptionConfig | None = None):
        self.config = config or EncryptionConfig()

    def generate_file_key(self, rmk: bytes) -> FileKey:
        """Generate a new per-file encryption key derived from RMK."""
        salt = secrets.token_bytes(SALT_SIZE)
        file_key = self._derive_file_key(rmk, salt)
        return FileKey(key=file_key, salt=salt, config=self.config)

    def _derive_file_key(self, rmk: bytes, file_id: bytes) -> bytes:
        """Derive a file encryption key from RMK and file ID."""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=self.config.key_size,
            salt=file_id,
            info=b"stash-file-key",
        )
        return hkdf.derive(rmk)

    def derive_file_key_from_rmk(self, rmk: bytes, file_id: bytes) -> FileKey:
        """Derive a FileKey from RMK and file ID."""
        file_key = self._derive_file_key(rmk, file_id)
        return FileKey(key=file_key, salt=file_id, config=self.config)

    def derive_chunk_key(self, file_key: FileKey, chunk_index: int) -> bytes:
        """Derive a per-chunk key from the file key."""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=self.config.key_size,
            salt=file_key.salt,
            info=f"stash-chunk-{chunk_index}".encode(),
        )
        return hkdf.derive(file_key.key)

    def encrypt_chunk(self, data: bytes, file_key: FileKey, chunk_index: int) -> EncryptedChunk:
        """Encrypt a single chunk."""
        if len(data) == 0:
            raise CryptoError("Cannot encrypt empty chunk")

        chunk_key = self.derive_chunk_key(file_key, chunk_index)
        nonce = secrets.token_bytes(self.config.nonce_size)
        aesgcm = AESGCM(chunk_key)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return EncryptedChunk(ciphertext=ciphertext, nonce=nonce, chunk_index=chunk_index)

    def decrypt_chunk(self, encrypted: EncryptedChunk, file_key: FileKey) -> bytes:
        """Decrypt a single chunk."""
        chunk_key = self.derive_chunk_key(file_key, encrypted.chunk_index)
        aesgcm = AESGCM(chunk_key)
        try:
            return aesgcm.decrypt(encrypted.nonce, encrypted.ciphertext, None)
        except Exception as e:
            raise CryptoError(f"Decryption failed for chunk {encrypted.chunk_index}: {e}") from e

    def encrypt_filename(self, filename: bytes, file_key: FileKey) -> tuple[bytes, bytes]:
        """Encrypt a filename using the file key."""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=self.config.key_size,
            salt=file_key.salt,
            info=b"stash-filename",
        )
        filename_key = hkdf.derive(file_key.key)
        nonce = secrets.token_bytes(self.config.nonce_size)
        aesgcm = AESGCM(filename_key)
        ciphertext = aesgcm.encrypt(nonce, filename, None)
        return ciphertext, nonce

    def decrypt_filename(self, ciphertext: bytes, nonce: bytes, file_key: FileKey) -> bytes:
        """Decrypt a filename using the file key."""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=self.config.key_size,
            salt=file_key.salt,
            info=b"stash-filename",
        )
        filename_key = hkdf.derive(file_key.key)
        aesgcm = AESGCM(filename_key)
        try:
            return aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as e:
            raise CryptoError(f"Filename decryption failed: {e}") from e