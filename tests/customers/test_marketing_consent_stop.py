"""
A customer's STOP in a messenger, answered by the platform before the
assistant, takes their marketing consent back for good: START lifts the
opt-out, never the withdrawal.
"""

from datetime import timedelta

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.marketing_consent import (
    CURRENT_MARKETING_CONSENT_TEXT,
    MarketingConsentSource,
    MarketingConsentWithdrawal,
)
from app.schemas.domain.contacts import ContactDocument, MarketingConsent
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.scripted_turns import say, scripted


def only_contact(world: BrainWorld) -> ContactDocument:
    [contact] = world.contacts()
    return contact


def agree(world: BrainWorld) -> None:
    """The customer ticked the box of their booking's page."""

    def given(contact: ContactDocument) -> None:
        contact.marketing_consent = MarketingConsent(
            given_at=world.clock.wall_clock().now_unix(),
            source=MarketingConsentSource.BOOKING_PAGE,
            text_version=CURRENT_MARKETING_CONSENT_TEXT,
        )

    contact = only_contact(world)
    world.contact_repo.change_card(world.business.id, contact.id, given)


def test_stop_in_a_messenger_takes_the_consent_back_and_start_keeps_it_back() -> None:
    world = build_world(scripted(say("Hello! Shall I book a table?")))
    world.send("Hello")
    agree(world)
    assert only_contact(world).has_marketing_consent

    world.send("STOP")

    stopped = only_contact(world).marketing_consent
    assert stopped is not None
    assert stopped.withdrawal is MarketingConsentWithdrawal.STOP
    assert stopped.withdrawn_at is not None and stopped.withdrawn_by is None

    world.send("START")

    restarted = only_contact(world)
    assert restarted.opted_out_channels == []
    assert restarted.marketing_consent == stopped
    assert not restarted.has_marketing_consent


def test_a_stop_in_a_channel_already_stopped_takes_a_newer_consent_back() -> None:
    # The customer stopped, ticked the box again on a booking page, then
    # wrote STOP again in the same chat: the new consent is taken back, and
    # START does not bring it back.
    world = build_world(scripted(say("Hello! Shall I book a table?")))
    world.send("Hello")
    agree(world)
    world.send("STOP")
    first = only_contact(world).marketing_consent
    assert first is not None and first.withdrawn_at is not None
    first_withdrawn_at = first.withdrawn_at
    world.clock.advance(timedelta(minutes=1))
    agree(world)
    assert only_contact(world).has_marketing_consent

    world.send("STOP")

    contact = only_contact(world)
    second = contact.marketing_consent
    assert second is not None
    assert second.withdrawal is MarketingConsentWithdrawal.STOP
    assert second.withdrawn_at is not None
    assert second.withdrawn_at >= second.given_at > first_withdrawn_at
    assert contact_audit(world) == [AuditAction.UPDATE]

    world.send("START")

    assert not only_contact(world).has_marketing_consent


def test_a_repeated_stop_without_a_consent_writes_no_contact_change() -> None:
    world = build_world(scripted(say("Hello! Shall I book a table?")))
    world.send("Hello")
    world.send("STOP")

    world.send("STOP")

    assert only_contact(world).marketing_consent is None
    assert contact_audit(world) == []


def contact_audit(world: BrainWorld) -> list[AuditAction]:
    return [
        entry.action
        for entry in world.audit_log_repo.list_by_business(world.business.id)
        if str(entry.entity) == "contact"
    ]
