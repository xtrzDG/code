"""Shared rendering of localized message templates and their labels.

Templates are `LocalizedText` with `str.format` fields. The template
language is chosen once (requested tag, base language, English) and every
label, date and inserted value is rendered in that same language.
"""

from collections.abc import Mapping

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.constants.bookings import LeadType
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.operations import BookingStaffNotificationInput
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.localization.strings import (
    FormattedPhoneNumber,
    LocalizedTextValue,
)
from app.utilities.scheduling.localized_formatting import (
    choose_template_language,
    format_full_date,
    isolate,
)
from app.utilities.scheduling.zoned_time import parse_local_date

MISSING_VALUE: str = "—"


def localized(**values: str) -> LocalizedText:
    """Template from keyword arguments named after language tags (en=..., ka=...)."""

    return LocalizedText(
        values={
            LanguageTag(tag.replace("_", "-")): LocalizedTextValue(value)
            for tag, value in values.items()
        }
    )


def render(
    resolver: LocalizedTextResolverContract,
    template: LocalizedText,
    language: LanguageTag,
    fields: Mapping[str, str],
) -> str:
    """Resolve the template in `language` and fill it with isolated values."""

    text: str = str(resolver.resolve(template, language))
    return text.format(
        **{name: isolate(value, language) for name, value in fields.items()}
    )


def resolve_label(
    resolver: LocalizedTextResolverContract,
    labels: Mapping[str, LocalizedText],
    key: str,
    language: LanguageTag,
) -> str:
    label: LocalizedText | None = labels.get(key)
    if label is None:
        return key

    return str(resolver.resolve(label, language))


def describe_date(value: LocalDate, language: LanguageTag) -> str:
    """Full local date with weekday, e.g. "Monday, October 5, 2026"."""

    return format_full_date(parse_local_date(value), language)


def describe_booking_period(booking: BookingView, language: LanguageTag) -> str:
    """ "Monday, October 5, 2026, 19:00–21:00" or a stay across dates."""

    start_date: str = describe_date(booking.date, language)
    start_time: str = "" if booking.time is None else f", {booking.time}"
    end_time: str = "" if booking.end_time is None else str(booking.end_time)
    if booking.end_date == booking.date:
        return f"{start_date}{start_time}–{end_time}"

    end_date: str = describe_date(booking.end_date, language)
    end_suffix: str = "" if end_time == "" else f", {end_time}"
    return f"{start_date}{start_time} – {end_date}{end_suffix}"


def describe_phone(
    display_phone: FormattedPhoneNumber | None,
    e164_phone: E164PhoneNumber | None,
) -> str:
    if display_phone is not None:
        return str(display_phone)

    if e164_phone is not None:
        return str(e164_phone)

    return MISSING_VALUE


def text_or_missing(value: object | None) -> str:
    if value is None:
        return MISSING_VALUE

    return str(value)


CHANNEL_LABELS: Mapping[str, LocalizedText] = {
    ChannelKind.PHONE: localized(en="Phone call", ru="Звонок", ka="ზარი"),
    ChannelKind.WHATSAPP: localized(en="WhatsApp", ru="WhatsApp", ka="WhatsApp"),
    ChannelKind.INSTAGRAM: localized(en="Instagram", ru="Instagram", ka="Instagram"),
    ChannelKind.MESSENGER: localized(en="Messenger", ru="Messenger", ka="Messenger"),
    ChannelKind.TELEGRAM: localized(en="Telegram", ru="Telegram", ka="Telegram"),
    ChannelKind.WEB_CHAT: localized(
        en="Website chat", ru="Чат на сайте", ka="ჩატი საიტზე"
    ),
    ChannelKind.VIBER: localized(en="Viber", ru="Viber", ka="Viber"),
    ChannelKind.OWNER_TEST: localized(
        en="Owner test", ru="Тест владельца", ka="მფლობელის ტესტი"
    ),
}

HANDOFF_REASON_LABELS: Mapping[str, LocalizedText] = {
    HandoffReason.CUSTOMER_REQUEST: localized(
        en="Customer asked for a person",
        ru="Клиент просит человека",
        ka="კლიენტი ითხოვს ადამიანს",
    ),
    HandoffReason.COMPLAINT: localized(en="Complaint", ru="Жалоба", ka="საჩივარი"),
    HandoffReason.VIP_GUEST: localized(
        en="VIP guest", ru="VIP-гость", ka="VIP სტუმარი"
    ),
    HandoffReason.NON_STANDARD_REQUEST: localized(
        en="Non-standard request",
        ru="Нестандартный запрос",
        ka="არასტანდარტული მოთხოვნა",
    ),
    HandoffReason.UNKNOWN_ANSWER: localized(
        en="No answer in the knowledge base",
        ru="Нет ответа в базе знаний",
        ka="ცოდნის ბაზაში პასუხი არ არის",
    ),
    HandoffReason.EMERGENCY: localized(
        en="Emergency", ru="Экстренная ситуация", ka="საგანგებო სიტუაცია"
    ),
    HandoffReason.SENSITIVE_TOPIC: localized(
        en="Sensitive topic", ru="Деликатная тема", ka="დელიკატური თემა"
    ),
    HandoffReason.PROFILE_RULE: localized(
        en="Owner's handoff rule",
        ru="Правило владельца",
        ka="მფლობელის წესი",
    ),
    HandoffReason.UNVERIFIED_NUMBERS: localized(
        en="Unverified prices or numbers",
        ru="Непроверенные цены или цифры",
        ka="გადაუმოწმებელი ფასები ან ციფრები",
    ),
}

HANDOFF_URGENCY_LABELS: Mapping[str, LocalizedText] = {
    HandoffUrgency.LOW: localized(en="Low", ru="Низкая", ka="დაბალი"),
    HandoffUrgency.NORMAL: localized(en="Normal", ru="Обычная", ka="ჩვეულებრივი"),
    HandoffUrgency.HIGH: localized(en="High", ru="Высокая", ka="მაღალი"),
    HandoffUrgency.CRITICAL: localized(en="Critical", ru="Критическая", ka="კრიტიკული"),
}

LEAD_TYPE_LABELS: Mapping[str, LocalizedText] = {
    LeadType.BANQUET: localized(en="Banquet", ru="Банкет", ka="ბანკეტი"),
    LeadType.GROUP: localized(en="Group", ru="Группа", ka="ჯგუფი"),
    LeadType.CORPORATE: localized(
        en="Corporate event", ru="Корпоратив", ka="კორპორატივი"
    ),
    LeadType.ORDER: localized(en="Order", ru="Заказ", ka="შეკვეთა"),
    LeadType.VIEWING: localized(en="Viewing", ru="Просмотр", ka="დათვალიერება"),
    LeadType.OTHER: localized(en="Other", ru="Другое", ka="სხვა"),
}

CANCELLATION_POLICY: LocalizedText = localized(
    en="Cancellation policy: {policy}",
    ru="Правила отмены: {policy}",
    ka="გაუქმების წესები: {policy}",
    tr="İptal koşulları: {policy}",
    he="מדיניות ביטול: {policy}",
    ar="سياسة الإلغاء: {policy}",
    hy="Չեղարկման կանոններ՝ {policy}",
    uk="Умови скасування: {policy}",
    de="Stornobedingungen: {policy}",
    fr="Conditions d'annulation : {policy}",
    es="Política de cancelación: {policy}",
    it="Condizioni di cancellazione: {policy}",
)

BOOKING_STAFF_DETAILS: LocalizedText = localized(
    en="{period} · {resource}\nName: {name}\nPhone: {phone}\nGuests: {party}\n"
    "Channel: {channel}",
    ru="{period} · {resource}\nИмя: {name}\nТелефон: {phone}\nГостей: {party}\n"
    "Канал: {channel}",
    ka="{period} · {resource}\nსახელი: {name}\nტელეფონი: {phone}\n"
    "სტუმრები: {party}\nარხი: {channel}",
)

NOTES_LINE: LocalizedText = localized(
    en="Notes: {notes}",
    ru="Пожелания: {notes}",
    ka="შენიშვნა: {notes}",
)


def render_booking_staff_notification(
    resolver: LocalizedTextResolverContract,
    title: LocalizedText,
    input_data: BookingStaffNotificationInput,
) -> str:
    """Title line plus booking details for staff, in the staff language."""

    language: LanguageTag = choose_template_language(title, input_data.language)
    booking: BookingView = input_data.booking
    lines: list[str] = [
        render(resolver, title, language, {"business": str(input_data.business_name)}),
        render(
            resolver,
            BOOKING_STAFF_DETAILS,
            language,
            {
                "period": describe_booking_period(booking, language),
                "resource": str(booking.resource_name),
                "name": text_or_missing(booking.contact_name),
                "phone": describe_phone(
                    input_data.contact_phone_display,
                    booking.contact_phone_number,
                ),
                "party": str(int(booking.party_size)),
                "channel": resolve_label(
                    resolver, CHANNEL_LABELS, booking.source_channel, language
                ),
            },
        ),
    ]
    if booking.notes is not None:
        lines.append(
            render(resolver, NOTES_LINE, language, {"notes": str(booking.notes)})
        )

    return "\n".join(lines)
