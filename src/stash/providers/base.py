"""Provider registry and base classes."""

from collections.abc import Callable
from typing import TypeVar

from stash.core.storage import BaseStorageProvider, ProviderConfig

T = TypeVar("T", bound=type[BaseStorageProvider])


class ProviderRegistry:
    """Registry for storage providers."""

    _providers: dict[str, type[BaseStorageProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[BaseStorageProvider]) -> None:
        """Register a provider class."""
        cls._providers[name.lower()] = provider_class

    @classmethod
    def get(cls, name: str) -> type[BaseStorageProvider]:
        """Get a provider class by name."""
        provider = cls._providers.get(name.lower())
        if not provider:
            raise KeyError(f"Provider '{name}' not registered. Available: {list(cls._providers.keys())}")
        return provider

    @classmethod
    async def create(cls, name: str, config: ProviderConfig) -> BaseStorageProvider:
        """Create and initialize a provider instance."""
        provider_class = cls.get(name)
        instance = provider_class()
        await instance.initialize(config)
        return instance

    @classmethod
    def list_providers(cls) -> list[str]:
        """List registered provider names."""
        return list(cls._providers.keys())


def register_provider(name: str) -> Callable[[T], T]:
    """Decorator to register a provider."""
    def decorator(cls: T) -> T:
        ProviderRegistry.register(name, cls)
        return cls
    return decorator