from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.operations.message_texts import BookingMessageInput
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

CANCELLATION_CONFIRMATION: LocalizedText = localized(
    en="Your booking at {business} on {date}, {time} is cancelled.",
    ru="Ваша бронь в «{business}» на {date}, {time} отменена.",
    ka="თქვენი ჯავშანი {business}-ში ({date}, {time}) გაუქმებულია.",
    tr="{business} için {date}, {time} tarihli rezervasyonunuz iptal edildi.",
    he="ההזמנה שלך ב-{business} ל-{date}, {time} בוטלה.",
    ar="تم إلغاء حجزك في {business} بتاريخ {date}، {time}.",
    hy="Ձեր ամրագրումը {business}-ում ({date}, {time}) չեղարկված է։",
    uk="Ваше бронювання в «{business}» на {date}, {time} скасовано.",
    de="Ihre Reservierung bei {business} am {date}, {time} wurde storniert.",
    fr="Votre réservation chez {business} du {date}, {time} est annulée.",
    es="Su reserva en {business} del {date}, {time} ha sido cancelada.",
    it="La sua prenotazione presso {business} per {date}, {time} è stata annullata.",
)


class CancellationConfirmationTransformer(
    TransformerContract[BookingMessageInput, MessageText]
):
    """
    Cancellation confirmation in the customer's language, followed by the
    owner's cancellation policy from the profile when there is one.
    """

    def __init__(self, text_resolver: LocalizedTextResolverContract) -> None:
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def transform(self, input_data: BookingMessageInput) -> MessageText:
        language: LanguageTag = choose_template_language(
            CANCELLATION_CONFIRMATION, input_data.language
        )
        booking = input_data.booking
        lines: list[str] = [
            render(
                self._text_resolver,
                CANCELLATION_CONFIRMATION,
                language,
                {
                    "business": str(input_data.business_name),
                    "date": describe_date(booking.date, language),
                    "time": text_or_missing(booking.time),
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
