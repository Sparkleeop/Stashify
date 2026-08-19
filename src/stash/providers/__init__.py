"""Stash storage providers."""

from stash.providers.base import ProviderRegistry, register_provider
from stash.providers.discord import DiscordProvider

ProviderRegistry.register("discord", DiscordProvider)

__all__ = [
    "ProviderRegistry",
    "register_provider",
    "DiscordProvider",
]