"""Telegram provider limits and constraints."""


from stash.core.storage import ProviderLimits

MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20MB for regular bots
DEFAULT_CHUNK_SIZE: int = 10 * 1024 * 1024  # 10MB
RATE_LIMIT_PER_SECOND: int = 30


def get_telegram_limits() -> ProviderLimits:
    """Get Telegram provider limits."""
    return ProviderLimits(
        max_file_size=MAX_FILE_SIZE,
        max_chunk_size=DEFAULT_CHUNK_SIZE,
        max_concurrent_uploads=3,
        rate_limit_requests=RATE_LIMIT_PER_SECOND,
        rate_limit_window=1,
        supports_resumable=False,
        supports_multipart=False,
    )