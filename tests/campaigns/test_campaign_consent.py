"""
Campaign messages are marketing: they go only to a guest whose marketing
consent is recorded and not taken back (Codice privacy art. 130).
"""

import pytest

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.campaigns import RebookingRuleKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.marketing_consent import MarketingConsentWithdrawal
from app.schemas.domain.contacts import ContactDocument
from tests.campaigns.campaign_world import CampaignWorld

VISIT_STARTS: str = "2026-09-04T19:00:00+04:00"
VISIT_ENDS: str = "2026-09-04T21:00:00+04:00"
ARRIVAL_STARTS: str = "2026-10-06T19:00:00+04:00"
ARRIVAL_ENDS: str = "2026-10-06T21:00:00+04:00"


def due_guest(
    world: CampaignWorld, rule_kind: RebookingRuleKind, has_consent: bool
) -> ContactDocument:
    guest = world.guest("Giulia", "en", has_consent=has_consent)
    if rule_kind is RebookingRuleKind.PRE_ARRIVAL:
        world.visit(guest, ARRIVAL_STARTS, ARRIVAL_ENDS, BookingStatus.CONFIRMED)
    else:
        world.visit(guest, VISIT_STARTS, VISIT_ENDS)
    return guest


@pytest.mark.parametrize("rule_kind", list(RebookingRuleKind))
def test_a_guest_without_consent_gets_no_campaign_message(
    rule_kind: RebookingRuleKind,
) -> None:
    world = CampaignWorld()
    is_arrival: bool = rule_kind is RebookingRuleKind.PRE_ARRIVAL
    world.enable(rule_kind, delay_days=2 if is_arrival else 30)
    guest = due_guest(world, rule_kind, has_consent=False)

    assert int(world.run_campaigns().processed_count) == 0
    assert world.outbox_texts() == []
    # Nothing is decided for them: a consent given while due still counts.
    assert world.messages_of(guest) == []


def test_a_consent_given_while_the_visit_is_due_brings_the_invitation() -> None:
    world = CampaignWorld()
    world.enable()
    guest = due_guest(world, RebookingRuleKind.REBOOK, has_consent=False)
    world.run_campaigns()

    world.agree(guest)

    assert int(world.run_campaigns().processed_count) == 1
    assert len(world.outbox_texts()) == 1


def test_a_consent_taken_back_stops_the_invitations() -> None:
    world = CampaignWorld()
    world.enable()
    guest = due_guest(world, RebookingRuleKind.REBOOK, has_consent=True)

    def withdraw(stored: ContactDocument) -> None:
        assert stored.marketing_consent is not None
        stored.marketing_consent = stored.marketing_consent.withdrawn(
            world.clock.now_microseconds(), MarketingConsentWithdrawal.BOOKING_PAGE
        )

    world.contact_repo.change_card(world.business.id, guest.id, withdraw)

    assert int(world.run_campaigns().processed_count) == 0
    assert world.outbox_texts() == []


def test_a_stop_takes_the_consent_back_for_good() -> None:
    world = CampaignWorld()
    world.enable()
    guest = due_guest(world, RebookingRuleKind.REBOOK, has_consent=True)
    stored = world.contact_repo.get(world.business.id, guest.id)
    assert stored is not None
    stored.opted_out_channels = [ChannelKind.TELEGRAM]
    world.contact_repo.save(stored)
    # START lifts the opt-out, never the withdrawal of the consent.
    stored.opted_out_channels = []
    world.contact_repo.save(stored)

    after = world.contact_repo.get(world.business.id, guest.id)

    assert after is not None and after.marketing_consent is not None
    assert after.marketing_consent.withdrawal is MarketingConsentWithdrawal.STOP
    assert not after.has_marketing_consent
    assert int(world.run_campaigns().processed_count) == 0
