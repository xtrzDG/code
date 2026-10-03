"""Why a customer file could not be fetched from its messaging platform."""

from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)


class MediaTooLargeError(ValidationFailedError):
    """The file is larger than the platform downloads for its kind."""


class MediaUnavailableError(ExternalServiceError):
    """
    The platform no longer hands out the file (expired, deleted, an address
    that is not the platform's): asking again cannot help.
    """


class TranscriptionNotConfiguredError(ExternalServiceError):
    """
    No speech-to-text service is configured (OPENAI_API_KEY missing, or an
    offline model): voice notes are answered with a request to write.
    """
