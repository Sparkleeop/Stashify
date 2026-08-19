"""File manifest - tracks chunks, encryption, and provider mapping."""

import hashlib
import json
import secrets
import time
from dataclasses import asdict, dataclass, field
from enum import Enum

from stash.core.exceptions import ManifestError


class DistributionStrategy(Enum):
    """How chunks are distributed across providers."""
    SINGLE = "single"
    SPLIT = "split"
    BALANCED = "balanced"
    REPLICATED = "replicated"


@dataclass(frozen=True, slots=True)
class ChunkInfo:
    """Information about a single chunk."""
    index: int
    size: int
    encrypted_size: int
    checksum: str
    provider: str
    remote_id: str
    nonce: bytes
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EncryptionInfo:
    """Encryption parameters for a file."""
    algorithm: str
    key_size: int
    nonce_size: int
    chunk_key_derivation: str
    file_key_salt: bytes
    file_key_wrapped: bytes | None = None


@dataclass(frozen=True, slots=True)
class FileManifest:
    """Complete manifest for a stored file."""
    file_id: str
    original_name: str
    original_size: int
    chunk_size: int
    chunk_count: int
    encryption: EncryptionInfo
    chunks: tuple[ChunkInfo, ...]
    strategy: DistributionStrategy
    created_at: float
    modified_at: float
    version: int = 1

    def to_json(self) -> str:
        """Serialize manifest to JSON."""
        data = asdict(self)
        data["chunks"] = [asdict(c) for c in self.chunks]
        data["encryption"] = asdict(self.encryption)
        data["strategy"] = self.strategy.value
        for chunk in data["chunks"]:
            chunk["nonce"] = chunk["nonce"].hex()
        data["encryption"]["file_key_salt"] = data["encryption"]["file_key_salt"].hex()
        if data["encryption"]["file_key_wrapped"]:
            data["encryption"]["file_key_wrapped"] = data["encryption"]["file_key_wrapped"].hex()
        return json.dumps(data, separators=(",", ":"))

    @classmethod
    def from_json(cls, json_str: str) -> "FileManifest":
        """Deserialize manifest from JSON."""
        data = json.loads(json_str)
        data["strategy"] = DistributionStrategy(data["strategy"])
        data["encryption"] = EncryptionInfo(**data["encryption"])
        data["encryption"]["file_key_salt"] = bytes.fromhex(data["encryption"]["file_key_salt"])
        if data["encryption"]["file_key_wrapped"]:
            data["encryption"]["file_key_wrapped"] = bytes.fromhex(data["encryption"]["file_key_wrapped"])
        chunks = []
        for c in data["chunks"]:
            c["nonce"] = bytes.fromhex(c["nonce"])
            chunks.append(ChunkInfo(**c))
        data["chunks"] = tuple(chunks)
        return cls(**data)

    def get_chunk(self, index: int) -> ChunkInfo:
        """Get chunk info by index."""
        for chunk in self.chunks:
            if chunk.index == index:
                return chunk
        raise ManifestError(f"Chunk {index} not found in manifest")

    def verify_integrity(self, data: bytes) -> bool:
        """Verify file integrity against manifest."""
        expected = hashlib.sha256(data).hexdigest()
        return expected == self.encryption.file_key_salt.hex()


@dataclass
class ManifestBuilder:
    """Helper to build a FileManifest incrementally."""
    file_id: str
    original_name: str
    original_size: int
    chunk_size: int
    encryption: EncryptionInfo
    strategy: DistributionStrategy = DistributionStrategy.SINGLE
    chunks: list[ChunkInfo] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def add_chunk(
        self,
        index: int,
        size: int,
        encrypted_size: int,
        checksum: str,
        provider: str,
        remote_id: str,
        nonce: bytes,
    ) -> None:
        """Add a chunk to the manifest."""
        self.chunks.append(ChunkInfo(
            index=index,
            size=size,
            encrypted_size=encrypted_size,
            checksum=checksum,
            provider=provider,
            remote_id=remote_id,
            nonce=nonce,
        ))

    def build(self) -> FileManifest:
        """Build the final manifest."""
        if len(self.chunks) == 0:
            raise ManifestError("Cannot build manifest with no chunks")
        return FileManifest(
            file_id=self.file_id,
            original_name=self.original_name,
            original_size=self.original_size,
            chunk_size=self.chunk_size,
            chunk_count=len(self.chunks),
            encryption=self.encryption,
            chunks=tuple(sorted(self.chunks, key=lambda c: c.index)),
            strategy=self.strategy,
            created_at=self.created_at,
            modified_at=time.time(),
        )


def compute_checksum(data: bytes) -> str:
    """Compute SHA256 checksum of data."""
    return hashlib.sha256(data).hexdigest()


def generate_file_id() -> str:
    """Generate a unique file ID."""
    return hashlib.sha256(f"{time.time()}-{secrets.token_bytes(16).hex()}".encode()).hexdigest()[:16]