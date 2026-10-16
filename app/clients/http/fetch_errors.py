"""Building the fetcher's errors with their machine-readable details."""

from app.schemas.constants.web_fetching import WebFetchProblem
from app.schemas.exceptions.web_fetch_errors import WebFetchError
from app.schemas.typings.platform.constrained_strings import ErrorReasonDetail

MAX_DETAIL_VALUE_LENGTH: int = 80


def fetch_error(
    problem: WebFetchProblem,
    message: str,
    value: str | None = None,
) -> WebFetchError:
    """
    The error of `problem`; its detail is the problem code, followed by
    ":<value>" when a value qualifies it ("http_status:404").
    """

    detail: str = problem.value
    if value is not None:
        cleaned: str = "".join(
            character
            for character in value[:MAX_DETAIL_VALUE_LENGTH]
            if character.isascii() and (character.isalnum() or character in "_.+-/")
        )
        if cleaned != "":
            detail = f"{detail}:{cleaned}"

    return WebFetchError(message, problem, ErrorReasonDetail(detail))
