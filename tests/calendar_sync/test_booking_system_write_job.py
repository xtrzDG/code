"""
The `write_booking_system_booking` job and its queue: only real bookings of
tables that follow Cal.com (or that were written there) are queued, one at
a time per booking; a repeated write finds the booking written before; a
booking moved to another table is cancelled there and written for the new
one; a table that stopped following keeps what it has; failures are
recorded and retried only when a retry may help.
"""

import json

import pytest

from app.adapters.storage.booking_upgrades import upgrade_bookings_from_v4
from app.adapters.storage.persisted_document_codec import PersistedDocumentCodec
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.domain.bookings import BookingDocument
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.calendar_sync.booking_system_jobs import (
    WRITE_BOOKING_SYSTEM_BOOKING_JOB,
)
from tests.calendar_sync.booking_write_world import EVENT_TYPE, BookingWriteWorld


def queued(world: BookingWriteWorld) -> list[str]:
    return [
        str(call.serial_key)
        for call in world.job_queue.calls
        if call.job_name == WRITE_BOOKING_SYSTEM_BOOKING_JOB
    ]


def test_only_real_bookings_of_following_tables_are_queued() -> None:
    world = BookingWriteWorld()
    world.follow(world.table_for_four)
    followed = world.evening()
    elsewhere = world.evening(world.table_for_eight, "Tamar")
    test_booking = world.changed(world.evening(name="Ana"), is_sandbox=True)

    for booking in (followed, elsewhere, test_booking):
        world.queue.sync(booking)

    assert queued(world) == [f"booking_system:{followed.id}"]
    assert world.cal_com.requests == []


def test_a_booking_written_before_is_queued_after_its_table_stopped_following() -> None:
    world = BookingWriteWorld()
    world.follow(world.table_for_four)
    booking = world.evening()
    world.write(booking)
    world.unfollow(world.table_for_four)

    world.queue.sync(world.stored(booking))

    assert queued(world) == [f"booking_system:{booking.id}"]


def test_a_write_repeated_after_a_crash_finds_the_booking_written_before() -> None:
    world = BookingWriteWorld()
    world.follow(world.table_for_four)
    booking = world.evening()
    world.write(booking)
    # The write went through but its id was not kept (the worker died).
    world.changed(booking, booking_system_booking=None)

    world.write(booking)

    ref = world.stored(booking).booking_system_booking
    assert ref is not None and str(ref.booking_id) == "created-1"
    assert len(world.cal_com.created) == 1


def test_a_booking_moved_to_another_table_follows_it() -> None:
    world = BookingWriteWorld()
    world.follow(world.table_for_four)
    world.follow(world.table_for_eight)
    booking = world.evening()
    world.write(booking)

    world.changed(booking, resource_id=world.table_for_eight.id)
    world.write(booking)

    ref = world.stored(booking).booking_system_booking
    assert world.cal_com.cancelled == ["created-1"]
    assert ref is not None and ref.resource_id == world.table_for_eight.id
    assert world.cal_com.active_created() == ["created-2"]


def test_a_table_that_stopped_following_keeps_what_it_has() -> None:
    world = BookingWriteWorld()
    world.follow(world.table_for_four)
    booking = world.evening()
    world.write(booking)
    world.unfollow(world.table_for_four)

    world.changed(booking, status=BookingStatus.CANCELLED)
    world.write(booking)

    assert world.cal_com.cancelled == []
    assert world.stored(booking).booking_system_booking is None


def test_a_refused_key_is_recorded_and_not_retried() -> None:
    world = BookingWriteWorld()
    world.follow(world.table_for_four, key="cal_wrong_key_0000")
    booking = world.evening()

    report = world.write(booking)

    status = world.link_of(world.table_for_four).write_status
    assert int(report.processed_count) == 0
    assert status.problem is CalendarSyncProblem.ACCESS_DENIED
    assert status.last_failed_at is not None
    assert world.stored(booking).booking_system_booking is None


def test_a_slow_cal_com_is_retried_until_the_last_attempt() -> None:
    world = BookingWriteWorld()
    world.follow(world.table_for_four)
    booking = world.evening()
    world.cal_com.is_slow = True

    with pytest.raises(BusyTimeSourceError):
        world.write(booking)
    last = world.write(booking, is_final=True)

    assert int(last.processed_count) == 0
    status = world.link_of(world.table_for_four).write_status
    assert status.problem is CalendarSyncProblem.TIMEOUT


def test_a_guest_without_a_name_is_named_in_the_owners_language() -> None:
    world = BookingWriteWorld()
    world.follow(world.table_for_four)
    booking = world.evening()
    contact = world.contact_repo.get(world.business.id, booking.contact_id)
    assert contact is not None
    world.contact_repo.save(contact.model_copy(update={"name": None}))

    world.write(booking)

    [created] = world.cal_com.created
    # The owner reads Cal.com in Russian; the guest wrote in Russian too.
    assert str(world.business.owner_language) == "ru"
    assert created["attendee"]["name"] == "Гость"
    assert created["attendee"]["language"] == "ru"
    assert created["eventTypeId"] == int(EVENT_TYPE)


def test_a_booking_gone_writes_nothing() -> None:
    world = BookingWriteWorld()
    world.follow(world.table_for_four)
    gone = world.evening().model_copy(update={"id": BookingId()})

    report = world.write(gone)

    assert int(report.processed_count) == 0
    assert world.cal_com.requests == []


def test_bookings_stored_before_version_5_were_written_nowhere() -> None:
    booking = BookingWriteWorld().evening()
    stored = booking.model_dump(mode="json", exclude={"booking_system_booking"})
    stored["schema_version"] = "4"
    codec = PersistedDocumentCodec(BookingDocument, DocumentCollectionName("bookings"))

    upgraded = upgrade_bookings_from_v4(stored)
    read = codec.decode(json.dumps(stored))

    assert upgraded["booking_system_booking"] is None
    assert read.booking_system_booking is None
    assert read.id == booking.id
