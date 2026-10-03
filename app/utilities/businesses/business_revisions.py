"""The refusal of a business change made from an older revision."""

from app.schemas.constants.businesses import BusinessSettingsRefusalCode
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import ConflictError
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
            ErrorReason(
                code=ErrorReasonCode(BusinessSettingsRefusalCode.STALE_REVISION.value),
                message=ErrorReasonMessage(STALE_REVISION_MESSAGE),
                details=(
                    []
                    if current_revision is None
                    else [ErrorReasonDetail(str(int(current_revision)))]
                ),
            )
        ],
    )
