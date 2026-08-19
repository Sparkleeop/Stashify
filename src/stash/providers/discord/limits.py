"""Discord provider limits and constraints."""

from dataclasses import dataclass, field

from stash.core.storage import ProviderLimits

MAX_FILE_SIZE: int = 25 * 1024 * 1024
ENCRYPTION_OVERHEAD: int = 12 + 16
MAX_CHUNK_SIZE: int = MAX_FILE_SIZE - ENCRYPTION_OVERHEAD
MAX_EMBED_SIZE: int = 6000
MAX_MESSAGE_LENGTH: int = 2000
RATE_LIMIT_GLOBAL: int = 50
RATE_LIMIT_PER_ROUTE: int = 5
RATE_LIMIT_WINDOW: int = 1


@dataclass(frozen=True, slots=True)
class DiscordLimits:
    """Discord-specific limits."""
    max_file_size: int = field(default=MAX_FILE_SIZE, init=False)
    max_embed_size: int = field(default=MAX_EMBED_SIZE, init=False)
    max_message_length: int = field(default=MAX_MESSAGE_LENGTH, init=False)
    rate_limit_global: int = field(default=RATE_LIMIT_GLOBAL, init=False)
    rate_limit_per_route: int = field(default=RATE_LIMIT_PER_ROUTE, init=False)
    rate_limit_window: int = field(default=RATE_LIMIT_WINDOW, init=False)


def get_discord_limits() -> ProviderLimits:
    """Get Discord provider limits."""
    return ProviderLimits(
        max_file_size=MAX_FILE_SIZE,
        max_chunk_size=MAX_CHUNK_SIZE,
        max_concurrent_uploads=3,
        rate_limit_requests=RATE_LIMIT_PER_ROUTE,
        rate_limit_window=RATE_LIMIT_WINDOW,
        supports_resumable=False,
        supports_multipart=False,
    )