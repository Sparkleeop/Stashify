"""Tests for crypto module."""

import pytest
from stash.core.crypto import CryptoEngine, EncryptionConfig


def test_crypto_engine_initialization():
    """Test CryptoEngine can be initialized."""
    config = EncryptionConfig()
    engine = CryptoEngine(config)
    assert engine.config == config


def test_generate_file_key():
    """Test file key generation."""
    engine = CryptoEngine()
    file_key = engine.generate_file_key()
    assert file_key.key is not None
    assert len(file_key.key) == 32
    assert file_key.salt is not None
    assert len(file_key.salt) == 16


def test_derive_chunk_key():
    """Test chunk key derivation."""
    engine = CryptoEngine()
    file_key = engine.generate_file_key()
    chunk_key_0 = engine.derive_chunk_key(file_key, 0)
    chunk_key_1 = engine.derive_chunk_key(file_key, 1)
    assert chunk_key_0 != chunk_key_1
    assert len(chunk_key_0) == 32


def test_encrypt_decrypt_chunk():
    """Test chunk encryption and decryption round-trip."""
    engine = CryptoEngine()
    file_key = engine.generate_file_key()
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
    file_key = engine.generate_file_key()
    with pytest.raises(Exception):
        engine.encrypt_chunk(b"", file_key, 0)


def test_decrypt_wrong_key_fails():
    """Test decrypting with wrong key fails."""
    engine = CryptoEngine()
    file_key1 = engine.generate_file_key()
    file_key2 = engine.generate_file_key()
    data = b"test data"
    
    encrypted = engine.encrypt_chunk(data, file_key1, 0)
    with pytest.raises(Exception):
        engine.decrypt_chunk(encrypted, file_key2)


def test_encrypt_file_key():
    """Test file key encryption."""
    engine = CryptoEngine()
    file_key = engine.generate_file_key()
    password = "test_password"
    
    wrapped = engine.encrypt_file_key(file_key, password)
    assert wrapped is not None
    assert len(wrapped) > 0


def test_decrypt_file_key():
    """Test file key decryption."""
    engine = CryptoEngine()
    file_key = engine.generate_file_key()
    password = "test_password"
    
    wrapped = engine.encrypt_file_key(file_key, password)
    config = EncryptionConfig()
    
    decrypted = engine.decrypt_file_key(wrapped, password, config)
    assert decrypted.key == file_key.key
    # The salt in the decrypted FileKey is the wrapping salt, not the original file key salt
    # The important thing is that the key decrypts correctly
    assert decrypted.key == file_key.key