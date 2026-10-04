"""
Reminders go through the outbox: queued once per booking and start time,
with their delivery job, so a run that comes again after a crash or a
restart never sends a second one, and a moved booking is reminded of its
new time.
"""

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import OutboundMessageKind, OutboundMessageStatus
from app.schemas.constants.jobs import JobLane
from app.schemas.dto.job_queue import QueuedJobPageQuery
from app.schemas.typings.bookings.constrained_integers import (
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.platform.constrained_integers import PageSize
from tests.operations.reminder_scene import ReminderScene


def queued_jobs(scene: ReminderScene) -> list[str]:
    return [
        str(job.name)
        for job in scene.sender.jobs.job_repo.list_page(
            QueuedJobPageQuery(page_size=PageSize(50))
        )
    ]


def test_a_reminder_is_one_outbox_message_with_its_delivery_job() -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"})
    booking = scene.add_booking(contact, "2026-10-05T15:00:00+00:00")

    assert scene.run().processed_count == 1

    [message] = scene.sender.queued()
    assert message.kind is OutboundMessageKind.BOOKING_REMINDER
    assert message.status is OutboundMessageStatus.PENDING
    assert message.booking_id == booking.id
    assert message.customer is not None
    assert str(message.customer.channel_user_id) == "7001"
    assert queued_jobs(scene) == ["deliver_outbound"]
    [job] = scene.sender.jobs.job_repo.list_page(
        QueuedJobPageQuery(page_size=PageSize(1))
    )
    assert job.lane is JobLane.OUTBOUND


def test_a_reminder_is_not_duplicated_across_a_restart() -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"})
    booking = scene.add_booking(contact, "2026-10-05T15:00:00+00:00")
    assert scene.run().processed_count == 1

    # The worker died after queuing the reminder, before the booking was
    # marked: the next run (a fresh process) finds the reminder queued.
    stored = scene.stored(booking)
    stored.reminder_sent_at = None
    scene.world.booking_repo.save(stored)
    rerun = scene.run()

    assert rerun.processed_count == 1
    assert len(scene.sender.queued()) == 1
    assert queued_jobs(scene) == ["deliver_outbound"]
    assert scene.stored(booking).reminder_sent_at is not None
    # A third run has nothing left to do.
    assert scene.run().processed_count == 0
    assert len(scene.sender.queued()) == 1


def test_a_moved_booking_is_reminded_of_its_new_time() -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"})
    booking = scene.add_booking(contact, "2026-10-05T15:00:00+00:00")
    assert scene.run().processed_count == 1

    moved = scene.stored(booking)
    moved.starts_at = BookingStartsAtUnixSeconds(int(moved.starts_at) + 3600)
    moved.reminder_sent_at = None
    scene.world.booking_repo.save(moved)

    assert scene.run().processed_count == 1
    first, second = scene.sender.queued()
    assert first.idempotency_key != second.idempotency_key
    assert "20:00" in str(second.text)  # 16:00 UTC is 20:00 in Tbilisi
