"""
"Paid" in the cabinet: staff mark the money they saw in their merchant
account, the held booking is confirmed, the mark is audited and marking
again changes nothing. The guest's reminder goes once through the outbox
halfway through the hold, never after the payment and never to a guest
who said STOP.
"""

import pytest

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.deposits import DepositStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.deposits.prefixed_id import DepositRequestId
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.privacy.suppressed_identities import contact_identities
from tests.deposits.deposit_world import DepositWorld

REMINDER: str = "напоминаем"


def waiting_deposit(world: DepositWorld) -> tuple[DepositRequestId, str]:
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    booking = world.big_table_booking(nino, chat)
    receipt = world.ask_deposit(nino, chat)
    assert receipt.issued is not None
    return receipt.issued.request_id, str(booking.id)


def test_paid_confirms_the_booking_and_is_audited() -> None:
    world = DepositWorld()
    world.take_deposits()
    request_id, _booking_id = waiting_deposit(world)
    world.pass_minutes(10)

    view = world.mark_paid(request_id)

    assert view.status is DepositStatus.PAID
    assert view.marked_paid_by == world.owner_id
    assert view.payment_link_label is not None
    request = world.request(request_id)
    assert request.booking_id is not None
    booking = world.booking(request.booking_id)
    assert booking.status is BookingStatus.CONFIRMED
    assert booking.deposit_status is DepositStatus.PAID
    entries = world.audit_repo.list_by_business(world.business.id)
    assert any(
        str(entry.entity) == "deposit_request"
        and str(entry.entity_id) == str(request_id)
        for entry in entries
    )


def test_marking_paid_twice_changes_nothing() -> None:
    world = DepositWorld()
    world.take_deposits()
    request_id, _booking_id = waiting_deposit(world)
    first = world.mark_paid(request_id)
    world.pass_minutes(3)

    second = world.mark_paid(request_id)

    assert second.paid_at == first.paid_at
    assert second.status is DepositStatus.PAID


def test_staff_may_mark_paid_and_strangers_may_not() -> None:
    world = DepositWorld()
    staff_id = UserId()
    world.business.members.append(
        world.business.members[0].model_copy(
            update={"user_id": staff_id, "role": BusinessMemberRole.STAFF}
        )
    )
    world.business_repo.save(world.business)
    world.take_deposits()
    request_id, _booking_id = waiting_deposit(world)

    with pytest.raises(NotFoundError):
        world.mark_paid(request_id, user_id=UserId())
    assert world.request(request_id).status is DepositStatus.AWAITING

    view = world.mark_paid(request_id, user_id=staff_id)

    assert view.marked_paid_by == staff_id


def test_the_reminder_goes_once_halfway_through_the_hold() -> None:
    world = DepositWorld()
    world.take_deposits(hold_minutes=60)
    waiting_deposit(world)

    world.pass_minutes(29)
    world.sweep()
    assert [text for text in world.outbox_texts() if REMINDER in text] == []

    world.pass_minutes(1)
    world.sweep()
    world.pass_minutes(1)
    world.sweep()

    reminders = [text for text in world.outbox_texts() if REMINDER in text]
    assert len(reminders) == 1
    assert "https://pay.example.com/deposit?sum=120.00" in reminders[0]


def test_a_paid_deposit_gets_no_reminder() -> None:
    world = DepositWorld()
    world.take_deposits(hold_minutes=60)
    request_id, _booking_id = waiting_deposit(world)
    world.mark_paid(request_id)

    world.pass_minutes(45)
    world.sweep()

    assert world.outbox_texts() == []


def test_a_guest_who_said_stop_gets_no_reminder_but_the_hold_still_ends() -> None:
    world = DepositWorld()
    world.take_deposits(hold_minutes=60)
    request_id, _booking_id = waiting_deposit(world)
    nino = world.contact_repo.get(
        world.business.id, world.request(request_id).contact_id
    )
    assert nino is not None
    world.suppression_list.suppress(
        world.business.id, contact_identities(nino), world.now()
    )

    world.pass_minutes(30)
    world.sweep()
    world.pass_minutes(30)
    world.sweep()

    assert world.outbox_texts() == []
    assert world.request(request_id).status is DepositStatus.EXPIRED
