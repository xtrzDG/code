"""
The refusals of a business change made from an older revision: 409 for a
stale `expected_revision` in the body, 412 for an If-Match header that names
another revision than the stored one.
"""

from app.schemas.constants.businesses import BusinessSettingsRefusalCode
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import (
    ConflictError,
    PreconditionFailedError,
)
from app.schemas.typings.businesses.constrained_integers import BusinessRevision
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage

STALE_REVISION_MESSAGE: str = (
    "These settings were saved by someone else after you opened them. Reload "
    "them and make your change again."
)
PRECONDITION_FAILED_MESSAGE: str = (
    "These settings were saved after the version named in If-Match. Read them "
    "again (the answer carries the current ETag) and make your change again."
)


def build_stale_revision_error(
    current_revision: BusinessRevision | None,
) -> ConflictError:
    """
    The refusal of a change made from an older revision; its details carry
    the current revision when it is known.
    """

    return ConflictError(
        STALE_REVISION_MESSAGE,
        reasons=[
            revision_reason(
                BusinessSettingsRefusalCode.STALE_REVISION,
                STALE_REVISION_MESSAGE,
                current_revision,
            )
        ],
    )


def build_precondition_failed_error(
    current_revision: BusinessRevision | None,
) -> PreconditionFailedError:
    """
    The refusal of a change whose If-Match header does not name the stored
    revision; its details carry the current revision when it is known.
    """

    return PreconditionFailedError(
        PRECONDITION_FAILED_MESSAGE,
        reasons=[
            revision_reason(
                BusinessSettingsRefusalCode.PRECONDITION_FAILED,
                PRECONDITION_FAILED_MESSAGE,
                current_revision,
            )
        ],
    )


def revision_reason(
    code: BusinessSettingsRefusalCode,
    message: str,
    current_revision: BusinessRevision | None,
) -> ErrorReason:
    return ErrorReason(
        code=ErrorReasonCode(code.value),
        message=ErrorReasonMessage(message),
        details=(
            []
            if current_revision is None
            else [ErrorReasonDetail(str(int(current_revision)))]
        ),
    )
