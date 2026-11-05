"""Bodies of failed API requests and their machine-readable reasons."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.errors import ApiErrorCode
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorMessageText, ErrorReasonMessage


class ErrorReason(ImmutableDTO):
    """
    One reason a request was refused, in the `reasons` list of an error
    response: a stable `code` clients branch on, an English `message`, and
    `details` that qualify it (gap kinds, statuses, missing settings).

    Example: {"code": "profile_gaps", "message": "Complete the profile ...",
    "details": ["no_opening_hours"]}
    """

    code: ErrorReasonCode
    message: ErrorReasonMessage
    details: list[ErrorReasonDetail] = Field(default_factory=list[ErrorReasonDetail])


class ErrorBody(ImmutableDTO):
    """
    Body of every failed request: the broad `error` code, an English
    `message`, and, when the server knows them, `reasons` with stable codes
    (absent otherwise, so older clients keep working).
    """

    error: ApiErrorCode
    message: ErrorMessageText
    reasons: list[ErrorReason] | None = None
