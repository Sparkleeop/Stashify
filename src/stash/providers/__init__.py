"""Stash storage providers."""

from stash.providers.base import ProviderRegistry, register_provider
from stash.providers.discord import DiscordProvider
from stash.providers.telegram import TelegramProvider

ProviderRegistry.register("discord", DiscordProvider)
ProviderRegistry.register("telegram", TelegramProvider)

__all__ = [
    "ProviderRegistry",
    "register_provider",
    "DiscordProvider",
    "TelegramProvider",
]