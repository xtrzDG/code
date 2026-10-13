"""Refusals of deposit actions, with a stable code the cabinet translates."""

from app.schemas.constants.deposits import DepositRefusalCode
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage


def deposit_refusal(code: DepositRefusalCode, message: str) -> ValidationFailedError:
    """A 422 whose reason code names what to fix (`link_not_https`)."""

    return ValidationFailedError(message, reasons=[_reason(code, message)])


def deposit_conflict(code: DepositRefusalCode, message: str) -> ConflictError:
    """A 409 whose reason code names what changed (`status_changed`)."""

    return ConflictError(message, reasons=[_reason(code, message)])


def _reason(code: DepositRefusalCode, message: str) -> ErrorReason:
    return ErrorReason(
        code=ErrorReasonCode(code.value), message=ErrorReasonMessage(message)
    )
