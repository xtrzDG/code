"""
Booking notes with health data are Restricted (PRIV-10): they never leave
the platform in a staff message, a Google Calendar event or a public API
or webhook payload ("see the booking" instead); other notes do as before.
"""

import pytest

from app.schemas.dto.operations.message_texts import CalendarEventTextInput
from app.schemas.typings.bookings.strings import BookingNote
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import FormattedPhoneNumber
from app.transformers.notifications.booking_moved_notification_transformer import (
    BookingMovedNotificationTransformer,
)
from app.transformers.notifications.calendar_event_text_transformer import (
    CalendarEventTextTransformer,
)
from app.transformers.notifications.new_booking_notification_transformer import (
    NewBookingNotificationTransformer,
)
from app.utilities.privacy.health_notes import is_health_note
from tests.operations.message_text_helpers import RESOLVER, booking_view, staff_input

HEALTH_NOTE: str = "Nut allergy, carries an EpiPen"


@pytest.mark.parametrize(
    "notes",
    [
        "Nut allergy",
        "Allergia alle arachidi",
        "intolleranza al lattosio",
        "Celiaca, senza glutine",
        "Coeliac",
        "Incinta di 6 mesi",
        "Pregnant, no hot stones",
        "Diabetic",
        "Comes in a wheelchair",
        "Sedia a rotelle",
        "Takes medication for the heart",
        "Farmaci anticoagulanti",
        "Аллергия на орехи",
        "Zöliakie",
        "ALLERGIE AUX NOIX",
    ],
)
def test_health_notes_are_recognised(notes: str) -> None:
    assert is_health_note(BookingNote(notes))


@pytest.mark.parametrize(
    "notes",
    [
        "High chair",
        "Birthday cake",
        "Window table",
        "Trattamento viso",
        "Late arrival, 20 minutes",
        "Vegetarian menu",
    ],
)
def test_other_notes_are_not(notes: str) -> None:
    assert not is_health_note(BookingNote(notes))


def test_staff_messages_point_to_the_booking_instead_of_a_health_note() -> None:
    new_booking = NewBookingNotificationTransformer(RESOLVER)
    moved = BookingMovedNotificationTransformer(RESOLVER)

    english = str(new_booking.transform(staff_input("en", notes=HEALTH_NOTE)))
    italian = str(moved.transform(staff_input("it", notes="Allergia alle noci")))

    assert english.splitlines()[-1] == (
        "Notes: health details, see the booking in the cabinet."
    )
    assert "EpiPen" not in english and "Nut" not in english
    assert italian.splitlines()[-1] == (
        "Note: dati sulla salute, vedi la prenotazione nel pannello."
    )
    assert "noci" not in italian


def test_a_calendar_event_never_carries_a_health_note() -> None:
    text = CalendarEventTextTransformer(RESOLVER).transform(
        CalendarEventTextInput(
            booking=booking_view(notes=HEALTH_NOTE),
            contact_phone_display=FormattedPhoneNumber("+995 555 12 34 56"),
            language=LanguageTag("en"),
        )
    )

    assert "EpiPen" not in str(text.description)
    assert str(text.description).splitlines()[-1] == (
        "Notes: health details, see the booking in the cabinet."
    )
