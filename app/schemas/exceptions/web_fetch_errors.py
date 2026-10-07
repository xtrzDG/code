"""Errors of the safe web fetcher (server-side requests to outside addresses)."""

from app.schemas.constants.web_fetching import WebFetchProblem
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_strings import ErrorReasonDetail


class WebFetchError(ValidationFailedError):
    """
    An address the platform was asked to read was refused, could not be
    fetched or served something unusable. `problem` says which;
    `detail` is the machine-readable specifics ("not_public",
    "http_status:404", "media_type:application/zip"). Callers translate it
    into their own refusal reasons; uncaught it is a 422.
    """

    def __init__(
        self,
        message: str,
        problem: WebFetchProblem,
        detail: ErrorReasonDetail,
    ) -> None:
        super().__init__(message)
        self.problem: WebFetchProblem = problem
        self.detail: ErrorReasonDetail = detail
