"""Tests for manifest module."""

import pytest
from stash.core.manifest import (
    ChunkInfo,
    FileManifest,
    ManifestBuilder,
    EncryptionInfo,
    DistributionStrategy,
    compute_checksum,
    generate_file_id,
)
from stash.core.crypto import CryptoEngine


def test_compute_checksum():
    """Test checksum computation."""
    data = b"test data"
    checksum = compute_checksum(data)
    assert len(checksum) == 64  # SHA256 hex


def test_generate_file_id():
    """Test file ID generation."""
    file_id = generate_file_id()
    assert len(file_id) == 16


def test_encryption_info():
    """Test EncryptionInfo dataclass."""
    enc = EncryptionInfo(
        algorithm="AES-256-GCM",
        key_size=32,
        nonce_size=12,
        chunk_key_derivation="HKDF-SHA256",
        file_key_salt=b"salt",
    )
    assert enc.algorithm == "AES-256-GCM"
    assert enc.file_key_wrapped is None


def test_chunk_info():
    """Test ChunkInfo dataclass."""
    chunk = ChunkInfo(
        index=0,
        size=100,
        encrypted_size=120,
        checksum="abc",
        provider="discord",
        remote_id="msg123",
        nonce=b"nonce",
    )
    assert chunk.index == 0
    assert chunk.metadata == {}


def test_manifest_builder():
    """Test ManifestBuilder."""
    crypto = CryptoEngine()
    rmk = b"0" * 32
    file_key = crypto.generate_file_key(rmk)
    enc = EncryptionInfo(
        algorithm="AES-256-GCM",
        key_size=32,
        nonce_size=12,
        chunk_key_derivation="HKDF-SHA256",
        file_key_salt=file_key.salt,
    )

    # Encrypt filename using file key
    ciphertext, nonce = crypto.encrypt_filename(b"test.txt", file_key)
    encrypted_name = ciphertext.hex()
    encrypted_name_nonce = nonce

    builder = ManifestBuilder(
        file_id="test123",
        original_name="test.txt",
        encrypted_name=encrypted_name,
        encrypted_name_nonce=nonce,
        original_size=1000,
        chunk_size=1024,
        encryption=enc,
        strategy=DistributionStrategy.SINGLE,
    )

    builder.add_chunk(0, 100, 120, "checksum", "discord", "msg1", b"nonce")
    manifest = builder.build()

    assert manifest.file_id == "test123"
    assert manifest.original_name == "test.txt"
    assert manifest.chunk_count == 1
    assert manifest.chunks[0].index == 0


def test_manifest_serialization():
    """Test manifest JSON serialization round-trip."""
    crypto = CryptoEngine()
    rmk = b"0" * 32
    file_key = crypto.generate_file_key(rmk)

    enc = EncryptionInfo(
        algorithm="AES-256-GCM",
        key_size=32,
        nonce_size=12,
        chunk_key_derivation="HKDF-SHA256",
        file_key_salt=file_key.salt,
    )

    # Encrypt filename using file key
    ciphertext, nonce = crypto.encrypt_filename(b"test.txt", file_key)
    encrypted_name = ciphertext.hex()
    encrypted_name_nonce = nonce

    builder = ManifestBuilder(
        file_id="test123",
        original_name="test.txt",
        encrypted_name=encrypted_name,
        encrypted_name_nonce=nonce,
        original_size=1000,
        chunk_size=1024,
        encryption=enc,
        strategy=DistributionStrategy.SINGLE,
    )

    builder.add_chunk(0, 100, 120, "checksum", "discord", "msg1", b"nonce")
    manifest = builder.build()

    # Serialize
    json_str = manifest.to_json()
    assert "test123" in json_str
    assert "discord" in json_str

    # Deserialize
    manifest2 = FileManifest.from_json(json_str)
    assert manifest2.file_id == manifest.file_id
    assert manifest2.original_name == manifest.original_name
    assert manifest2.chunk_count == manifest.chunk_count
    assert manifest2.chunks[0].remote_id == manifest.chunks[0].remote_id


def test_distribution_strategies():
    """Test all distribution strategies."""
    for strategy in DistributionStrategy:
        assert strategy.value in ["single", "split", "balanced", "replicated"]


def test_filename_encryption_in_manifest():
    """Test that filename encryption works correctly in manifest round-trip."""
    crypto = CryptoEngine()
    rmk = b"0" * 32
    file_key = crypto.generate_file_key(rmk)

    enc = EncryptionInfo(
        algorithm="AES-256-GCM",
        key_size=32,
        nonce_size=12,
        chunk_key_derivation="HKDF-SHA256",
        file_key_salt=file_key.salt,
    )

    original_name = "my_test_file.txt"
    ciphertext, nonce = crypto.encrypt_filename(original_name.encode(), file_key)
    encrypted_name = ciphertext.hex()
    encrypted_name_nonce = nonce

    builder = ManifestBuilder(
        file_id="test456",
        original_name=original_name,
        encrypted_name=encrypted_name,
        encrypted_name_nonce=nonce,
        original_size=2000,
        chunk_size=1024,
        encryption=enc,
        strategy=DistributionStrategy.SINGLE,
    )

    builder.add_chunk(0, 500, 520, "checksum1", "discord", "msg1", b"nonce1")
    builder.add_chunk(1, 500, 520, "checksum2", "telegram", "msg2", b"nonce2")
    manifest = builder.build()

    # Serialize and deserialize
    json_str = manifest.to_json()
    manifest2 = FileManifest.from_json(json_str)

    # Decrypt filename using decrypt_filename method
    decrypted = crypto.decrypt_filename(
        bytes.fromhex(manifest2.encrypted_name),
        manifest2.encrypted_name_nonce,
        file_key
    )
    assert decrypted.decode() == original_name