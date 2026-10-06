"""The 409 refusals of a request whose idempotency key is taken."""

from app.schemas.constants.idempotency import IdempotencyRefusalCode
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage

KEY_REUSED_MESSAGE: str = (
    "This Idempotency-Key was already used for a different request. Send a "
    "new key for a new action, and the same request again for a retry."
)
IN_PROGRESS_MESSAGE: str = (
    "A request with this Idempotency-Key is still running. Wait for it, then "
    "retry with the same key to get its answer."
)


def build_refusal(code: IdempotencyRefusalCode) -> ConflictError:
    """ConflictError (409) with the reason `code` and its explanation."""

    message: str = (
        KEY_REUSED_MESSAGE
        if code is IdempotencyRefusalCode.KEY_REUSED
        else IN_PROGRESS_MESSAGE
    )
    return ConflictError(
        message,
        reasons=[
            ErrorReason(
                code=ErrorReasonCode(code.value),
                message=ErrorReasonMessage(message),
            )
        ],
    )
