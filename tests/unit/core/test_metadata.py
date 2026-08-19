"""Tests for metadata module."""

import pytest
import tempfile
import os
from pathlib import Path
from stash.core.metadata import MetadataStore
from stash.core.manifest import (
    FileManifest,
    ManifestBuilder,
    EncryptionInfo,
    DistributionStrategy,
    generate_file_id,
)
from stash.core.crypto import CryptoEngine, FileKey


def _make_builder(file_id: str, original_name: str, size: int = 1000):
    """Create a ManifestBuilder with encrypted filename."""
    engine = CryptoEngine()
    file_key = engine.generate_file_key()
    crypto = CryptoEngine()
    encrypted_name_chunk = crypto.encrypt_chunk(original_name.encode(), file_key, -1)
    encrypted_name = encrypted_name_chunk.ciphertext.hex()
    encrypted_name_nonce = encrypted_name_chunk.nonce
    
    enc = EncryptionInfo(
        algorithm="AES-256-GCM",
        key_size=32,
        nonce_size=12,
        chunk_key_derivation="HKDF-SHA256",
        file_key_salt=file_key.salt,
    )
    
    builder = ManifestBuilder(
        file_id=file_id,
        original_name=original_name,
        encrypted_name=encrypted_name,
        encrypted_name_nonce=encrypted_name_nonce,
        original_size=size,
        chunk_size=1024,
        encryption=enc,
        strategy=DistributionStrategy.SINGLE,
    )
    builder.add_chunk(0, 100, 120, "checksum", "discord", "msg1", b"nonce")
    return builder.build()


def test_metadata_store_init():
    """Test MetadataStore initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MetadataStore(Path(tmpdir))
        assert str(store.repo_path) == os.path.abspath(tmpdir)


def test_save_load_manifest():
    """Test saving and loading manifest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MetadataStore(Path(tmpdir))
        manifest = _make_builder("test123", "test.txt", 1000)
        
        store.save_manifest(manifest)
        loaded = store.load_manifest("test123")
        
        assert loaded.file_id == manifest.file_id
        assert loaded.original_name == manifest.original_name
        assert loaded.chunk_count == manifest.chunk_count


def test_list_files():
    """Test listing files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MetadataStore(Path(tmpdir))
        assert store.list_files() == []
        
        for i in range(3):
            manifest = _make_builder(generate_file_id(), f"file{i}.txt", 1000)
            store.save_manifest(manifest)
        
        files = store.list_files()
        assert len(files) == 3


def test_file_exists():
    """Test file_exists method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MetadataStore(Path(tmpdir))
        manifest = _make_builder("test123", "test.txt", 1000)
        store.save_manifest(manifest)
        
        assert store.file_exists("test123")
        assert not store.file_exists("nonexistent")


def test_delete_manifest():
    """Test deleting manifest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MetadataStore(Path(tmpdir))
        manifest = _make_builder("test123", "test.txt", 1000)
        store.save_manifest(manifest)
        
        assert store.file_exists("test123")
        store.delete_manifest("test123")
        assert not store.file_exists("test123")


def test_provider_config():
    """Test provider configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MetadataStore(Path(tmpdir))
        
        from stash.core.storage import ProviderConfig
        config = ProviderConfig(
            name="discord",
            type="discord",
            credentials={"token": "token", "channel_id": "123"},
            settings={"max_concurrent": "3"},
        )
        store.set_provider_config("discord", config)
        
        config = store.get_provider_config("discord")
        assert config is not None
        assert config.type == "discord"
        assert config.credentials["channel_id"] == "123"
        
        providers = store.list_providers()
        assert "discord" in providers
        
        store.remove_provider_config("discord")
        assert "discord" not in store.list_providers()


def test_config_persistence():
    """Test config persistence across store instances."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store1 = MetadataStore(Path(tmpdir))
        
        from stash.core.storage import ProviderConfig
        config = ProviderConfig(
            name="discord",
            type="discord",
            credentials={"token": "token", "channel_id": "123"},
            settings={"max_concurrent": "3"},
        )
        store1.set_provider_config("discord", config)
        
        store2 = MetadataStore(Path(tmpdir))
        config = store2.get_provider_config("discord")
        assert config is not None
        assert config.credentials["channel_id"] == "123"