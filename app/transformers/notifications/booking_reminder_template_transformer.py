from app.contracts.transformer_contract import TransformerContract
from app.schemas.dto.operations.message_texts import BookingMessageInput
from app.schemas.typings.conversations.strings import MessageText
from app.transformers.notifications.message_rendering import (
    describe_date,
    text_or_missing,
)


class BookingReminderTemplateTransformer(
    TransformerContract[BookingMessageInput, list[MessageText]]
):
    """
    Body parameters of the approved WhatsApp booking reminder template
    (concept section 6: reminders outside the 24-hour window are templates),
    in this order: business name, the local date written out in the
    customer's language, the local time, the customer's name. Meta keeps
    the wording of the template itself, one translation per language.
    """

    def transform(self, input_data: BookingMessageInput) -> list[MessageText]:
        booking = input_data.booking
        return [
            MessageText(str(input_data.business_name)),
            MessageText(describe_date(booking.date, input_data.language)),
            MessageText(text_or_missing(booking.time)),
            MessageText(text_or_missing(booking.contact_name)),
        ]
