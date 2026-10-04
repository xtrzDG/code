"""Which bookings the reminder job reminds, once, and what changes during a run."""

from datetime import datetime

import pytest

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.bookings import RescheduleBookingCommand
from app.schemas.typings.bookings.constrained_integers import (
    BookingReminderLeadSeconds,
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.operations.reminder_scene import ReminderScene


def test_a_cancellation_during_the_job_is_never_undone() -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"})
    first = scene.add_booking(
        contact, "2026-10-05T15:00:00+00:00", ChannelKind.TELEGRAM
    )
    second = scene.add_booking(
        contact, "2026-10-05T17:00:00+00:00", ChannelKind.TELEGRAM
    )

    def cancel_both_while_sending() -> None:
        for booking in (first, second):
            stored = scene.stored(booking)
            stored.status = BookingStatus.CANCELLED
            scene.world.booking_repo.save(stored)

    scene.sender.outbound_message_repo.on_insert = cancel_both_while_sending

    report = scene.run()

    # Only the first reminder was already on its way; the second booking is
    # read again before its turn and is no longer due.
    assert report.processed_count == 1
    assert len(scene.sender.sent) == 1
    for booking in (first, second):
        stored = scene.stored(booking)
        assert stored.status is BookingStatus.CANCELLED
        assert stored.reminder_sent_at is None


def test_a_move_during_the_send_keeps_the_new_time() -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"})
    booking = scene.add_booking(
        contact, "2026-10-05T15:00:00+00:00", ChannelKind.TELEGRAM
    )
    moved_start = BookingStartsAtUnixSeconds(int(booking.starts_at) + 3600)

    def move_while_sending() -> None:
        stored = scene.stored(booking)
        stored.starts_at = moved_start
        scene.world.booking_repo.save(stored)

    scene.sender.outbound_message_repo.on_insert = move_while_sending

    scene.run()

    stored = scene.stored(booking)
    assert stored.starts_at == moved_start
    assert stored.reminder_sent_at is None  # the next run reminds the new time


def test_a_second_run_does_not_remind_again() -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"})
    scene.add_booking(contact, "2026-10-05T15:00:00+00:00", ChannelKind.TELEGRAM)

    first = scene.run()
    second = scene.run()

    assert (first.processed_count, second.processed_count) == (1, 0)
    assert len(scene.sender.sent) == 1


def test_only_confirmed_real_bookings_starting_within_a_day_are_reminded() -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"})
    due = scene.add_booking(contact, "2026-10-06T07:00:00+00:00", ChannelKind.TELEGRAM)
    at_the_edge = scene.add_booking(
        contact, "2026-10-06T08:00:00+00:00", ChannelKind.TELEGRAM
    )
    skipped = [
        scene.add_booking(contact, "2026-10-06T08:00:01+00:00", ChannelKind.TELEGRAM),
        scene.add_booking(contact, "2026-10-05T07:00:00+00:00", ChannelKind.TELEGRAM),
        scene.add_booking(contact, "2026-10-05T08:00:00+00:00", ChannelKind.TELEGRAM),
        scene.add_booking(
            contact,
            "2026-10-05T15:00:00+00:00",
            ChannelKind.TELEGRAM,
            status=BookingStatus.CANCELLED,
        ),
        scene.add_booking(
            contact,
            "2026-10-05T15:00:00+00:00",
            ChannelKind.TELEGRAM,
            status=BookingStatus.PENDING,
        ),
        scene.add_booking(
            contact,
            "2026-10-05T15:00:00+00:00",
            ChannelKind.TELEGRAM,
            is_sandbox=True,
        ),
    ]

    report = scene.run()

    assert report.processed_count == 2
    assert scene.stored(due).reminder_sent_at is not None
    assert scene.stored(at_the_edge).reminder_sent_at is not None
    assert all(scene.stored(booking).reminder_sent_at is None for booking in skipped)


def test_reminder_lead_is_configurable() -> None:
    scene = ReminderScene(reminder_lead=BookingReminderLeadSeconds(2 * 60 * 60))
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"})
    soon = scene.add_booking(contact, "2026-10-05T09:30:00+00:00", ChannelKind.TELEGRAM)
    later = scene.add_booking(
        contact, "2026-10-05T10:30:00+00:00", ChannelKind.TELEGRAM
    )

    scene.run()

    assert scene.stored(soon).reminder_sent_at is not None
    assert scene.stored(later).reminder_sent_at is None


@pytest.mark.parametrize(
    ("status", "service_mode"),
    [
        (BusinessStatus.PAUSED, ServiceMode.FULL),
        (BusinessStatus.LIVE, ServiceMode.LEADS_ONLY),
    ],
)
def test_paused_or_leads_only_businesses_send_no_reminders(
    status: BusinessStatus,
    service_mode: ServiceMode,
) -> None:
    scene = ReminderScene()
    scene.business.status = status
    scene.business.service_mode = service_mode
    scene.world.business_repo.save(scene.business)
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"})
    scene.add_booking(contact, "2026-10-05T15:00:00+00:00", ChannelKind.TELEGRAM)

    report = scene.run()

    assert report.processed_count == 0
    assert scene.sender.sent == []


def test_rescheduled_booking_gets_a_new_reminder() -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"})
    booking = scene.add_booking(
        contact, "2026-10-05T15:00:00+00:00", ChannelKind.TELEGRAM
    )
    scene.run()
    assert scene.stored(booking).reminder_sent_at is not None

    scene.world.reschedule_booking().run(
        RescheduleBookingCommand(
            business_id=scene.business.id,
            booking_id=booking.id,
            new_date=LocalDate("2026-10-06"),
            new_time=LocalTimeOfDay("18:00"),
            language=LanguageTag("en"),
        )
    )

    assert scene.stored(booking).reminder_sent_at is None
    assert scene.run().processed_count == 0  # 18:00 tomorrow is 30 hours away

    scene.world.clock.move_to(datetime.fromisoformat("2026-10-05T16:00:00+00:00"))

    assert scene.run().processed_count == 1
    assert len(scene.sender.sent) == 2
