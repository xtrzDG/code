from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.exceptions.base_exception import ApplicationError


class BackupToolError(ExternalServiceError):
    """
    pg_dump, pg_restore or the scratch database failed; the message names
    the step and the tool's last error lines (no row contents).
    """


class BackupArchiveCorruptError(ValidationFailedError):
    """
    A downloaded archive differs from its manifest (size or SHA-256), does
    not open with the identity, or was changed or cut off.
    """


class RestoreDrillFailedError(ApplicationError):
    """
    The restore drill restored the archive but some checks failed; the
    message lists them (reported to Sentry, the drill exits with 1).
    """
