"""
The owner blocks a customer: the assistant answers nothing they send and
nothing unrequested reaches them (reminders, text-backs, feedback
requests) until the owner unblocks them.
"""

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversation_engine import TurnGate
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
)
from app.schemas.typings.conversations.constrained_integers import (
    ContactMessageLimit,
    InjectionFlagLimit,
)
from app.use_cases.conversations.turns.turn_gate import choose_turn_gate
from app.utilities.privacy.messaging_suppression import is_messaging_suppressed
from tests.customers.customer_bed import CustomerBed
from tests.privacy.suppression_doubles import build_suppression_list


def gate_for(
    bed: CustomerBed, contact: ContactDocument, conversation: ConversationDocument
) -> TurnGate:
    testbed = bed.customers.testbed
    return choose_turn_gate(
        conversation_repo=testbed.conversation_repo,
        message_repo=testbed.message_repo,
        contact_message_limit=ContactMessageLimit(30),
        business=bed.customers.business,
        contact=contact,
        conversation=conversation,
        now=testbed.clock.now_microseconds(),
        injection_flag=None,
        injection_flag_limit=InjectionFlagLimit(5),
    )


def reload(bed: CustomerBed, contact: ContactDocument) -> ContactDocument:
    stored = bed.customers.testbed.contact_repo.get(contact.business_id, contact.id)
    assert stored is not None
    return stored


def test_a_blocked_customer_gets_no_reply_in_any_channel() -> None:
    bed = CustomerBed()
    giorgi = bed.customers.giorgi
    assert gate_for(bed, giorgi.contact, giorgi.chat_conversation) is TurnGate.ANSWER

    card = bed.block(giorgi.contact.id)

    blocked = reload(bed, giorgi.contact)
    assert card.is_blocked is True
    assert card.blocked_at == bed.customers.testbed.clock.now_microseconds()
    for conversation in (giorgi.chat_conversation, giorgi.phone_conversation):
        assert gate_for(bed, blocked, conversation) is TurnGate.BLOCKED_SILENCE


def test_the_owners_test_chat_still_answers_a_blocked_contact() -> None:
    bed = CustomerBed()
    giorgi = bed.customers.giorgi
    bed.block(giorgi.contact.id)
    sandbox = giorgi.chat_conversation.model_copy(update={"is_sandbox": True})

    assert gate_for(bed, reload(bed, giorgi.contact), sandbox) is TurnGate.ANSWER


def test_nothing_unrequested_reaches_a_blocked_customer() -> None:
    bed = CustomerBed()
    nino = bed.customers.nino.contact
    suppression_list = build_suppression_list()
    business_id = bed.customers.business.id
    assert not is_messaging_suppressed(suppression_list, business_id, nino)

    bed.block(nino.id)

    assert is_messaging_suppressed(suppression_list, business_id, reload(bed, nino))
    bed.block(nino.id, is_blocked=False)
    assert not is_messaging_suppressed(suppression_list, business_id, reload(bed, nino))


def test_blocking_again_keeps_the_first_moment_and_unblocking_clears_it() -> None:
    bed = CustomerBed()
    clock = bed.customers.testbed.clock
    nino = bed.customers.nino.contact
    first = bed.block(nino.id)
    clock.advance(3600)

    again = bed.block(nino.id)
    unblocked = bed.block(nino.id, is_blocked=False)

    assert again.blocked_at == first.blocked_at
    assert (unblocked.is_blocked, unblocked.blocked_at) == (False, None)
    stored = reload(bed, nino)
    assert (stored.block, stored.is_blocked) == (None, False)
    entries = bed.customers.testbed.audit_log_repo.list_by_business(
        bed.customers.business.id
    )
    assert [(entry.action, entry.entity) for entry in entries[-3:]] == [
        (AuditAction.UPDATE, "contact")
    ] * 3
    assert entries[-1].actor_id == bed.owner_id


def test_only_owners_block_customers() -> None:
    bed = CustomerBed()
    giorgi = bed.customers.giorgi.contact

    with pytest.raises(AccessDeniedError):
        bed.block(giorgi.id, user_id=bed.staff_id)

    assert reload(bed, giorgi).block is None


def test_unknown_and_erased_customers_cannot_be_blocked() -> None:
    bed = CustomerBed()
    with pytest.raises(NotFoundError):
        bed.block(bed.customers.foreign.contact.id)

    giorgi = bed.customers.giorgi.contact
    bed.customers.testbed.contact_repo.save(
        ContactDocument(
            id=giorgi.id,
            business_id=giorgi.business_id,
            erased_at=bed.customers.testbed.clock.now_microseconds(),
        )
    )
    with pytest.raises(ConflictError):
        bed.block(giorgi.id)


def test_a_card_change_keeps_the_block() -> None:
    bed = CustomerBed()
    giorgi = bed.customers.giorgi.contact
    bed.block(giorgi.id)

    card = bed.tag(giorgi.id, "spam", user_id=bed.staff_id)

    assert card.is_blocked is True
    assert reload(bed, giorgi).block is not None
