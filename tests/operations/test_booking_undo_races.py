"""An Undo and a new booking racing for the same freed time: one wins."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from app.schemas.constants.bookings import BookingStatus
from app.schemas.dto.operations.bookings import (
    RevertBookingStatusCommand,
    UpdateBookingCommand,
)
from app.schemas.exceptions.application_errors import ConflictError
from tests.operations.cabinet_bookings_helpers import Cabinet

ROUNDS: int = 12


def race_once() -> tuple[str, str]:
    """What the Undo and the walk-in booking each got: "ok" or the refusal."""

    cabinet = Cabinet()
    booking = cabinet.world.add_booking(
        cabinet.business,
        cabinet.table,
        cabinet.customer,
        "2026-10-05T19:00:00+04:00",
        "2026-10-05T21:00:00+04:00",
    )
    cabinet.world.update_booking().run(
        UpdateBookingCommand(
            business_id=cabinet.business.id,
            actor_id=cabinet.staff_id,
            booking_id=booking.id,
            status=BookingStatus.NO_SHOW,
        )
    )
    # The walk-in wants this very table (the hall would seat them too).
    walk_in_command = cabinet.manual(
        name="Walk-in", day="2026-10-05", time="19:00"
    ).model_copy(update={"resource_id": cabinet.table.id})
    start = Barrier(2)
    revert = cabinet.world.revert_booking_status()
    create = cabinet.world.create_manual_booking()

    def undo() -> str:
        start.wait()
        try:
            revert.run(
                RevertBookingStatusCommand(
                    business_id=cabinet.business.id,
                    actor_id=cabinet.staff_id,
                    booking_id=booking.id,
                    status=BookingStatus.NO_SHOW,
                )
            )
        except ConflictError as error:
            return str(error.reasons[0].code)
        return "ok"

    def walk_in() -> str:
        start.wait()
        try:
            create.run(walk_in_command)
        except ConflictError as error:
            return str(error.reasons[0].code) if error.reasons else "conflict"
        return "ok"

    with ThreadPoolExecutor(max_workers=2) as pool:
        undone = pool.submit(undo)
        booked = pool.submit(walk_in)
        return undone.result(timeout=10), booked.result(timeout=10)


def test_the_undo_and_a_new_booking_never_both_take_the_table() -> None:
    outcomes = {race_once() for _ in range(ROUNDS)}

    # Whoever takes the lock first wins; the other is refused with its reason.
    assert outcomes <= {("ok", "conflict"), ("ok", "taken"), ("slot_taken", "ok")}
    assert all(outcome.count("ok") == 1 for outcome in outcomes)
