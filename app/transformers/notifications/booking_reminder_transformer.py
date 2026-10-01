from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.bookings import BookingUnit
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.operations import BookingMessageInput
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.notifications.message_rendering import (
    CANCELLATION_POLICY,
    describe_date,
    localized,
    render,
    text_or_missing,
)
from app.utilities.scheduling.localized_formatting import choose_template_language

TIME_SLOT_REMINDER: LocalizedText = localized(
    en=(
        "Reminder: your booking at {business} is on {date} at {time}. "
        "Name: {name}. Guests: {party}. "
        "To cancel or change it, just reply to this message."
    ),
    ru=(
        "Напоминание: ваша бронь в «{business}» — {date}, {time}. "
        "Имя: {name}. Гостей: {party}. "
        "Чтобы отменить или перенести бронь, просто ответьте на это сообщение."
    ),
    ka=(
        "შეხსენება: თქვენი ჯავშანი {business}-ში — {date}, {time}. "
        "სახელი: {name}. სტუმრები: {party}. "
        "გასაუქმებლად ან გადასატანად უბრალოდ უპასუხეთ ამ შეტყობინებას."
    ),
)

STAY_REMINDER: LocalizedText = localized(
    en=(
        "Reminder: your stay at {business} starts on {date}, check-in from "
        "{time}. Name: {name}. Guests: {party}. "
        "To cancel or change it, just reply to this message."
    ),
    ru=(
        "Напоминание: ваше проживание в «{business}» начинается {date}, "
        "заезд с {time}. Имя: {name}. Гостей: {party}. "
        "Чтобы отменить или перенести бронь, просто ответьте на это сообщение."
    ),
    ka=(
        "შეხსენება: თქვენი ჯავშანი {business}-ში იწყება {date}, შესვლა "
        "{time}-დან. სახელი: {name}. სტუმრები: {party}. "
        "გასაუქმებლად ან გადასატანად უბრალოდ უპასუხეთ ამ შეტყობინებას."
    ),
)


class BookingReminderTransformer(TransformerContract[BookingMessageInput, MessageText]):
    """
    Reminder of an upcoming booking in the customer's language (concept:
    "с подтверждением и напоминанием"): business, date and time in the
    business time zone, name and party size, how to cancel or move it (reply
    in the same chat, where the assistant can cancel and reschedule), then
    the owner's cancellation policy when the profile has one.

    Texts exist in English, Russian and Georgian; other languages fall back
    to their base language, then English.
    """

    def __init__(self, text_resolver: LocalizedTextResolverContract) -> None:
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def transform(self, input_data: BookingMessageInput) -> MessageText:
        template: LocalizedText = (
            STAY_REMINDER
            if input_data.booking_unit is BookingUnit.NIGHT
            else TIME_SLOT_REMINDER
        )
        language: LanguageTag = choose_template_language(template, input_data.language)
        booking = input_data.booking
        lines: list[str] = [
            render(
                self._text_resolver,
                template,
                language,
                {
                    "business": str(input_data.business_name),
                    "date": describe_date(booking.date, language),
                    "time": text_or_missing(booking.time),
                    "name": text_or_missing(booking.contact_name),
                    "party": str(int(booking.party_size)),
                },
            )
        ]
        if input_data.cancellation_policy is not None:
            lines.append(
                render(
                    self._text_resolver,
                    CANCELLATION_POLICY,
                    language,
                    {"policy": str(input_data.cancellation_policy)},
                )
            )

        return MessageText("\n".join(lines))
