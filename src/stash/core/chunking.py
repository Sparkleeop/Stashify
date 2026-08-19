"""File chunking with provider-aware sizing."""

import math
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from stash.core.exceptions import ChunkingError

DEFAULT_CHUNK_SIZE: int = 50 * 1024 * 1024
MIN_CHUNK_SIZE: int = 1024 * 1024
MAX_CHUNK_SIZE: int = 2 * 1024 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ChunkConfig:
    """Chunking configuration."""
    chunk_size: int = DEFAULT_CHUNK_SIZE
    min_chunk_size: int = field(default=MIN_CHUNK_SIZE, init=False)
    max_chunk_size: int = field(default=MAX_CHUNK_SIZE, init=False)

    def __post_init__(self) -> None:
        if not (self.min_chunk_size <= self.chunk_size <= self.max_chunk_size):
            raise ChunkingError(
                f"chunk_size must be between {self.min_chunk_size} and {self.max_chunk_size}"
            )

    @classmethod
    def from_provider_limit(cls, max_size: int, overhead: int = 1024 * 1024) -> "ChunkConfig":
        """Create config from provider's max file size with overhead buffer."""
        chunk_size = max(max_size - overhead, MIN_CHUNK_SIZE)
        chunk_size = min(chunk_size, MAX_CHUNK_SIZE)
        return cls(chunk_size=chunk_size)


@dataclass(frozen=True, slots=True)
class Chunk:
    """A file chunk with its data and metadata."""
    index: int
    data: bytes
    offset: int
    size: int
    is_last: bool


class Chunker:
    """Splits files into chunks for provider upload."""

    def __init__(self, config: ChunkConfig | None = None):
        self.config = config or ChunkConfig()

    def chunk_file(self, file_path: Path) -> Iterator[Chunk]:
        """Iterate over chunks of a file."""
        file_size = file_path.stat().st_size
        if file_size == 0:
            raise ChunkingError("Cannot chunk empty file")

        num_chunks = math.ceil(file_size / self.config.chunk_size)

        with file_path.open("rb") as f:
            for i in range(num_chunks):
                offset = i * self.config.chunk_size
                remaining = file_size - offset
                chunk_size = min(self.config.chunk_size, remaining)
                data = f.read(chunk_size)
                if len(data) != chunk_size:
                    raise ChunkingError(f"Short read at chunk {i}: expected {chunk_size}, got {len(data)}")
                yield Chunk(
                    index=i,
                    data=data,
                    offset=offset,
                    size=len(data),
                    is_last=(i == num_chunks - 1),
                )

    def chunk_data(self, data: bytes) -> list[Chunk]:
        """Split raw bytes into chunks."""
        if not data:
            raise ChunkingError("Cannot chunk empty data")

        num_chunks = math.ceil(len(data) / self.config.chunk_size)
        chunks = []
        for i in range(num_chunks):
            offset = i * self.config.chunk_size
            chunk_data = data[offset:offset + self.config.chunk_size]
            chunks.append(Chunk(
                index=i,
                data=chunk_data,
                offset=offset,
                size=len(chunk_data),
                is_last=(i == num_chunks - 1),
            ))
        return chunks

    def get_num_chunks(self, file_size: int) -> int:
        """Calculate number of chunks for a given file size."""
        return math.ceil(file_size / self.config.chunk_size)

    def reconstruct(self, chunks: list[Chunk]) -> bytes:
        """Reconstruct original data from chunks (for testing)."""
        chunks_sorted = sorted(chunks, key=lambda c: c.index)
        return b"".join(c.data for c in chunks_sorted)