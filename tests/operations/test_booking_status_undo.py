"""Undoing a status change staff made to a booking (revert-status)."""

from datetime import datetime

import pytest

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.bookings import BookingView, CancelBookingCommand
from app.schemas.dto.operations.bookings import (
    RevertBookingStatusCommand,
    UpdateBookingCommand,
)
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.bookings.prefixed_id import BookingId, ResourceId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.operations.cabinet_bookings_helpers import Cabinet

EVENING_START: str = "2026-10-05T19:00:00+04:00"
EVENING_END: str = "2026-10-05T21:00:00+04:00"


def evening_booking(cabinet: Cabinet, **options: object) -> BookingDocument:
    return cabinet.world.add_booking(
        cabinet.business,
        cabinet.table,
        cabinet.customer,
        EVENING_START,
        EVENING_END,
        **options,  # type: ignore[arg-type]
    )


def set_status(
    cabinet: Cabinet, booking_id: BookingId, status: BookingStatus
) -> BookingView:
    return cabinet.world.update_booking().run(
        UpdateBookingCommand(
            business_id=cabinet.business.id,
            actor_id=cabinet.staff_id,
            booking_id=booking_id,
            status=status,
        )
    )


def undo(cabinet: Cabinet, booking_id: BookingId, status: BookingStatus) -> BookingView:
    return cabinet.world.revert_booking_status().run(
        RevertBookingStatusCommand(
            business_id=cabinet.business.id,
            actor_id=cabinet.staff_id,
            booking_id=booking_id,
            status=status,
        )
    )


def refusal_code(error: pytest.ExceptionInfo[ConflictError]) -> str:
    return str(error.value.reasons[0].code)


def stored(cabinet: Cabinet, booking_id: BookingId) -> BookingDocument:
    booking = cabinet.world.booking_repo.get(cabinet.business.id, booking_id)
    assert booking is not None
    return booking


def test_undo_restores_the_status_once_and_audits_it() -> None:
    cabinet = Cabinet()
    booking = evening_booking(cabinet)

    assert set_status(cabinet, booking.id, BookingStatus.COMPLETED).status is (
        BookingStatus.COMPLETED
    )
    change = stored(cabinet, booking.id).last_status_change
    assert change is not None and change.changed_by == cabinet.staff_id
    assert change.previous_status is BookingStatus.CONFIRMED

    restored = undo(cabinet, booking.id, BookingStatus.COMPLETED)

    assert restored.status is BookingStatus.CONFIRMED
    assert stored(cabinet, booking.id).last_status_change is None
    audited = cabinet.world.audit_repo.list_by_business(cabinet.business.id)
    assert [entry.action for entry in audited] == [AuditAction.UPDATE] * 2
    assert {str(entry.actor_id) for entry in audited} == {str(cabinet.staff_id)}
    assert cabinet.world.live_events.kinds() == [LiveEventKind.BOOKING_CHANGED] * 2
    assert [item.status for item in cabinet.world.calendar_sync.synced][-1] is (
        BookingStatus.CONFIRMED
    )

    with pytest.raises(ConflictError) as again:
        undo(cabinet, booking.id, BookingStatus.COMPLETED)
    assert refusal_code(again) == "nothing_to_undo"


def test_undo_of_a_no_show_refused_when_the_table_was_taken_meanwhile() -> None:
    cabinet = Cabinet()
    booking = evening_booking(cabinet)
    set_status(cabinet, booking.id, BookingStatus.NO_SHOW)
    # A walk-in takes the freed table for the same evening.
    walk_in = cabinet.world.create_manual_booking().run(
        cabinet.manual(name="Walk-in", day="2026-10-05", time="19:30", party_size=2)
    )
    assert walk_in.booking.resource_id == cabinet.table.id

    with pytest.raises(ConflictError) as refused:
        undo(cabinet, booking.id, BookingStatus.NO_SHOW)

    assert refusal_code(refused) == "slot_taken"
    assert refused.value.reasons[0].details == [str(cabinet.table.id)]
    assert stored(cabinet, booking.id).status is BookingStatus.NO_SHOW


def test_undo_of_a_no_show_succeeds_when_another_table_was_taken() -> None:
    cabinet = Cabinet()
    booking = evening_booking(cabinet)
    set_status(cabinet, booking.id, BookingStatus.NO_SHOW)
    cabinet.world.add_booking(
        cabinet.business, cabinet.hall, cabinet.customer, EVENING_START, EVENING_END
    )
    # A booking that ends before this one starts does not overlap it.
    cabinet.world.add_booking(
        cabinet.business,
        cabinet.table,
        cabinet.customer,
        "2026-10-05T16:00:00+04:00",
        "2026-10-05T19:00:00+04:00",
    )

    assert undo(cabinet, booking.id, BookingStatus.NO_SHOW).status is (
        BookingStatus.CONFIRMED
    )


def test_cancellation_in_the_cabinet_can_be_undone_but_not_the_customers() -> None:
    cabinet = Cabinet()
    by_staff = evening_booking(cabinet)
    by_customer = cabinet.world.add_booking(
        cabinet.business,
        cabinet.hall,
        cabinet.customer,
        EVENING_START,
        EVENING_END,
    )
    cancel = cabinet.world.cancel_booking()
    cancel.run(
        CancelBookingCommand(
            business_id=cabinet.business.id,
            booking_id=by_staff.id,
            language=LanguageTag("en"),
            actor_id=cabinet.staff_id,
        )
    )
    cancel.run(
        CancelBookingCommand(
            business_id=cabinet.business.id,
            booking_id=by_customer.id,
            contact_id=cabinet.customer.id,
            language=LanguageTag("en"),
        )
    )

    assert undo(cabinet, by_staff.id, BookingStatus.CANCELLED).status is (
        BookingStatus.CONFIRMED
    )
    with pytest.raises(ConflictError) as refused:
        undo(cabinet, by_customer.id, BookingStatus.CANCELLED)
    assert refusal_code(refused) == "nothing_to_undo"


def test_undo_window_and_a_later_status() -> None:
    cabinet = Cabinet()
    late = evening_booking(cabinet)
    pending = evening_booking(cabinet, status=BookingStatus.PENDING)
    set_status(cabinet, late.id, BookingStatus.COMPLETED)
    set_status(cabinet, pending.id, BookingStatus.CONFIRMED)

    with pytest.raises(ConflictError) as other_status:
        undo(cabinet, pending.id, BookingStatus.COMPLETED)
    assert refusal_code(other_status) == "status_changed"
    assert other_status.value.reasons[0].details == ["confirmed"]

    # Ten minutes is still in time; a minute more is not.
    cabinet.world.clock.move_to(datetime.fromisoformat("2026-10-05T08:10:00+00:00"))
    assert undo(cabinet, pending.id, BookingStatus.CONFIRMED).status is (
        BookingStatus.PENDING
    )
    cabinet.world.clock.move_to(datetime.fromisoformat("2026-10-05T08:11:00+00:00"))
    with pytest.raises(ConflictError) as expired:
        undo(cabinet, late.id, BookingStatus.COMPLETED)
    assert refusal_code(expired) == "undo_expired"
    assert expired.value.reasons[0].details == ["10"]


def test_undo_refused_for_a_missing_booking_or_place() -> None:
    cabinet = Cabinet()
    booking = evening_booking(cabinet)
    set_status(cabinet, booking.id, BookingStatus.NO_SHOW)
    moved = stored(cabinet, booking.id).model_copy(update={"resource_id": ResourceId()})
    cabinet.world.booking_repo.save(moved)

    with pytest.raises(ConflictError) as gone:
        undo(cabinet, booking.id, BookingStatus.NO_SHOW)
    assert refusal_code(gone) == "place_gone"
    with pytest.raises(NotFoundError):
        undo(cabinet, BookingId(), BookingStatus.NO_SHOW)


def test_undo_of_a_test_booking_stays_out_of_calendar_and_live_events() -> None:
    cabinet = Cabinet()
    booking = evening_booking(cabinet, is_sandbox=True)
    set_status(cabinet, booking.id, BookingStatus.COMPLETED)

    assert undo(cabinet, booking.id, BookingStatus.COMPLETED).status is (
        BookingStatus.CONFIRMED
    )
    assert cabinet.world.calendar_sync.synced == []
    assert cabinet.world.live_events.kinds() == []


def test_a_test_booking_sees_real_bookings_that_took_its_time() -> None:
    cabinet = Cabinet()
    booking = evening_booking(cabinet, is_sandbox=True)
    set_status(cabinet, booking.id, BookingStatus.NO_SHOW)
    evening_booking(cabinet)

    with pytest.raises(ConflictError) as refused:
        undo(cabinet, booking.id, BookingStatus.NO_SHOW)
    assert refusal_code(refused) == "slot_taken"
