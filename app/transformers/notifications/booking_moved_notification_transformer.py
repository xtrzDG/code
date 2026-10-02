from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.operations.message_texts import BookingStaffNotificationInput
from app.schemas.typings.conversations.strings import MessageText
from app.transformers.notifications.message_rendering import (
    localized,
    render_booking_staff_notification,
)

BOOKING_MOVED_TITLE: LocalizedText = localized(
    en="Booking moved to a new time · {business}",
    ru="Бронь перенесена на новое время · {business}",
    ka="ჯავშანი ახალ დროზე გადაიტანეს · {business}",
)


class BookingMovedNotificationTransformer(
    TransformerContract[BookingStaffNotificationInput, MessageText]
):
    """Staff notification that a customer moved a booking (new time shown)."""

    def __init__(self, text_resolver: LocalizedTextResolverContract) -> None:
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def transform(self, input_data: BookingStaffNotificationInput) -> MessageText:
        return MessageText(
            render_booking_staff_notification(
                self._text_resolver, BOOKING_MOVED_TITLE, input_data
            )
        )
