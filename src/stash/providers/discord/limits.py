"""Discord provider limits and constraints."""

from dataclasses import dataclass

from stash.core.storage import ProviderLimits

MAX_FILE_SIZE: int = 25 * 1024 * 1024
DEFAULT_CHUNK_SIZE: int = 5 * 1024 * 1024
RATE_LIMIT_GLOBAL: int = 50
RATE_LIMIT_PER_ROUTE: int = 5
RATE_LIMIT_WINDOW: int = 1


@dataclass(frozen=True, slots=True)
class DiscordLimits:
    """Discord-specific limits."""
    max_file_size: int = MAX_FILE_SIZE
    default_chunk_size: int = DEFAULT_CHUNK_SIZE
    rate_limit_global: int = RATE_LIMIT_GLOBAL
    rate_limit_per_route: int = RATE_LIMIT_PER_ROUTE
    rate_limit_window: int = RATE_LIMIT_WINDOW


def get_discord_limits() -> ProviderLimits:
    """Get Discord provider limits."""
    return ProviderLimits(
        max_file_size=MAX_FILE_SIZE,
        max_chunk_size=DEFAULT_CHUNK_SIZE,
        max_concurrent_uploads=3,
        rate_limit_requests=RATE_LIMIT_PER_ROUTE,
        rate_limit_window=RATE_LIMIT_WINDOW,
        supports_resumable=False,
        supports_multipart=False,
    )