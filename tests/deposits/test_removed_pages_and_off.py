"""
A deposit already asked keeps its link: after the owner removed its
payment page (the page is retired, out of their list, until no hold can
still need it) and after the owner turned deposits off (its hold still
stands). A new deposit never uses a removed page. A reminder counts as
sent only once it was queued. The first turn-on is noted once.
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.deposits import (
    DepositExemption,
    PaymentLinkKind,
    PaymentLinkOutcome,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.deposits import PaymentLink
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.deposits.constrained_strings import (
    PaymentLinkAddress,
    PaymentLinkLabel,
)
from app.schemas.typings.deposits.prefixed_id import DepositRequestId
from app.schemas.typings.deposits.strings import PaymentLinkHost, PaymentLinkPreview
from app.utilities.deposits.payment_pages import LONGEST_HOLD_MINUTES
from app.utilities.privacy.suppressed_identities import contact_identities
from tests.deposits.deposit_owner_actions import (
    remove_page,
    stored_settings,
    switch_deposits,
)
from tests.deposits.deposit_store import PAGE
from tests.deposits.deposit_world import DepositWorld

LINK: str = "https://pay.example.com/deposit?sum=120.00"
REMINDER: str = "напоминаем"


def waiting_deposit(
    world: DepositWorld,
) -> tuple[ContactDocument, ConversationDocument, DepositRequestId]:
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    world.big_table_booking(nino, chat)
    receipt = world.ask_deposit(nino, chat)
    assert receipt.issued is not None
    return nino, chat, receipt.issued.request_id


def second_page(world: DepositWorld) -> PaymentLink:
    settings = stored_settings(world)
    page = PaymentLink(
        label=PaymentLinkLabel("Card"),
        kind=PaymentLinkKind.TEMPLATE,
        address=PaymentLinkAddress(PAGE),
        host=PaymentLinkHost("pay.example.com"),
        preview=PaymentLinkPreview(PAGE),
        added_at=world.now(),
    )
    settings.payment_links.append(page)
    world.deposit_settings_repo.save(settings)
    return page


def test_a_removed_page_still_sends_the_waiting_deposits_link() -> None:
    world = DepositWorld()
    page = world.take_deposits().payment_links[0]
    nino, chat, request_id = waiting_deposit(world)

    view = remove_page(world, page.id)
    again = world.ask_deposit(nino, chat)

    assert view.payment_links == []
    assert again.outcome is PaymentLinkOutcome.SENT
    assert again.issued is not None and again.issued.request_id == request_id
    assert LINK in str(again.issued.line)


def test_the_reminder_goes_with_the_removed_pages_link() -> None:
    world = DepositWorld()
    page = world.take_deposits(hold_minutes=60).payment_links[0]
    _nino, _chat, request_id = waiting_deposit(world)
    remove_page(world, page.id)

    world.pass_minutes(30)
    world.sweep()

    reminders = [text for text in world.outbox_texts() if REMINDER in text]
    assert len(reminders) == 1 and LINK in reminders[0]
    assert world.request(request_id).reminder_sent_at == world.now()


def test_a_reminder_that_could_not_go_is_not_marked_sent() -> None:
    world = DepositWorld()
    world.take_deposits(hold_minutes=60)
    nino, _chat, request_id = waiting_deposit(world)
    world.suppression_list.suppress(
        world.business.id, contact_identities(nino), world.now()
    )

    world.pass_minutes(30)
    world.sweep()
    world.pass_minutes(1)
    world.sweep()

    request = world.request(request_id)
    assert request.reminder_sent_at is None
    # Claimed once: the sweep does not try it again every minute.
    assert request.reminder_due_at is None
    assert world.outbox_texts() == []


def test_a_new_deposit_never_uses_a_removed_page() -> None:
    world = DepositWorld()
    page = world.take_deposits().payment_links[0]
    remove_page(world, page.id)

    with pytest.raises(ValidationFailedError) as raised:
        waiting_deposit(world)

    assert [str(reason.code) for reason in raised.value.reasons] == ["no_payment_link"]


@pytest.mark.parametrize(
    ("minutes_later", "kept"),
    [(LONGEST_HOLD_MINUTES - 1, 2), (LONGEST_HOLD_MINUTES + 1, 1)],
)
def test_a_retired_page_goes_for_good_after_the_longest_hold(
    minutes_later: int, kept: int
) -> None:
    world = DepositWorld()
    first = world.take_deposits().payment_links[0]
    second = second_page(world)
    remove_page(world, first.id)

    world.pass_minutes(minutes_later)
    remove_page(world, second.id)

    retired = stored_settings(world).retired_payment_links
    assert len(retired) == kept
    assert retired[-1].link.id == second.id


def test_turning_deposits_off_still_sends_the_waiting_deposit() -> None:
    world = DepositWorld()
    world.take_deposits()
    nino, chat, request_id = waiting_deposit(world)

    switch_deposits(world, is_enabled=False)
    again = world.ask_deposit(nino, chat)

    assert again.outcome is PaymentLinkOutcome.SENT
    assert again.issued is not None and again.issued.request_id == request_id
    assert LINK in str(again.issued.line)


def test_no_new_deposit_once_deposits_are_off() -> None:
    world = DepositWorld()
    world.take_deposits()
    switch_deposits(world, is_enabled=False)
    tamar = world.guest("Tamar", "ka")
    chat = world.telegram_conversation(tamar)
    world.big_table_booking(tamar, chat)

    receipt = world.ask_deposit(tamar, chat)

    assert receipt.outcome is PaymentLinkOutcome.NOT_REQUIRED
    assert receipt.exemption is DepositExemption.DEPOSITS_OFF


def test_the_first_turn_on_is_noted_once() -> None:
    world = DepositWorld()
    world.take_deposits(is_enabled=False)
    first_on: Microseconds = world.now()

    switch_deposits(world, is_enabled=True)
    world.pass_minutes(60)
    switch_deposits(world, is_enabled=False)
    switch_deposits(world, is_enabled=True)

    assert stored_settings(world).enabled_at == first_on
