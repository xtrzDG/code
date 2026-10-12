"""
send_payment_link: the amount comes from the owner's policy and the link
from the owner's page, never from the model; the booking is held for the
deposit (PENDING while the booking_deposits gate is closed); asking again
sends the same deposit, and a booking the policy does not cover needs none.
"""

import pytest

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.deposits import (
    DepositExemption,
    DepositRule,
    DepositStatus,
    PaymentLinkOutcome,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.utilities.deposits.booking_deposit_state import held_status
from tests.deposits.deposit_world import DepositWorld


def test_the_link_carries_the_policy_amount_and_the_reference() -> None:
    world = DepositWorld()
    world.take_deposits(rule=DepositRule.PER_GUEST, amount_minor=2000)
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    world.big_table_booking(nino, chat, party_size=6)

    receipt = world.ask_deposit(nino, chat)

    assert receipt.outcome is PaymentLinkOutcome.SENT
    assert receipt.issued is not None and receipt.reference is not None
    assert int(receipt.issued.amount.amount_minor) == 12000
    line = str(receipt.issued.line)
    assert "https://pay.example.com/deposit?sum=120.00&ref=" in line
    assert str(receipt.reference) in line
    assert "120,00" in line and "13:00" in line
    request = world.request(receipt.issued.request_id)
    assert request.status is DepositStatus.AWAITING
    assert int(request.amount_minor) == 12000
    assert str(request.currency_code) == "GEL"


def test_the_booking_is_held_with_its_deposit_on_its_row() -> None:
    world = DepositWorld()
    world.take_deposits()
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    booking = world.big_table_booking(nino, chat)

    receipt = world.ask_deposit(nino, chat)

    held = world.booking(booking.id)
    assert held.status is held_status()
    # The gate is closed in this release: the stored status stays PENDING.
    assert held.status is BookingStatus.PENDING
    assert held.deposit is not None and receipt.issued is not None
    assert held.deposit.request_id == receipt.issued.request_id
    assert held.deposit_status is DepositStatus.AWAITING


def test_asking_again_sends_the_same_deposit() -> None:
    world = DepositWorld()
    world.take_deposits()
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    booking = world.big_table_booking(nino, chat)

    first = world.ask_deposit(nino, chat)
    world.pass_minutes(5)
    second = world.ask_deposit(nino, chat)

    assert first.issued is not None and second.issued is not None
    assert first.issued.request_id == second.issued.request_id
    assert first.reference == second.reference
    requests = world.deposit_request_repo.list_of_booking(world.business.id, booking.id)
    assert len(requests) == 1


def test_a_small_party_needs_no_deposit() -> None:
    world = DepositWorld()
    world.take_deposits(min_party_size=6)
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    booking = world.big_table_booking(nino, chat, party_size=4)

    receipt = world.ask_deposit(nino, chat)

    assert receipt.outcome is PaymentLinkOutcome.NOT_REQUIRED
    assert receipt.exemption is DepositExemption.SMALL_PARTY
    assert receipt.issued is None
    assert world.booking(booking.id).deposit is None


def test_no_deposit_while_deposits_are_off() -> None:
    world = DepositWorld()
    world.take_deposits(is_enabled=False)
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    world.big_table_booking(nino, chat)

    receipt = world.ask_deposit(nino, chat)

    assert receipt.outcome is PaymentLinkOutcome.NOT_REQUIRED
    assert receipt.exemption is DepositExemption.DEPOSITS_OFF


def test_a_booking_of_another_guest_is_refused() -> None:
    world = DepositWorld()
    world.take_deposits()
    nino = world.guest("Nino", "ru")
    giorgi = world.guest("Giorgi", "ka")
    nino_chat = world.telegram_conversation(nino)
    giorgi_chat = world.telegram_conversation(giorgi)
    giorgis = world.big_table_booking(giorgi, giorgi_chat)

    with pytest.raises(NotFoundError):
        world.ask_deposit(nino, nino_chat, booking_id=giorgis.id)

    assert world.booking(giorgis.id).deposit is None


def test_a_paid_deposit_is_not_asked_again() -> None:
    world = DepositWorld()
    world.take_deposits()
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    world.big_table_booking(nino, chat)
    first = world.ask_deposit(nino, chat)
    assert first.issued is not None
    world.mark_paid(first.issued.request_id)

    again = world.ask_deposit(nino, chat)

    assert again.outcome is PaymentLinkOutcome.ALREADY_PAID
    assert again.issued is None


def test_the_line_speaks_the_guests_language() -> None:
    world = DepositWorld()
    world.take_deposits(rule=DepositRule.FIXED, amount_minor=5000, min_party_size=None)
    tamar = world.guest("Tamar", "ka")
    chat = world.telegram_conversation(tamar)
    world.big_table_booking(tamar, chat, party_size=2)

    receipt = world.ask_deposit(tamar, chat)

    assert receipt.issued is not None
    line = str(receipt.issued.line)
    assert "50,00" in line
    assert any("ა" <= letter <= "ჿ" for letter in line)
