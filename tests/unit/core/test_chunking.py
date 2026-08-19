"""Tests for chunking module."""

import pytest
import tempfile
import os
from pathlib import Path
from stash.core.chunking import Chunker, ChunkConfig, Chunk


def test_chunk_config_defaults():
    """Test default chunk config values."""
    config = ChunkConfig()
    assert config.chunk_size == 50 * 1024 * 1024  # 50MB
    assert config.min_chunk_size == 1024 * 1024  # 1MB
    assert config.max_chunk_size == 2 * 1024 * 1024 * 1024  # 2GB


def test_chunk_config_custom():
    """Test custom chunk config."""
    config = ChunkConfig(chunk_size=1024 * 1024)  # 1MB
    assert config.chunk_size == 1024 * 1024


def test_chunk_config_invalid():
    """Test invalid chunk config raises error."""
    with pytest.raises(Exception):
        ChunkConfig(chunk_size=500 * 1024)  # Below minimum


def test_chunk_config_from_provider_limit():
    """Test creating config from provider limit."""
    config = ChunkConfig.from_provider_limit(10 * 1024 * 1024)
    assert config.chunk_size <= 10 * 1024 * 1024


def test_chunker_empty_file():
    """Test chunking empty file raises error."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"")
        fname = f.name
    try:
        chunker = Chunker()
        with pytest.raises(Exception):
            list(chunker.chunk_file(fname))
    finally:
        os.unlink(fname)


def test_chunker_single_chunk():
    """Test chunking small file."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"Hello, World!")
        fname = Path(f.name)
    try:
        chunker = Chunker(ChunkConfig(chunk_size=1024, min_chunk_size=100))
        chunks = list(chunker.chunk_file(fname))
        assert len(chunks) == 1
        assert chunks[0].data == b"Hello, World!"
        assert chunks[0].index == 0
        assert chunks[0].is_last
    finally:
        os.unlink(fname)


def test_chunker_multiple_chunks():
    """Test chunking large file."""
    chunk_size = 100
    data = b"x" * 350  # 3.5 chunks
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(data)
        fname = Path(f.name)
    try:
        chunker = Chunker(ChunkConfig(chunk_size=chunk_size, min_chunk_size=10))
        chunks = list(chunker.chunk_file(fname))
        assert len(chunks) == 4  # 3 full + 1 partial
        assert chunks[0].size == 100
        assert chunks[1].size == 100
        assert chunks[2].size == 100
        assert chunks[3].size == 50
        assert chunks[3].is_last
        # Verify data integrity
        reconstructed = b"".join(c.data for c in chunks)
        assert reconstructed == data
    finally:
        os.unlink(fname)


def test_chunker_get_num_chunks():
    """Test get_num_chunks method."""
    chunker = Chunker(ChunkConfig(chunk_size=100, min_chunk_size=10))
    assert chunker.get_num_chunks(0) == 0
    assert chunker.get_num_chunks(1) == 1
    assert chunker.get_num_chunks(100) == 1
    assert chunker.get_num_chunks(101) == 2
    assert chunker.get_num_chunks(200) == 2
    assert chunker.get_num_chunks(201) == 3


def test_chunk_reconstruct():
    """Test chunk reconstruction."""
    chunker = Chunker(ChunkConfig(chunk_size=50, min_chunk_size=10))
    data = b"Hello, World! This is a test." * 10
    chunks = chunker.chunk_data(data)
    reconstructed = chunker.reconstruct(chunks)
    assert reconstructed == data