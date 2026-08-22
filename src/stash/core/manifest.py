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


class ChunkStatus(Enum):
    """Upload status of a chunk."""
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    FAILED = "failed"


class UploadStatus(Enum):
    """Overall upload status of a file."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


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
    status: ChunkStatus = ChunkStatus.PENDING
    uploaded_at: float | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class EncryptionInfo:
    """Encryption parameters for a file."""
    algorithm: str
    key_size: int
    nonce_size: int
    chunk_key_derivation: str
    file_key_salt: bytes
    # file_key_wrapped is no longer used with RMK-based system
    # kept for backwards compatibility
    file_key_wrapped: bytes | None = None


@dataclass(frozen=True, slots=True)
class FileManifest:
    """Complete manifest for a stored file."""
    file_id: str
    original_name: str
    encrypted_name: str
    encrypted_name_nonce: bytes
    original_size: int
    chunk_size: int
    chunk_count: int
    encryption: "EncryptionInfo"
    chunks: tuple["ChunkInfo", ...]
    strategy: DistributionStrategy
    created_at: float
    modified_at: float
    version: int = 1
    upload_status: UploadStatus = UploadStatus.NOT_STARTED
    total_chunks: int = 0
    uploaded_chunks: int = 0
    started_at: float | None = None
    completed_at: float | None = None

    def to_json(self) -> str:
        """Serialize manifest to JSON."""
        data = asdict(self)
        data["chunks"] = [asdict(c) for c in self.chunks]
        data["encryption"] = asdict(self.encryption)
        data["strategy"] = self.strategy.value
        data["encrypted_name_nonce"] = self.encrypted_name_nonce.hex()
        data["upload_status"] = self.upload_status.value
        for chunk in data["chunks"]:
            chunk["nonce"] = chunk["nonce"].hex()
            chunk["status"] = chunk["status"].value
        data["encryption"]["file_key_salt"] = data["encryption"]["file_key_salt"].hex()
        if data["encryption"]["file_key_wrapped"]:
            data["encryption"]["file_key_wrapped"] = data["encryption"]["file_key_wrapped"].hex()
        return json.dumps(data, separators=(",", ":"))

    @classmethod
    def from_json(cls, json_str: str) -> "FileManifest":
        """Deserialize manifest from JSON."""
        data = json.loads(json_str)
        data["strategy"] = DistributionStrategy(data["strategy"])
        data["upload_status"] = UploadStatus(data.get("upload_status", "not_started"))
        enc_data = data["encryption"]
        enc_data["file_key_salt"] = bytes.fromhex(enc_data["file_key_salt"])
        if enc_data["file_key_wrapped"]:
            enc_data["file_key_wrapped"] = bytes.fromhex(enc_data["file_key_wrapped"])
        data["encryption"] = EncryptionInfo(**enc_data)
        data["encrypted_name_nonce"] = bytes.fromhex(data["encrypted_name_nonce"])
        chunks = []
        for c in data["chunks"]:
            c["nonce"] = bytes.fromhex(c["nonce"])
            c["status"] = ChunkStatus(c.get("status", "pending"))
            chunks.append(ChunkInfo(**c))
        data["chunks"] = tuple(chunks)
        return cls(**data)

    def get_chunk(self, index: int) -> "ChunkInfo":
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
    encrypted_name: str
    encrypted_name_nonce: bytes
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
        metadata: dict[str, str] | None = None,
        status: ChunkStatus = ChunkStatus.PENDING,
        uploaded_at: float | None = None,
        error: str | None = None,
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
            metadata=metadata or {},
            status=status,
            uploaded_at=uploaded_at,
            error=error,
        ))

    def build(self) -> "FileManifest":
        """Build the final manifest."""
        if len(self.chunks) == 0:
            raise ManifestError("Cannot build manifest with no chunks")
        
        total = len(self.chunks)
        uploaded = sum(1 for c in self.chunks if c.status == ChunkStatus.UPLOADED)
        status = UploadStatus.NOT_STARTED
        if uploaded == len(self.chunks) and total > 0:
            status = UploadStatus.COMPLETED
        elif uploaded > 0:
            status = UploadStatus.IN_PROGRESS
        elif any(c.status == ChunkStatus.FAILED for c in self.chunks):
            status = UploadStatus.FAILED

        return FileManifest(
            file_id=self.file_id,
            original_name=self.original_name,
            encrypted_name=self.encrypted_name,
            encrypted_name_nonce=self.encrypted_name_nonce,
            original_size=self.original_size,
            chunk_size=self.chunk_size,
            chunk_count=len(self.chunks),
            encryption=self.encryption,
            chunks=tuple(sorted(self.chunks, key=lambda c: c.index)),
            strategy=self.strategy,
            created_at=self.created_at,
            modified_at=time.time(),
            upload_status=status,
            total_chunks=total,
            uploaded_chunks=uploaded,
            started_at=self.chunks[0].uploaded_at if self.chunks else None,
            completed_at=time.time() if status == UploadStatus.COMPLETED else None,
        )


def compute_checksum(data: bytes) -> str:
    """Compute SHA256 checksum of data."""
    return hashlib.sha256(data).hexdigest()


def generate_file_id() -> str:
    """Generate a unique file ID."""
    return hashlib.sha256(f"{time.time()}-{secrets.token_bytes(16).hex()}".encode()).hexdigest()[:16]