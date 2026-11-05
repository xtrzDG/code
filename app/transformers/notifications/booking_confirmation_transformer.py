from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.bookings import BookingUnit
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.operations.message_texts import BookingMessageInput
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.notifications.message_rendering import (
    describe_date,
    localized,
    render,
    text_or_missing,
)
from app.utilities.scheduling.localized_formatting import choose_template_language

TIME_SLOT_CONFIRMATION: LocalizedText = localized(
    en=(
        "Your booking at {business} is confirmed: {date}, {time}. "
        "Name: {name}. Guests: {party}."
    ),
    ru=(
        "Ваша бронь в «{business}» подтверждена: {date}, {time}. "
        "Имя: {name}. Гостей: {party}."
    ),
    ka=(
        "თქვენი ჯავშანი {business}-ში დადასტურებულია: {date}, {time}. "
        "სახელი: {name}. სტუმრები: {party}."
    ),
    tr=(
        "{business} rezervasyonunuz onaylandı: {date}, {time}. "
        "İsim: {name}. Kişi sayısı: {party}."
    ),
    he=(
        "ההזמנה שלך ב-{business} אושרה: {date}, {time}. "
        "שם: {name}. מספר אורחים: {party}."
    ),
    ar=(
        "تم تأكيد حجزك في {business}: {date}، {time}. "
        "الاسم: {name}. عدد الضيوف: {party}."
    ),
    hy=(
        "Ձեր ամրագրումը {business}-ում հաստատված է՝ {date}, {time}։ "
        "Անուն՝ {name}։ Հյուրերի թիվը՝ {party}։"
    ),
    uk=(
        "Ваше бронювання в «{business}» підтверджено: {date}, {time}. "
        "Ім'я: {name}. Гостей: {party}."
    ),
    de=(
        "Ihre Reservierung bei {business} ist bestätigt: {date}, {time}. "
        "Name: {name}. Personen: {party}."
    ),
    fr=(
        "Votre réservation chez {business} est confirmée : {date}, {time}. "
        "Nom : {name}. Personnes : {party}."
    ),
    es=(
        "Su reserva en {business} está confirmada: {date}, {time}. "
        "Nombre: {name}. Personas: {party}."
    ),
    it=(
        "La sua prenotazione presso {business} è confermata: {date}, {time}. "
        "Nome: {name}. Persone: {party}."
    ),
)

STAY_CONFIRMATION: LocalizedText = localized(
    en=(
        "Your stay at {business} is confirmed: check-in {date} from {time}, "
        "check-out {end_date} until {end_time}. Name: {name}. Guests: {party}."
    ),
    ru=(
        "Ваше проживание в «{business}» подтверждено: заезд {date} с {time}, "
        "выезд {end_date} до {end_time}. Имя: {name}. Гостей: {party}."
    ),
    ka=(
        "თქვენი ჯავშანი {business}-ში დადასტურებულია: შესვლა {date}, "
        "{time}-დან, გასვლა {end_date}, {end_time}-მდე. სახელი: {name}. "
        "სტუმრები: {party}."
    ),
    tr=(
        "{business} konaklamanız onaylandı: giriş {date}, saat {time} itibarıyla; "
        "çıkış {end_date}, en geç saat {end_time}. İsim: {name}. "
        "Kişi sayısı: {party}."
    ),
    he=(
        "השהייה שלך ב-{business} אושרה: צ'ק-אין {date} החל מ-{time}, "
        "צ'ק-אאוט {end_date} עד {end_time}. שם: {name}. מספר אורחים: {party}."
    ),
    ar=(
        "تم تأكيد إقامتك في {business}: تسجيل الوصول {date} من الساعة {time}، "
        "والمغادرة {end_date} حتى الساعة {end_time}. الاسم: {name}. "
        "عدد الضيوف: {party}."
    ),
    hy=(
        "Ձեր կացությունը {business}-ում հաստատված է՝ մուտք {date}, {time}-ից, "
        "ելք {end_date}, մինչև {end_time}։ Անուն՝ {name}։ Հյուրերի թիվը՝ {party}։"
    ),
    uk=(
        "Ваше проживання в «{business}» підтверджено: заїзд {date} з {time}, "
        "виїзд {end_date} до {end_time}. Ім'я: {name}. Гостей: {party}."
    ),
    de=(
        "Ihr Aufenthalt bei {business} ist bestätigt: Anreise {date} ab {time}, "
        "Abreise {end_date} bis {end_time}. Name: {name}. Personen: {party}."
    ),
    fr=(
        "Votre séjour chez {business} est confirmé : arrivée le {date} à partir "
        "de {time}, départ le {end_date} avant {end_time}. Nom : {name}. "
        "Personnes : {party}."
    ),
    es=(
        "Su estancia en {business} está confirmada: entrada el {date} desde las "
        "{time}, salida el {end_date} hasta las {end_time}. Nombre: {name}. "
        "Personas: {party}."
    ),
    it=(
        "Il suo soggiorno presso {business} è confermato: arrivo {date} dalle "
        "{time}, partenza {end_date} entro le {end_time}. Nome: {name}. "
        "Persone: {party}."
    ),
)


class BookingConfirmationTransformer(
    TransformerContract[BookingMessageInput, MessageText]
):
    """
    Confirmation of a new booking in the customer's language: it repeats the
    date, time, name and party size in the business time zone (concept:
    the assistant repeats date, time and name). Languages without a text
    fall back to the base language, then English.
    """

    def __init__(self, text_resolver: LocalizedTextResolverContract) -> None:
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def transform(self, input_data: BookingMessageInput) -> MessageText:
        template: LocalizedText = (
            STAY_CONFIRMATION
            if input_data.booking_unit is BookingUnit.NIGHT
            else TIME_SLOT_CONFIRMATION
        )
        language: LanguageTag = choose_template_language(template, input_data.language)
        booking = input_data.booking
        return MessageText(
            render(
                self._text_resolver,
                template,
                language,
                {
                    "business": str(input_data.business_name),
                    "date": describe_date(booking.date, language),
                    "time": text_or_missing(booking.time),
                    "end_date": describe_date(booking.end_date, language),
                    "end_time": text_or_missing(booking.end_time),
                    "name": text_or_missing(booking.contact_name),
                    "party": str(int(booking.party_size)),
                },
            )
        )
