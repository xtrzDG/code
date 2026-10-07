"""Mirroring bookings in the connected Google Calendar."""

from datetime import datetime

from app.facilitators.calendar.google_calendar_sync_facilitator import (
    summarize_sync_failure,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.bookings import CreateBookingCommand
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.channels.strings import EncryptedChannelSecret
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from tests.operations.calendar_world import CalendarWorld


class TestSync:
    def test_event_follows_the_booking_in_the_owner_language(self) -> None:
        calendar = CalendarWorld()
        calendar.complete(calendar.start())
        booking = calendar.booking()

        calendar.sync.sync(booking)

        link = calendar.link_repo.find_by_booking(calendar.business.id, booking.id)
        assert link is not None
        event = calendar.google.events[str(link.event_id)]
        assert event["summary"] == "Бронь: Nino, гостей: 2"
        assert event["start"] == {
            "dateTime": "2026-10-06T15:00:00Z",
            "timeZone": "Asia/Tbilisi",
        }
        assert "Телефон: +995 555 12 34 56" in str(event["description"])

        booking.starts_at = BookingStartsAtUnixSeconds(int(booking.starts_at) + 3600)
        booking.ends_at = BookingEndsAtUnixSeconds(int(booking.ends_at) + 3600)
        calendar.sync.sync(booking)
        assert calendar.google.events[str(link.event_id)]["start"] == {
            "dateTime": "2026-10-06T16:00:00Z",
            "timeZone": "Asia/Tbilisi",
        }

        booking.status = BookingStatus.CANCELLED
        calendar.sync.sync(booking)
        assert calendar.google.events == {}
        assert (
            calendar.link_repo.find_by_booking(calendar.business.id, booking.id) is None
        )
        assert [request.method for request in calendar.calendar_requests()] == [
            "POST",
            "PATCH",
            "DELETE",
        ]
        # The access token from the code exchange is still valid: no refresh.
        assert calendar.google.refresh_count == 0

    def test_expired_access_token_is_refreshed_once_and_cached(self) -> None:
        calendar = CalendarWorld()
        calendar.complete(calendar.start())
        calendar.world.clock.move_to(
            datetime.fromisoformat("2026-10-05T10:00:00+00:00")
        )

        calendar.sync.sync(calendar.booking())
        calendar.sync.sync(calendar.booking())

        assert calendar.google.refresh_count == 1
        assert [
            request.headers["authorization"] for request in calendar.calendar_requests()
        ] == ["Bearer access-refreshed-1", "Bearer access-refreshed-1"]
        connection = calendar.connection()
        assert connection is not None
        assert connection.encrypted_access_token is not None
        assert calendar.cipher.decrypt(connection.encrypted_access_token) == (
            "access-refreshed-1"
        )

    def test_nothing_happens_without_connection_for_sandbox_or_finished(self) -> None:
        calendar = CalendarWorld()
        calendar.sync.sync(calendar.booking())
        assert calendar.google.requests == []

        calendar.complete(calendar.start())
        calendar.sync.sync(calendar.booking(is_sandbox=True))
        calendar.sync.sync(calendar.booking(status=BookingStatus.COMPLETED))
        calendar.sync.sync(calendar.booking(status=BookingStatus.CANCELLED))
        assert calendar.calendar_requests() == []

    def test_google_and_storage_failures_never_raise(self) -> None:
        calendar = CalendarWorld()
        calendar.complete(calendar.start())
        booking = calendar.booking()
        calendar.google.failure_status = 503

        calendar.sync.sync(booking)

        assert (
            calendar.link_repo.find_by_booking(calendar.business.id, booking.id) is None
        )
        connection = calendar.connection()
        assert connection is not None
        assert connection.last_sync_error == (
            "Google Calendar event insert returned HTTP 503 (UNAVAILABLE)."
        )
        assert connection.last_sync_error_at == calendar.world.clock.now_microseconds()
        assert connection.last_synced_at is None
        connection.encrypted_access_token = None
        connection.encrypted_refresh_token = EncryptedChannelSecret("corrupted")
        calendar.connection_repo.save(connection)
        calendar.google.failure_status = None
        requests_before = len(calendar.google.requests)

        calendar.sync.sync(booking)

        assert len(calendar.google.requests) == requests_before
        broken = calendar.connection()
        assert broken is not None
        assert broken.last_sync_error is not None
        assert "corrupted" not in str(broken.last_sync_error)

    def test_a_successful_sync_clears_the_last_error(self) -> None:
        calendar = CalendarWorld()
        calendar.complete(calendar.start())
        calendar.google.failure_status = 401
        calendar.sync.sync(calendar.booking())
        failed = calendar.connection()
        assert failed is not None
        assert failed.last_sync_error is not None

        calendar.google.failure_status = None
        calendar.sync.sync(calendar.booking())

        healed = calendar.connection()
        assert healed is not None
        assert healed.last_sync_error is None
        assert healed.last_sync_error_at is None
        assert healed.last_synced_at == calendar.world.clock.now_microseconds()

    def test_long_provider_errors_are_shortened(self) -> None:
        summary = summarize_sync_failure("x" * 1000)

        assert len(str(summary)) == 300
        assert str(summary).endswith("…")
        assert summarize_sync_failure("  a \n b ") == "a b"

    def test_create_booking_pushes_the_event(self) -> None:
        calendar = CalendarWorld()
        calendar.complete(calendar.start())

        calendar.world.create_booking(calendar.sync).run(
            CreateBookingCommand(
                business_id=calendar.business.id,
                contact_id=calendar.contact.id,
                contact_name=ContactName("Nino"),
                contact_phone_number=E164PhoneNumber("+995555123456"),
                date=LocalDate("2026-10-07"),
                time=LocalTimeOfDay("20:00"),
                party_size=PartySize(2),
                source_channel=ChannelKind.TELEGRAM,
                language=LanguageTag("ka"),
            )
        )

        assert len(calendar.google.events) == 1
        event = next(iter(calendar.google.events.values()))
        assert event["end"] == {
            "dateTime": "2026-10-07T18:00:00Z",
            "timeZone": "Asia/Tbilisi",
        }
