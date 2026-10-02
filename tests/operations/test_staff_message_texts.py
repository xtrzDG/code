"""Texts for staff: booking, stay, lead and handoff notices, and calendar events."""

from app.schemas.constants.bookings import (
    LeadStatus,
    LeadType,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.dto.bookings import LeadView
from app.schemas.dto.operations.message_texts import (
    CalendarEventTextInput,
    HandoffStaffNotificationInput,
    LeadStaffNotificationInput,
)
from app.schemas.typings.bookings.prefixed_id import LeadId
from app.schemas.typings.bookings.strings import LeadDetails
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
)
from app.schemas.typings.localization.strings import FormattedPhoneNumber
from app.transformers.notifications.booking_cancelled_notification_transformer import (
    BookingCancelledNotificationTransformer,
)
from app.transformers.notifications.booking_moved_notification_transformer import (
    BookingMovedNotificationTransformer,
)
from app.transformers.notifications.calendar_event_text_transformer import (
    CalendarEventTextTransformer,
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
from tests.operations.message_text_helpers import RESOLVER, booking_view, staff_input


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
