"""Tests for crypto module."""

import pytest
from stash.core.crypto import CryptoEngine, EncryptionConfig, FileKey


def test_crypto_engine_initialization():
    """Test CryptoEngine can be initialized."""
    config = EncryptionConfig()
    engine = CryptoEngine(config)
    assert engine.config == config


def test_generate_file_key():
    """Test file key generation from RMK."""
    engine = CryptoEngine()
    rmk = b"0" * 32  # dummy RMK for testing
    file_key = engine.generate_file_key(rmk)
    assert file_key.key is not None
    assert len(file_key.key) == 32
    assert file_key.salt is not None
    assert len(file_key.salt) == 16


def test_derive_chunk_key():
    """Test chunk key derivation."""
    engine = CryptoEngine()
    rmk = b"0" * 32
    file_key = engine.generate_file_key(rmk)
    chunk_key_0 = engine.derive_chunk_key(file_key, 0)
    chunk_key_1 = engine.derive_chunk_key(file_key, 1)
    assert chunk_key_0 != chunk_key_1
    assert len(chunk_key_0) == 32


def test_encrypt_decrypt_chunk():
    """Test chunk encryption and decryption round-trip."""
    engine = CryptoEngine()
    rmk = b"0" * 32
    file_key = engine.generate_file_key(rmk)
    data = b"test data for encryption"

    encrypted = engine.encrypt_chunk(data, file_key, 0)
    assert encrypted.ciphertext != data
    assert encrypted.nonce is not None
    assert encrypted.chunk_index == 0

    decrypted = engine.decrypt_chunk(encrypted, file_key)
    assert decrypted == data


def test_encrypt_empty_chunk_raises():
    """Test encrypting empty chunk raises error."""
    engine = CryptoEngine()
    rmk = b"0" * 32
    file_key = engine.generate_file_key(rmk)
    with pytest.raises(Exception):
        engine.encrypt_chunk(b"", file_key, 0)


def test_decrypt_wrong_key_fails():
    """Test decrypting with wrong key fails."""
    engine = CryptoEngine()
    rmk = b"0" * 32
    file_key1 = engine.generate_file_key(rmk)
    file_key2 = engine.generate_file_key(rmk)
    data = b"test data"

    encrypted = engine.encrypt_chunk(data, file_key1, 0)
    with pytest.raises(Exception):
        engine.decrypt_chunk(encrypted, file_key2)


def test_filename_encryption():
    """Test filename encryption and decryption."""
    engine = CryptoEngine()
    rmk = b"0" * 32
    file_key = engine.generate_file_key(rmk)
    filename = b"test_file.txt"

    ciphertext, nonce = engine.encrypt_filename(filename, file_key)
    assert ciphertext is not None
    assert nonce is not None
    assert len(nonce) == 12

    decrypted = engine.decrypt_filename(ciphertext, nonce, file_key)
    assert decrypted == filename


def test_derive_file_key_from_rmk():
    """Test deriving file key directly from RMK and file_id."""
    engine = CryptoEngine()
    rmk = b"0" * 32
    file_id = b"test-file-id-123"

    file_key = engine.derive_file_key_from_rmk(rmk, file_id)
    assert isinstance(file_key, FileKey)
    assert file_key.key is not None
    assert len(file_key.key) == 32
    assert file_key.salt == file_id


def test_deterministic_file_key():
    """Test that same RMK + file_id always produces same file key."""
    engine = CryptoEngine()
    rmk = b"0" * 32
    file_id = b"test-file-id-456"

    file_key1 = engine.derive_file_key_from_rmk(rmk, file_id)
    file_key2 = engine.derive_file_key_from_rmk(rmk, file_id)
    assert file_key1.key == file_key2.key
    assert file_key1.salt == file_key2.salt


def test_different_rmk_different_key():
    """Test that different RMKs produce different file keys."""
    engine = CryptoEngine()
    file_id = b"test-file-id-789"

    file_key1 = engine.derive_file_key_from_rmk(b"0" * 32, file_id)
    file_key2 = engine.derive_file_key_from_rmk(b"1" * 32, file_id)
    assert file_key1.key != file_key2.key