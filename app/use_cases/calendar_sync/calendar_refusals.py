"""Refusals of calendar changes, with a stable code the cabinet translates."""

from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage


def calendar_refusal(code: str, message: str) -> ValidationFailedError:
    """A 422 whose reason code names what to fix ("feed_limit", "access_denied")."""

    return ValidationFailedError(
        message,
        reasons=[
            ErrorReason(code=ErrorReasonCode(code), message=ErrorReasonMessage(message))
        ],
    )
