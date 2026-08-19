"""Storage provider abstraction - provider-agnostic interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Protocol

from stash.core.chunking import Chunk


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    """Configuration for a storage provider."""
    name: str
    type: str
    credentials: dict[str, str]
    settings: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProviderLimits:
    """Provider-specific limits."""
    max_file_size: int
    max_chunk_size: int
    max_concurrent_uploads: int
    rate_limit_requests: int
    rate_limit_window: int
    supports_resumable: bool = False
    supports_multipart: bool = False


@dataclass(frozen=True, slots=True)
class RemoteRef:
    """Reference to a remote chunk."""
    provider: str
    remote_id: str
    metadata: dict[str, str] = field(default_factory=dict)


class StorageProvider(Protocol):
    """Abstract interface for storage providers."""

    async def initialize(self, config: ProviderConfig) -> None:
        """Initialize the provider with configuration."""
        ...

    async def upload_chunk(self, chunk: Chunk, remote_path: str) -> RemoteRef:
        """Upload a single chunk."""
        ...

    async def download_chunk(self, remote_ref: RemoteRef) -> bytes:
        """Download a single chunk."""
        ...

    async def delete_chunk(self, remote_ref: RemoteRef) -> None:
        """Delete a single chunk."""
        ...

    async def list_chunks(self, prefix: str) -> list[RemoteRef]:
        """List chunks with given prefix."""
        ...

    def get_limits(self) -> ProviderLimits:
        """Get provider limits."""
        ...

    async def close(self) -> None:
        """Clean up resources."""
        ...


class BaseStorageProvider(ABC):
    """Base implementation with common functionality."""

    def __init__(self) -> None:
        self._config: ProviderConfig | None = None
        self._initialized = False

    @property
    def config(self) -> ProviderConfig:
        if self._config is None:
            raise RuntimeError("Provider not initialized")
        return self._config

    @abstractmethod
    async def _initialize(self, config: ProviderConfig) -> None:
        """Provider-specific initialization."""
        pass

    async def initialize(self, config: ProviderConfig) -> None:
        """Initialize the provider."""
        if self._initialized:
            return
        await self._initialize(config)
        self._config = config
        self._initialized = True

    @abstractmethod
    async def upload_chunk(self, chunk: Chunk, remote_path: str) -> RemoteRef:
        pass

    @abstractmethod
    async def download_chunk(self, remote_ref: RemoteRef) -> bytes:
        pass

    @abstractmethod
    async def delete_chunk(self, remote_ref: RemoteRef) -> None:
        pass

    @abstractmethod
    async def list_chunks(self, prefix: str) -> list[RemoteRef]:
        pass

    @abstractmethod
    def get_limits(self) -> ProviderLimits:
        pass

    async def close(self) -> None:
        """Clean up resources."""
        self._initialized = False
        self._config = None