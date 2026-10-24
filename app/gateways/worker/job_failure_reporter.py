import logging

from app.contracts.observability import ErrorReportingFacilitatorContract
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobErrorText

LOGGER: logging.Logger = logging.getLogger(__name__)
MAX_ERROR_TEXT_LENGTH: int = 500


class JobFailureReporter:
    """
    Where job failures go: expected application errors (a provider is down,
    a record is gone) are logged as warnings; unexpected ones go to the
    error reporter (Sentry) as well.
    """

    def __init__(self, error_reporter: ErrorReportingFacilitatorContract) -> None:
        self._error_reporter: ErrorReportingFacilitatorContract = error_reporter

    def report(self, job_name: JobName, error: Exception) -> None:
        if isinstance(error, ApplicationError):
            LOGGER.warning("Job %s failed: %s", job_name, error)
            return

        LOGGER.error("Job %s failed: %s", job_name, describe_error(error))
        self._error_reporter.capture_exception(error)


def describe_error(error: Exception) -> JobErrorText:
    """The error as stored on a job: its type and message, shortened."""

    text: str = f"{type(error).__name__}: {error}"
    return JobErrorText(text[:MAX_ERROR_TEXT_LENGTH])
