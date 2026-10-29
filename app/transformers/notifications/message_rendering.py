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
from app.schemas.dto.operations.message_texts import BookingStaffNotificationInput
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.localization.strings import (
    FormattedPhoneNumber,
    LocalizedTextValue,
)
from app.utilities.localization.owner_texts import owner_text
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
    ChannelKind.PHONE: owner_text("notifications.staff_message.channel_labels.phone"),
    ChannelKind.WHATSAPP: owner_text(
        "notifications.staff_message.channel_labels.whatsapp"
    ),
    ChannelKind.INSTAGRAM: owner_text(
        "notifications.staff_message.channel_labels.instagram"
    ),
    ChannelKind.MESSENGER: owner_text(
        "notifications.staff_message.channel_labels.messenger"
    ),
    ChannelKind.TELEGRAM: owner_text(
        "notifications.staff_message.channel_labels.telegram"
    ),
    ChannelKind.WEB_CHAT: owner_text(
        "notifications.staff_message.channel_labels.web_chat"
    ),
    ChannelKind.VIBER: owner_text("notifications.staff_message.channel_labels.viber"),
    ChannelKind.OWNER_TEST: owner_text(
        "notifications.staff_message.channel_labels.owner_test"
    ),
}

HANDOFF_REASON_LABELS: Mapping[str, LocalizedText] = {
    HandoffReason.CUSTOMER_REQUEST: owner_text(
        "notifications.staff_message.handoff_reason_labels.customer_request"
    ),
    HandoffReason.COMPLAINT: owner_text(
        "notifications.staff_message.handoff_reason_labels.complaint"
    ),
    HandoffReason.VIP_GUEST: owner_text(
        "notifications.staff_message.handoff_reason_labels.vip_guest"
    ),
    HandoffReason.NON_STANDARD_REQUEST: owner_text(
        "notifications.staff_message.handoff_reason_labels.non_standard_request"
    ),
    HandoffReason.UNKNOWN_ANSWER: owner_text(
        "notifications.staff_message.handoff_reason_labels.unknown_answer"
    ),
    HandoffReason.EMERGENCY: owner_text(
        "notifications.staff_message.handoff_reason_labels.emergency"
    ),
    HandoffReason.SENSITIVE_TOPIC: owner_text(
        "notifications.staff_message.handoff_reason_labels.sensitive_topic"
    ),
    HandoffReason.PROFILE_RULE: owner_text(
        "notifications.staff_message.handoff_reason_labels.profile_rule"
    ),
    HandoffReason.UNVERIFIED_NUMBERS: owner_text(
        "notifications.staff_message.handoff_reason_labels.unverified_numbers"
    ),
}

HANDOFF_URGENCY_LABELS: Mapping[str, LocalizedText] = {
    HandoffUrgency.LOW: owner_text(
        "notifications.staff_message.handoff_urgency_labels.low"
    ),
    HandoffUrgency.NORMAL: owner_text(
        "notifications.staff_message.handoff_urgency_labels.normal"
    ),
    HandoffUrgency.HIGH: owner_text(
        "notifications.staff_message.handoff_urgency_labels.high"
    ),
    HandoffUrgency.CRITICAL: owner_text(
        "notifications.staff_message.handoff_urgency_labels.critical"
    ),
}

LEAD_TYPE_LABELS: Mapping[str, LocalizedText] = {
    LeadType.BANQUET: owner_text(
        "notifications.staff_message.lead_type_labels.banquet"
    ),
    LeadType.GROUP: owner_text("notifications.staff_message.lead_type_labels.group"),
    LeadType.CORPORATE: owner_text(
        "notifications.staff_message.lead_type_labels.corporate"
    ),
    LeadType.ORDER: owner_text("notifications.staff_message.lead_type_labels.order"),
    LeadType.VIEWING: owner_text(
        "notifications.staff_message.lead_type_labels.viewing"
    ),
    LeadType.OTHER: owner_text("notifications.staff_message.lead_type_labels.other"),
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

BOOKING_STAFF_DETAILS: LocalizedText = owner_text(
    "notifications.staff_message.booking_staff_details"
)

NOTES_LINE: LocalizedText = owner_text("notifications.staff_message.notes_line")


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
