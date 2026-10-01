from datetime import date

import pytest
from babel.dates import format_date

from app.schemas.constants.bookings import (
    BookingStatus,
    BookingUnit,
    LeadStatus,
    LeadType,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.dto.bookings import BookingView, LeadView
from app.schemas.dto.operations import (
    BookingMessageInput,
    BookingStaffNotificationInput,
    CalendarEventTextInput,
    HandoffCustomerMessageInput,
    HandoffStaffNotificationInput,
    LeadStaffNotificationInput,
)
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId, ResourceId
from app.schemas.typings.bookings.strings import BookingNote, LeadDetails, ResourceName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.localization.strings import FormattedPhoneNumber
from app.schemas.typings.profiles.strings import CancellationPolicyText
from app.transformers.notifications.booking_cancelled_notification_transformer import (
    BookingCancelledNotificationTransformer,
)
from app.transformers.notifications.booking_confirmation_transformer import (
    TIME_SLOT_CONFIRMATION,
    BookingConfirmationTransformer,
)
from app.transformers.notifications.booking_moved_notification_transformer import (
    BookingMovedNotificationTransformer,
)
from app.transformers.notifications.calendar_event_text_transformer import (
    CalendarEventTextTransformer,
)
from app.transformers.notifications.cancellation_confirmation_transformer import (
    CancellationConfirmationTransformer,
)
from app.transformers.notifications.handoff_customer_message_transformer import (
    HandoffCustomerMessageTransformer,
)
from app.transformers.notifications.handoff_notification_transformer import (
    HandoffNotificationTransformer,
)
from app.transformers.notifications.new_booking_notification_transformer import (
    NewBookingNotificationTransformer,
)
from app.transformers.notifications.new_lead_notification_transformer import (
    NewLeadNotificationTransformer,
)
from app.transformers.notifications.reschedule_confirmation_transformer import (
    RescheduleConfirmationTransformer,
)
from app.utilities.scheduling.localized_formatting import (
    FIRST_STRONG_ISOLATE,
    choose_template_language,
    find_locale,
    is_right_to_left,
)
from tests.operations.fakes import FakeLocalizedTextResolver

CUSTOMER_LANGUAGES: tuple[str, ...] = (
    "en",
    "ru",
    "ka",
    "tr",
    "he",
    "ar",
    "hy",
    "uk",
    "de",
    "fr",
    "es",
    "it",
)
RESOLVER = FakeLocalizedTextResolver()


def booking_view(
    day: str = "2026-10-06",
    time: str = "19:30",
    end_day: str | None = None,
    end_time: str = "21:30",
    notes: str | None = None,
) -> BookingView:
    return BookingView(
        id=BookingId(),
        business_id=BusinessId(),
        resource_id=ResourceId(),
        resource_name=ResourceName("Table 4"),
        contact_id=ContactId(),
        contact_name=ContactName("Nino Kapanadze"),
        contact_phone_number=E164PhoneNumber("+995555123456"),
        date=LocalDate(day),
        time=LocalTimeOfDay(time),
        end_date=LocalDate(end_day or day),
        end_time=LocalTimeOfDay(end_time),
        timezone=TimezoneName("Asia/Tbilisi"),
        party_size=PartySize(5),
        status=BookingStatus.CONFIRMED,
        source_channel=ChannelKind.INSTAGRAM,
        notes=None if notes is None else BookingNote(notes),
    )


def full_date(day: date, language: str) -> str:
    return format_date(day, "full", locale=find_locale(LanguageTag(language)))


def message_input(
    language: str,
    booking: BookingView | None = None,
    booking_unit: BookingUnit = BookingUnit.TIME_SLOT,
    policy: str | None = None,
) -> BookingMessageInput:
    return BookingMessageInput(
        business_name=BusinessName("Salobie Bia"),
        booking=booking or booking_view(),
        booking_unit=booking_unit,
        language=LanguageTag(language),
        cancellation_policy=None if policy is None else CancellationPolicyText(policy),
    )


@pytest.mark.parametrize("language", CUSTOMER_LANGUAGES)
def test_booking_confirmation_repeats_date_time_name_and_party(language: str) -> None:
    text = str(
        BookingConfirmationTransformer(RESOLVER).transform(message_input(language))
    )

    assert full_date(date(2026, 10, 6), language) in text
    for value in ("19:30", "Nino Kapanadze", "Salobie Bia", "5"):
        assert value in text

    assert "{" not in text
    assert (FIRST_STRONG_ISOLATE in text) is is_right_to_left(LanguageTag(language))


@pytest.mark.parametrize("language", CUSTOMER_LANGUAGES)
def test_stay_confirmation_has_check_in_and_check_out(language: str) -> None:
    stay = booking_view(
        day="2026-10-12", time="14:00", end_day="2026-10-15", end_time="12:00"
    )

    text = str(
        BookingConfirmationTransformer(RESOLVER).transform(
            message_input(language, stay, BookingUnit.NIGHT)
        )
    )

    assert full_date(date(2026, 10, 12), language) in text
    assert full_date(date(2026, 10, 15), language) in text
    assert "14:00" in text and "12:00" in text and "{" not in text


@pytest.mark.parametrize("language", CUSTOMER_LANGUAGES)
def test_cancellation_and_reschedule_quote_the_policy(language: str) -> None:
    policy = "Free cancellation up to 2 hours before."
    cancelled = str(
        CancellationConfirmationTransformer(RESOLVER).transform(
            message_input(language, policy=policy)
        )
    )
    moved = str(
        RescheduleConfirmationTransformer(RESOLVER).transform(
            message_input(language, policy=policy)
        )
    )
    without_policy = str(
        CancellationConfirmationTransformer(RESOLVER).transform(message_input(language))
    )

    for text in (cancelled, moved):
        assert full_date(date(2026, 10, 6), language) in text
        assert "19:30" in text and policy in text and "{" not in text
        assert len(text.splitlines()) == 2

    assert "Nino Kapanadze" in moved
    assert len(without_policy.splitlines()) == 1


@pytest.mark.parametrize("language", CUSTOMER_LANGUAGES)
def test_handoff_customer_message_in_and_out_of_hours(language: str) -> None:
    transformer = HandoffCustomerMessageTransformer(RESOLVER)

    soon = str(
        transformer.transform(
            HandoffCustomerMessageInput(language=LanguageTag(language))
        )
    )
    later = str(
        transformer.transform(
            HandoffCustomerMessageInput(
                language=LanguageTag(language),
                reopens_on=LocalDate("2026-10-11"),
                reopens_at=LocalTimeOfDay("09:00"),
            )
        )
    )

    assert "{" not in soon and "09:00" not in soon
    assert full_date(date(2026, 10, 11), language) in later
    assert "09:00" in later
    assert soon != later


def test_fallbacks_regional_tags_and_unknown_locales() -> None:
    transformer = BookingConfirmationTransformer(RESOLVER)

    swiss_german = str(transformer.transform(message_input("de-CH")))
    brazilian = str(transformer.transform(message_input("pt-BR")))
    klingon = str(transformer.transform(message_input("tlh")))

    assert swiss_german.startswith("Ihre Reservierung bei Salobie Bia")
    assert brazilian.startswith("Your booking at Salobie Bia")
    assert "Tuesday, October 6, 2026" in brazilian
    assert "Tuesday, October 6, 2026" in klingon
    assert str(find_locale(LanguageTag("tlh"))) == "en"


def test_template_language_choice() -> None:
    assert choose_template_language(TIME_SLOT_CONFIRMATION, LanguageTag("ka")) == "ka"
    assert (
        choose_template_language(TIME_SLOT_CONFIRMATION, LanguageTag("uk-UA")) == "uk"
    )
    assert choose_template_language(TIME_SLOT_CONFIRMATION, LanguageTag("ja")) == "en"


def staff_input(
    language: str, notes: str | None = None
) -> BookingStaffNotificationInput:
    return BookingStaffNotificationInput(
        business_name=BusinessName("Salobie Bia"),
        booking=booking_view(notes=notes),
        contact_phone_display=FormattedPhoneNumber("+995 555 12 34 56"),
        language=LanguageTag(language),
    )


def test_staff_booking_notifications_in_staff_languages() -> None:
    new_booking = NewBookingNotificationTransformer(RESOLVER)

    assert str(new_booking.transform(staff_input("ka", notes="Birthday cake"))) == (
        "ახალი ჯავშანი · Salobie Bia\n"
        "სამშაბათი, 06 ოქტომბერი, 2026, 19:30–21:30 · Table 4\n"
        "სახელი: Nino Kapanadze\n"
        "ტელეფონი: +995 555 12 34 56\n"
        "სტუმრები: 5\n"
        "არხი: Instagram\n"
        "შენიშვნა: Birthday cake"
    )
    assert str(new_booking.transform(staff_input("de"))).startswith(
        "New booking · Salobie Bia\nTuesday, October 6, 2026, 19:30–21:30"
    )
    assert str(
        BookingCancelledNotificationTransformer(RESOLVER).transform(staff_input("ru"))
    ).startswith("Бронь отменена · Salobie Bia\nвторник, 6 октября 2026")
    assert str(
        BookingMovedNotificationTransformer(RESOLVER).transform(staff_input("en"))
    ).startswith("Booking moved to a new time · Salobie Bia")


def test_staff_notification_for_a_stay_spans_two_dates() -> None:
    stay = staff_input("en").model_copy(
        update={
            "booking": booking_view(
                day="2026-10-12", time="14:00", end_day="2026-10-15", end_time="12:00"
            )
        }
    )

    text = str(NewBookingNotificationTransformer(RESOLVER).transform(stay))

    assert "Monday, October 12, 2026, 14:00 – Thursday, October 15, 2026, 12:00" in text


def test_lead_and_handoff_notifications_without_optional_values() -> None:
    lead = LeadView(
        id=LeadId(),
        business_id=BusinessId(),
        contact_id=ContactId(),
        lead_type=LeadType.CORPORATE,
        details=LeadDetails("Team dinner for a bank"),
        source_channel=ChannelKind.WEB_CHAT,
        status=LeadStatus.NEW,
    )

    lead_text = str(
        NewLeadNotificationTransformer(RESOLVER).transform(
            LeadStaffNotificationInput(
                business_name=BusinessName("Salobie Bia"),
                lead=lead,
                language=LanguageTag("en"),
            )
        )
    )
    handoff_text = str(
        HandoffNotificationTransformer(RESOLVER).transform(
            HandoffStaffNotificationInput(
                business_name=BusinessName("Salobie Bia"),
                reason=HandoffReason.EMERGENCY,
                urgency=HandoffUrgency.CRITICAL,
                summary=HandoffSummary("Guest fainted at table 4."),
                channel=ChannelKind.PHONE,
                language=LanguageTag("ka"),
            )
        )
    )

    assert lead_text.splitlines() == [
        "New request · Salobie Bia",
        "Type: Corporate event",
        "Team dinner for a bank",
        "Name: —",
        "Phone: —",
        "Channel: Website chat",
    ]
    assert handoff_text.splitlines()[:3] == [
        "[კრიტიკული] კლიენტს ადამიანი სჭირდება · Salobie Bia",
        "მიზეზი: საგანგებო სიტუაცია",
        "Guest fainted at table 4.",
    ]
    assert handoff_text.splitlines()[-1] == "არხი: ზარი"


def test_calendar_event_text_in_the_owner_language() -> None:
    text = CalendarEventTextTransformer(RESOLVER).transform(
        CalendarEventTextInput(
            booking=booking_view(notes="High chair"),
            contact_phone_display=FormattedPhoneNumber("+995 555 12 34 56"),
            language=LanguageTag("ru"),
        )
    )

    assert text.title == "Бронь: Nino Kapanadze, гостей: 5"
    assert str(text.description).splitlines()[:3] == [
        "Table 4",
        "Телефон: +995 555 12 34 56",
        "Канал: Instagram",
    ]
    assert str(text.description).splitlines()[-1] == "Пожелания: High chair"
