"""Discord provider authentication."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DiscordAuth:
    """Discord authentication configuration."""
    token: str
    is_bot: bool = True
    application_id: str | None = None

    @classmethod
    def from_bot_token(cls, token: str) -> "DiscordAuth":
        """Create auth from bot token."""
        return cls(token=token, is_bot=True)

    @classmethod
    def from_user_token(cls, token: str) -> "DiscordAuth":
        """Create auth from user token."""
        return cls(token=token, is_bot=False)

    def get_auth_header(self) -> str:
        """Get the Authorization header value."""
        prefix = "Bot" if self.is_bot else ""
        return f"{prefix} {self.token}".strip()


DISCORD_API_BASE = "https://discord.com/api/v10"