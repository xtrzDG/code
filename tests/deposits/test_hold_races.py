"""
The hold's end against "Paid", decided under the business's booking lock:
whichever comes first wins and the other sees it; two sweeps at once
release a place once and tell the guest once.
"""

import threading
from collections.abc import Callable
from functools import partial

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.deposits import DepositStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.deposits.prefixed_id import DepositRequestId
from tests.deposits.deposit_world import DepositWorld

ROUNDS: int = 12


def run_together(*actions: Callable[[], object]) -> list[object]:
    """Start the actions at the same moment; their results or errors, in order."""

    barrier = threading.Barrier(len(actions))
    results: list[object] = [None] * len(actions)

    def run(index: int, action: Callable[[], object]) -> None:
        barrier.wait()
        try:
            results[index] = action()
        except ApplicationError as error:
            results[index] = error

    threads = [
        threading.Thread(target=run, args=(index, action))
        for index, action in enumerate(actions)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    return results


def held_evening() -> tuple[DepositWorld, BookingDocument, DepositRequestId]:
    """Nino's evening held for her deposit; the hour of the hold has passed."""

    world = DepositWorld()
    world.take_deposits(hold_minutes=60)
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    booking = world.big_table_booking(nino, chat)
    receipt = world.ask_deposit(nino, chat)
    assert receipt.issued is not None
    world.pass_minutes(60)
    return world, booking, receipt.issued.request_id


def test_paid_and_the_hold_running_out_never_both_win() -> None:
    outcomes: set[str] = set()
    for _ in range(ROUNDS):
        world, booking, request_id = held_evening()

        paid, _swept = run_together(partial(world.mark_paid, request_id), world.sweep)

        request = world.request(request_id)
        stored = world.booking(booking.id)
        if isinstance(paid, ConflictError):
            outcomes.add("released")
            assert request.status is DepositStatus.EXPIRED
            assert stored.status is BookingStatus.CANCELLED
            assert stored.deposit_status is DepositStatus.EXPIRED
        else:
            outcomes.add("paid")
            assert request.status is DepositStatus.PAID
            assert stored.status is BookingStatus.CONFIRMED
            assert stored.deposit_status is DepositStatus.PAID
            assert len(world.outbox_texts()) <= 1  # at most the reminder

    assert outcomes <= {"released", "paid"}


def test_paid_after_the_release_is_refused_with_status_changed() -> None:
    world, booking, request_id = held_evening()
    world.sweep()

    try:
        world.mark_paid(request_id)
    except ConflictError as error:
        codes = [str(reason.code) for reason in error.reasons]
        assert codes == ["status_changed"]
    else:
        raise AssertionError("A released deposit was marked paid.")

    assert world.booking(booking.id).status is BookingStatus.CANCELLED


def test_two_sweeps_release_the_place_once() -> None:
    for _ in range(ROUNDS):
        world, booking, request_id = held_evening()

        run_together(world.sweep, world.sweep)

        assert world.request(request_id).status is DepositStatus.EXPIRED
        assert world.booking(booking.id).status is BookingStatus.CANCELLED
        released = [
            text for text in world.outbox_texts() if "не смогли сохранить" in text
        ]
        assert len(released) == 1


def test_a_hold_never_outlives_the_booking_start() -> None:
    world = DepositWorld()
    world.take_deposits(hold_minutes=1440)
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    # Tonight at 19:00 local: the hold ends at the start, not a day later.
    booking = world.big_table_booking(nino, chat, day="2026-10-05")

    receipt = world.ask_deposit(nino, chat)

    assert receipt.issued is not None
    request = world.request(receipt.issued.request_id)
    assert int(request.hold_expires_at) == int(booking.starts_at) * 1_000_000
