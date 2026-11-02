"""
A customer's STOP in a messenger, answered by the platform before the
assistant, takes their marketing consent back for good: START lifts the
opt-out, never the withdrawal.
"""

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
