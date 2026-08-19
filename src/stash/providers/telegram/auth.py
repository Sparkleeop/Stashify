"""Telegram provider authentication."""

from dataclasses import dataclass

TELEGRAM_API_BASE = "https://api.telegram.org/bot"


@dataclass(frozen=True, slots=True)
class TelegramAuth:
    """Telegram authentication configuration."""
    bot_token: str

    def get_api_url(self) -> str:
        """Get the base API URL with token."""
        return f"{TELEGRAM_API_BASE}{self.bot_token}"