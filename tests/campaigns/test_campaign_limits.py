"""What a campaign never does: write past STOP, a block or its cap, too often."""

from app.schemas.constants.campaigns import CampaignMessageStatus, CampaignSkipReason
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.contacts import ContactBlock, ContactDocument
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.privacy.suppressed_identities import contact_identities
from tests.campaigns.campaign_world import CampaignWorld

VISIT_STARTS: str = "2026-09-04T19:00:00+04:00"
VISIT_ENDS: str = "2026-09-04T21:00:00+04:00"


def guests_with_visits(world: CampaignWorld, count: int) -> list[ContactDocument]:
    guests: list[ContactDocument] = []
    for index in range(count):
        guest = world.guest(f"Guest {index}", "en")
        world.visit(guest, VISIT_STARTS, VISIT_ENDS)
        guests.append(guest)
    return guests


def skip_reason(world: CampaignWorld, guest: ContactDocument) -> object:
    [message] = world.messages_of(guest)
    assert message.status is CampaignMessageStatus.SKIPPED
    return message.skip_reason


def test_stop_the_suppression_list_and_a_block_always_win() -> None:
    world = CampaignWorld()
    world.enable()
    said_stop, suppressed, blocked = guests_with_visits(world, 3)
    said_stop.opted_out_channels = [ChannelKind.TELEGRAM]
    world.contact_repo.save(said_stop)
    world.suppression_list.suppress(
        world.business.id,
        contact_identities(suppressed),
        world.clock.now_microseconds(),
    )

    def block(stored: ContactDocument) -> None:
        stored.block = ContactBlock(
            blocked_at=world.clock.now_microseconds(), blocked_by=UserId()
        )

    world.contact_repo.change_card(world.business.id, blocked.id, block)

    assert int(world.run_campaigns().processed_count) == 0
    for guest in (said_stop, suppressed, blocked):
        assert skip_reason(world, guest) is CampaignSkipReason.OPTED_OUT
    assert world.outbox_texts() == []


def test_a_guest_in_no_connected_messenger_is_skipped_with_the_reason() -> None:
    world = CampaignWorld()
    world.enable()
    phone_only = world.add_contact(world.business, "Phone only", "+995599111222")
    world.visit(phone_only, VISIT_STARTS, VISIT_ENDS)

    world.run_campaigns()

    assert skip_reason(world, phone_only) is CampaignSkipReason.NO_CHANNEL


def test_the_monthly_cap_stops_the_month() -> None:
    world = CampaignWorld()
    world.enable(monthly_cap=2)
    guests = guests_with_visits(world, 3)

    first = world.run_campaigns()
    again = world.run_campaigns()

    assert (int(first.processed_count), int(again.processed_count)) == (2, 0)
    written = [guest for guest in guests if world.messages_of(guest)]
    assert len(written) == 2
    assert len(world.outbox_texts()) == 2


def test_a_segment_audience_writes_to_its_members_only() -> None:
    world = CampaignWorld()
    vip, regular = guests_with_visits(world, 2)
    world.make_vip(vip)
    world.enable(segment=world.vip_segment())

    world.run_campaigns()

    assert len(world.messages_of(vip)) == 1
    assert world.messages_of(regular) == []


def test_a_guest_hears_from_the_campaign_at_most_once_in_two_weeks() -> None:
    world = CampaignWorld()
    world.enable(delay_days=30)
    nino = world.guest("Nino", "ru")
    world.visit(nino, "2026-09-02T19:00:00+04:00", "2026-09-02T21:00:00+04:00")
    world.run_campaigns()
    world.visit(nino, VISIT_STARTS, VISIT_ENDS)

    world.run_campaigns()

    assert len(world.messages_of(nino)) == 1
