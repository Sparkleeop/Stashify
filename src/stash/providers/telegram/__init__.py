"""Telegram storage provider for Stash."""

from stash.providers.telegram.provider import TelegramProvider
from stash.providers.telegram.auth import TelegramAuth
from stash.providers.telegram.limits import get_telegram_limits

__all__ = [
    "TelegramProvider",
    "TelegramAuth",
    "get_telegram_limits",
]