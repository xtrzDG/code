"""The answer of a booking change: the booking and its confirmation text."""

from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.bookings import BookingUnit
from app.schemas.dto.bookings import BookingResult, BookingView
from app.schemas.dto.operations.message_texts import BookingMessageInput
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.bookings.booking_support import SchedulingInputs


def confirmed_change(
    confirmation_transformer: TransformerContract[BookingMessageInput, MessageText],
    inputs: SchedulingInputs,
    view: BookingView,
    booking_unit: BookingUnit,
    language: LanguageTag,
) -> BookingResult:
    """
    The changed booking with its confirmation in the customer's language,
    quoting the profile's cancellation policy.
    """

    return BookingResult(
        booking=view,
        confirmation_text=confirmation_transformer.transform(
            BookingMessageInput(
                business_name=inputs.business.name,
                booking=view,
                booking_unit=booking_unit,
                language=language,
                cancellation_policy=(
                    None if inputs.rules is None else inputs.rules.cancellation_policy
                ),
            )
        ),
    )
