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

    def generate_file_key(self) -> FileKey:
        """Generate a new per-file encryption key."""
        salt = secrets.token_bytes(SALT_SIZE)
        master_key = secrets.token_bytes(self.config.key_size)
        return FileKey(key=master_key, salt=salt, config=self.config)

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

    def encrypt_file_key(self, file_key: FileKey, password: str) -> bytes:
        """Encrypt a file key with a password (for key wrapping)."""
        salt = secrets.token_bytes(SALT_SIZE)
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=self.config.key_size,
            salt=salt,
            info=b"stash-key-wrap",
        )
        wrapping_key = hkdf.derive(password.encode())
        aesgcm = AESGCM(wrapping_key)
        nonce = secrets.token_bytes(self.config.nonce_size)
        ciphertext = aesgcm.encrypt(nonce, file_key.key, None)
        return salt + nonce + ciphertext

    def decrypt_file_key(self, wrapped: bytes, password: str, salt: bytes, config: EncryptionConfig) -> FileKey:
        """Decrypt a file key with a password."""
        if len(wrapped) < config.nonce_size + TAG_SIZE:
            raise CryptoError("Invalid wrapped key format")
        nonce = wrapped[:config.nonce_size]
        ciphertext = wrapped[config.nonce_size:]
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=config.key_size,
            salt=salt,
            info=b"stash-key-wrap",
        )
        wrapping_key = hkdf.derive(password.encode())
        aesgcm = AESGCM(wrapping_key)
        try:
            key = aesgcm.decrypt(nonce, ciphertext, None)
            return FileKey(key=key, salt=salt, config=config)
        except Exception as e:
            raise CryptoError(f"Key unwrapping failed: {e}") from e