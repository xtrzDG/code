"""The refusals of platform support's access to a client's cabinet."""

from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage

SUPPORT_ACCESS_REQUIRED_CODE: ErrorReasonCode = ErrorReasonCode(
    "support_access_required"
)
SUPPORT_READ_ONLY_CODE: ErrorReasonCode = ErrorReasonCode("support_read_only")
SUPPORT_ACCESS_REQUIRED_MESSAGE: str = (
    "Open this client's cabinet from the admin pages with a reason first; "
    "access lasts an hour."
)
SUPPORT_READ_ONLY_MESSAGE: str = (
    "Platform support may only look here: the owner has not allowed changes."
)


def support_access_required() -> AccessDeniedError:
    """HTTP 403, reason `support_access_required`: no open look right now."""

    return AccessDeniedError(
        SUPPORT_ACCESS_REQUIRED_MESSAGE,
        reasons=[
            ErrorReason(
                code=SUPPORT_ACCESS_REQUIRED_CODE,
                message=ErrorReasonMessage(SUPPORT_ACCESS_REQUIRED_MESSAGE),
            )
        ],
    )


def support_read_only() -> AccessDeniedError:
    """HTTP 403, reason `support_read_only`: a change without consent."""

    return AccessDeniedError(
        SUPPORT_READ_ONLY_MESSAGE,
        reasons=[
            ErrorReason(
                code=SUPPORT_READ_ONLY_CODE,
                message=ErrorReasonMessage(SUPPORT_READ_ONLY_MESSAGE),
            )
        ],
    )
