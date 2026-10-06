from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.operations.message_texts import BookingStaffNotificationInput
from app.schemas.typings.conversations.strings import MessageText
from app.transformers.notifications.message_rendering import (
    render_booking_staff_notification,
)
from app.utilities.localization.owner_texts import owner_text

BOOKING_CANCELLED_TITLE: LocalizedText = owner_text(
    "notifications.booking_cancelled.booking_cancelled_title"
)


class BookingCancelledNotificationTransformer(
    TransformerContract[BookingStaffNotificationInput, MessageText]
):
    """Staff notification that a customer cancelled a booking."""

    def __init__(self, text_resolver: LocalizedTextResolverContract) -> None:
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def transform(self, input_data: BookingStaffNotificationInput) -> MessageText:
        return MessageText(
            render_booking_staff_notification(
                self._text_resolver, BOOKING_CANCELLED_TITLE, input_data
            )
        )
