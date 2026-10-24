"""
Why a number could not be taken. Each refusal carries one stable reason
code (`number_taken`, `price_changed`) so the cabinet words it in the
owner's language instead of showing the English message.
"""

from collections.abc import Sequence

from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage

NUMBER_TAKEN_REASON: ErrorReasonCode = ErrorReasonCode("number_taken")
PRICE_CHANGED_REASON: ErrorReasonCode = ErrorReasonCode("price_changed")


class PhoneNumberUnavailableError(ConflictError):
    """
    The carrier no longer rents the chosen number (someone took it since the
    search, or it was withdrawn): the owner searches again and picks another.
    Reason `number_taken`.
    """

    def __init__(self, *args: object, reasons: Sequence[ErrorReason] = ()) -> None:
        super().__init__(
            *args,
            reasons=reasons
            or [
                ErrorReason(
                    code=NUMBER_TAKEN_REASON,
                    message=ErrorReasonMessage("Search again and pick another number."),
                )
            ],
        )


class PhoneNumberPriceChangedError(ConflictError):
    """
    The monthly price of the chosen kind of number is not the one the
    cabinet showed (the carrier's price or the exchange rate moved since the
    search): the owner looks at the new price before taking the number.
    Reason `price_changed`.
    """

    def __init__(self, *args: object, reasons: Sequence[ErrorReason] = ()) -> None:
        super().__init__(
            *args,
            reasons=reasons
            or [
                ErrorReason(
                    code=PRICE_CHANGED_REASON,
                    message=ErrorReasonMessage("Search again to see the new price."),
                )
            ],
        )
