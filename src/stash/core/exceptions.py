"""Custom exceptions for Stash."""


class StashError(Exception):
    """Base exception for all Stash errors."""
    pass


class CryptoError(StashError):
    """Cryptography-related errors."""
    pass


class ChunkingError(StashError):
    """File chunking errors."""
    pass


class ManifestError(StashError):
    """Manifest parsing/validation errors."""
    pass


class ProviderError(StashError):
    """Storage provider errors."""
    pass


class ProviderAuthError(ProviderError):
    """Authentication/authorization errors with provider."""
    pass


class ProviderRateLimitError(ProviderError):
    """Rate limit exceeded."""
    pass


class ProviderNotFoundError(ProviderError):
    """Provider not found or not configured."""
    pass


class MetadataError(StashError):
    """Metadata storage errors."""
    pass


class JobError(StashError):
    """Job execution errors."""
    pass


class JobCancelledError(JobError):
    """Job was cancelled."""
    pass


class ConfigurationError(StashError):
    """Configuration errors."""
    pass


class ValidationError(StashError):
    """Input validation errors."""
    pass