"""
An erased customer leaves the business's Google Calendar too (PRIV-08): a
booking still ahead keeps its event without the guest's name, phone or
notes; a past one's event (the mirror keeps those) is deleted with its
link; a Google failure is shown on the connection and never fails the
erasure.
"""

import pytest

from app.facilitators.calendar.google_calendar_guest_eraser import (
    GoogleCalendarGuestEraser,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.bookings.strings import BookingNote
from tests.operations.calendar_world import CalendarWorld


def eraser(calendar: CalendarWorld) -> GoogleCalendarGuestEraser:
    return GoogleCalendarGuestEraser(
        connection_repo=calendar.connection_repo,
        event_link_repo=calendar.link_repo,
        calendar_client=calendar.client,
        secret_cipher=calendar.cipher,
        mirror=calendar.sync,
        wall_clock=calendar.world.clock.wall_clock,
    )


def mirrored(calendar: CalendarWorld, status: BookingStatus) -> BookingDocument:
    """A booking with notes, mirrored while confirmed, then in `status`."""

    booking = calendar.booking()
    booking.notes = BookingNote("Allergic to nuts")
    calendar.world.booking_repo.save(booking)
    calendar.sync.sync(booking)
    booking.status = status
    calendar.world.booking_repo.save(booking)
    calendar.sync.sync(booking)
    return booking


def erase_guest(calendar: CalendarWorld, bookings: list[BookingDocument]) -> None:
    """What the erasure leaves: the contact erased, the bookings' notes gone."""

    contact = calendar.contact
    calendar.world.contact_repo.save(
        ContactDocument(
            id=contact.id,
            business_id=contact.business_id,
            erased_at=calendar.world.clock.now_microseconds(),
            created_at=contact.created_at,
            updated_at=calendar.world.clock.now_microseconds(),
        )
    )
    for booking in bookings:
        booking.notes = None
        calendar.world.booking_repo.save(booking)


def event_of(calendar: CalendarWorld, booking: BookingDocument) -> dict[str, object]:
    link = calendar.link_repo.find_by_booking(calendar.business.id, booking.id)
    assert link is not None
    return calendar.google.events[str(link.event_id)]


def test_an_upcoming_event_loses_the_guest_and_a_past_one_is_deleted() -> None:
    calendar = CalendarWorld()
    calendar.complete(calendar.start())
    upcoming = mirrored(calendar, BookingStatus.CONFIRMED)
    past = mirrored(calendar, BookingStatus.COMPLETED)
    before = str(event_of(calendar, upcoming))
    assert "Nino" in before
    assert "Allergic" in before
    assert len(calendar.google.events) == 2
    erase_guest(calendar, [upcoming, past])

    changed = eraser(calendar).forget_guest([upcoming, past])

    assert int(changed) == 2
    after = str(event_of(calendar, upcoming))
    assert "Nino" not in after
    assert "555" not in after
    assert "Allergic" not in after
    assert calendar.link_repo.find_by_booking(calendar.business.id, past.id) is None
    assert len(calendar.google.events) == 1


def test_bookings_without_an_event_or_of_the_sandbox_are_left_alone() -> None:
    calendar = CalendarWorld()
    calendar.complete(calendar.start())
    never_mirrored = calendar.booking(status=BookingStatus.COMPLETED)
    sandbox = calendar.booking(is_sandbox=True)

    assert int(eraser(calendar).forget_guest([never_mirrored, sandbox])) == 0
    assert calendar.calendar_requests() == []


def test_a_google_failure_is_shown_on_the_connection_and_never_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calendar = CalendarWorld()
    calendar.complete(calendar.start())
    past = mirrored(calendar, BookingStatus.NO_SHOW)
    erase_guest(calendar, [past])

    def refuse(*_arguments: object) -> None:
        raise ExternalServiceError("Google Calendar event delete failed: 503.")

    monkeypatch.setattr(calendar.client, "delete_event", refuse)
    changed = eraser(calendar).forget_guest([past])

    assert int(changed) == 0
    connection = calendar.connection()
    assert connection is not None
    assert str(connection.last_sync_error) == (
        "Google Calendar event delete failed: 503."
    )
    # The link stays, so the event can still be found and deleted.
    assert calendar.link_repo.find_by_booking(calendar.business.id, past.id)


def test_a_disconnected_calendar_only_forgets_the_link() -> None:
    calendar = CalendarWorld()
    calendar.complete(calendar.start())
    past = mirrored(calendar, BookingStatus.COMPLETED)
    calendar.connection_repo.delete_by_business(calendar.business.id)

    assert int(eraser(calendar).forget_guest([past])) == 0
    assert calendar.link_repo.find_by_booking(calendar.business.id, past.id) is None
