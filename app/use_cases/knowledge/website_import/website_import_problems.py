"""How a website that cannot be read is reported: problem codes and 422 reasons."""

from app.schemas.constants.web_fetching import (
    REFUSED_FETCH_PROBLEMS,
    UNUSABLE_FETCH_PROBLEMS,
)
from app.schemas.constants.website_import import WebsiteImportProblem
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.exceptions.web_fetch_errors import WebFetchError
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage

IMPORT_RUNNING_CODE: ErrorReasonCode = ErrorReasonCode("website_import_running")


def problem_of(error: WebFetchError) -> WebsiteImportProblem:
    """Refused: invalid; fetched but unusable: unreadable; else unreachable."""

    if error.problem in REFUSED_FETCH_PROBLEMS:
        return WebsiteImportProblem.INVALID

    if error.problem in UNUSABLE_FETCH_PROBLEMS:
        return WebsiteImportProblem.UNREADABLE

    return WebsiteImportProblem.UNREACHABLE


def invalid_address(error: WebFetchError) -> ValidationFailedError:
    """The 422 of an address refused before the import starts."""

    return ValidationFailedError(
        f"The website cannot be read: {error}",
        reasons=[
            ErrorReason(
                code=ErrorReasonCode(problem_of(error).value),
                message=ErrorReasonMessage(str(error)),
                details=[error.detail],
            )
        ],
    )


def import_already_running() -> ConflictError:
    """The 409 while the business's last import is still reading its site."""

    message: str = "The website is already being read; wait until that import finishes."
    return ConflictError(
        message,
        reasons=[
            ErrorReason(code=IMPORT_RUNNING_CODE, message=ErrorReasonMessage(message))
        ],
    )
