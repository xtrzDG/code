from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
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

RESCHEDULE_CONFIRMATION: LocalizedText = localized(
    en=(
        "Your booking at {business} has been moved to {date}, {time}. "
        "Name: {name}. Guests: {party}."
    ),
    ru=(
        "Ваша бронь в «{business}» перенесена на {date}, {time}. "
        "Имя: {name}. Гостей: {party}."
    ),
    ka=(
        "თქვენი ჯავშანი {business}-ში გადატანილია: {date}, {time}. "
        "სახელი: {name}. სტუმრები: {party}."
    ),
    tr=(
        "{business} rezervasyonunuz {date}, {time} olarak değiştirildi. "
        "İsim: {name}. Kişi sayısı: {party}."
    ),
    he=(
        "ההזמנה שלך ב-{business} הועברה ל-{date}, {time}. "
        "שם: {name}. מספר אורחים: {party}."
    ),
    ar=(
        "تم نقل حجزك في {business} إلى {date}، {time}. "
        "الاسم: {name}. عدد الضيوف: {party}."
    ),
    hy=(
        "Ձեր ամրագրումը {business}-ում տեղափոխվել է՝ {date}, {time}։ "
        "Անուն՝ {name}։ Հյուրերի թիվը՝ {party}։"
    ),
    uk=(
        "Ваше бронювання в «{business}» перенесено на {date}, {time}. "
        "Ім'я: {name}. Гостей: {party}."
    ),
    de=(
        "Ihre Reservierung bei {business} wurde verschoben auf {date}, {time}. "
        "Name: {name}. Personen: {party}."
    ),
    fr=(
        "Votre réservation chez {business} a été déplacée au {date}, {time}. "
        "Nom : {name}. Personnes : {party}."
    ),
    es=(
        "Su reserva en {business} se ha cambiado al {date}, {time}. "
        "Nombre: {name}. Personas: {party}."
    ),
    it=(
        "La sua prenotazione presso {business} è stata spostata a {date}, {time}. "
        "Nome: {name}. Persone: {party}."
    ),
)


class RescheduleConfirmationTransformer(
    TransformerContract[BookingMessageInput, MessageText]
):
    """
    New date and time of a moved booking in the customer's language, with
    the owner's cancellation policy when the profile has one.
    """

    def __init__(self, text_resolver: LocalizedTextResolverContract) -> None:
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def transform(self, input_data: BookingMessageInput) -> MessageText:
        language: LanguageTag = choose_template_language(
            RESCHEDULE_CONFIRMATION, input_data.language
        )
        booking = input_data.booking
        lines: list[str] = [
            render(
                self._text_resolver,
                RESCHEDULE_CONFIRMATION,
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
