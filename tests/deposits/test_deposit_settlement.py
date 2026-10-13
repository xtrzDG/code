"""
A paid deposit when its booking ends: cancelled early enough under the
owner's policy it is to be refunded (staff are told, with the reference to
find it by); cancelled late or a no-show, the business keeps it; a staff
cancellation waits out the cabinet's undo window before it is settled.
"""

from datetime import timedelta

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.deposits import DepositStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.bookings import CancelBookingCommand
from app.schemas.dto.operations.bookings import (
    RevertBookingStatusCommand,
    UpdateBookingCommand,
)
from app.schemas.typings.deposits.prefixed_id import DepositRequestId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.deposits.deposit_settlement import STAFF_SETTLE_DELAY_SECONDS
from tests.deposits.deposit_world import DepositWorld


def paid_evening(
    refund_cutoff_hours: int = 24,
) -> tuple[DepositWorld, BookingDocument, DepositRequestId]:
    """Nino paid the deposit of Wednesday's evening (two days ahead)."""

    world = DepositWorld()
    world.take_deposits(refund_cutoff_hours=refund_cutoff_hours)
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    booking = world.big_table_booking(nino, chat)
    receipt = world.ask_deposit(nino, chat)
    assert receipt.issued is not None
    world.mark_paid(receipt.issued.request_id)
    return world, booking, receipt.issued.request_id


def customer_cancels(world: DepositWorld, booking: BookingDocument) -> None:
    world.cancel_booking().run(
        CancelBookingCommand(
            business_id=world.business.id,
            contact_id=booking.contact_id,
            booking_id=booking.id,
            language=LanguageTag("ru"),
        )
    )


def staff_set(
    world: DepositWorld, booking: BookingDocument, status: BookingStatus
) -> None:
    world.update_booking().run(
        UpdateBookingCommand(
            business_id=world.business.id,
            actor_id=world.owner_id,
            booking_id=booking.id,
            status=status,
        )
    )


def alert_texts(world: DepositWorld) -> list[str]:
    return [str(text) for _contact, text in world.notifier.sent]


def test_an_early_cancellation_is_to_be_refunded_and_staff_are_told() -> None:
    world, booking, request_id = paid_evening(refund_cutoff_hours=24)

    customer_cancels(world, booking)

    request = world.request(request_id)
    assert request.status is DepositStatus.REFUND_DUE
    assert request.settled_at is not None
    assert world.booking(booking.id).deposit_status is DepositStatus.REFUND_DUE
    assert any(str(request.reference) in text for text in alert_texts(world))


def test_a_late_cancellation_keeps_the_deposit() -> None:
    world, booking, request_id = paid_evening(refund_cutoff_hours=72)

    customer_cancels(world, booking)

    assert world.request(request_id).status is DepositStatus.KEPT
    assert not any(
        str(world.request(request_id).reference) in text for text in alert_texts(world)
    )


def test_a_staff_cancellation_is_settled_after_the_undo_window() -> None:
    world, booking, request_id = paid_evening(refund_cutoff_hours=24)

    staff_set(world, booking, BookingStatus.CANCELLED)
    world.sweep()

    waiting = world.request(request_id)
    assert waiting.status is DepositStatus.PAID
    assert waiting.settle_after is not None

    world.pass_minutes(STAFF_SETTLE_DELAY_SECONDS // 60 + 1)
    world.sweep()

    assert world.request(request_id).status is DepositStatus.REFUND_DUE


def test_an_undone_staff_cancellation_keeps_the_deposit_paid() -> None:
    world, booking, request_id = paid_evening()
    staff_set(world, booking, BookingStatus.CANCELLED)

    world.pass_minutes(2)
    world.revert_booking_status().run(
        RevertBookingStatusCommand(
            business_id=world.business.id,
            actor_id=world.owner_id,
            booking_id=booking.id,
            status=BookingStatus.CANCELLED,
        )
    )
    world.pass_minutes(STAFF_SETTLE_DELAY_SECONDS // 60 + 1)
    world.sweep()

    request = world.request(request_id)
    assert request.status is DepositStatus.PAID
    assert request.cancelled_at is None
    assert world.booking(booking.id).deposit_status is DepositStatus.PAID


def test_a_no_show_keeps_the_deposit() -> None:
    world, booking, request_id = paid_evening()
    starts = world.now_at + timedelta(
        seconds=int(booking.starts_at) - int(world.now()) // 1_000_000
    )
    world.clock.move_to(starts + timedelta(minutes=30))
    world.now_at = starts + timedelta(minutes=30)

    staff_set(world, booking, BookingStatus.NO_SHOW)
    world.pass_minutes(STAFF_SETTLE_DELAY_SECONDS // 60 + 1)
    world.sweep()

    assert world.request(request_id).status is DepositStatus.KEPT


def test_an_unpaid_deposit_of_a_cancelled_booking_is_dropped() -> None:
    world = DepositWorld()
    world.take_deposits()
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    booking = world.big_table_booking(nino, chat)
    receipt = world.ask_deposit(nino, chat)
    assert receipt.issued is not None

    customer_cancels(world, booking)
    world.pass_minutes(120)
    world.sweep()

    request = world.request(receipt.issued.request_id)
    assert request.status is DepositStatus.CANCELLED
    assert not [text for text in world.outbox_texts() if "напоминаем" in text]
