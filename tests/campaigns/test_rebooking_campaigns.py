"""The hourly job: invitations back, recalls, pre-arrival notes, attribution."""

from app.schemas.constants.bookings import BookingOrigin, BookingStatus
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.campaigns import CampaignMessageStatus, RebookingRuleKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.bookings import CreateBookingCommand
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.constrained_strings import (
    LocalDate,
    LocalTimeOfDay,
)
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.campaigns.campaign_world import CampaignWorld

# Monday 5 October 2026, 12:00 in Tbilisi: 30 days back is 5 September.
VISIT_STARTS: str = "2026-09-04T19:00:00+04:00"
VISIT_ENDS: str = "2026-09-04T21:00:00+04:00"


def test_a_visit_thirty_days_ago_gets_one_invitation_back() -> None:
    world = CampaignWorld()
    world.enable()
    nino = world.guest("Nino", "ru")
    visit = world.visit(nino, VISIT_STARTS, VISIT_ENDS)

    first = world.run_campaigns()
    second = world.run_campaigns()

    assert (int(first.processed_count), int(second.processed_count)) == (1, 0)
    [message] = world.messages_of(nino)
    assert message.status is CampaignMessageStatus.SENT
    assert message.anchor_booking_id == visit.id
    assert message.channel is ChannelKind.TELEGRAM
    assert str(message.month) == "2026-10"
    [text] = world.outbox_texts()
    assert text.startswith("Salobie Bia:") and "СТОП" in text


def test_a_guest_who_already_booked_again_is_not_invited() -> None:
    world = CampaignWorld()
    world.enable()
    nino = world.guest("Nino", "ru")
    world.visit(nino, VISIT_STARTS, VISIT_ENDS)
    world.visit(
        nino,
        "2026-10-09T19:00:00+04:00",
        "2026-10-09T21:00:00+04:00",
        status=BookingStatus.CONFIRMED,
    )

    world.run_campaigns()

    assert world.messages_of(nino) == []
    assert world.outbox_texts() == []


def test_a_recent_or_a_cancelled_visit_is_not_written_about() -> None:
    world = CampaignWorld()
    world.enable()
    recent = world.guest("Recent", "en")
    world.visit(recent, "2026-09-20T19:00:00+04:00", "2026-09-20T21:00:00+04:00")
    cancelled = world.guest("Cancelled", "en")
    world.visit(cancelled, VISIT_STARTS, VISIT_ENDS, status=BookingStatus.CANCELLED)

    assert int(world.run_campaigns().processed_count) == 0


def test_a_campaign_that_is_off_or_a_business_not_live_writes_nothing() -> None:
    world = CampaignWorld()
    nino = world.guest("Nino", "ru")
    world.visit(nino, VISIT_STARTS, VISIT_ENDS)

    world.enable(is_enabled=False)
    assert int(world.run_campaigns().processed_count) == 0

    world.enable()
    world.business.status = BusinessStatus.PAUSED
    world.business_repo.save(world.business)
    assert int(world.run_campaigns().processed_count) == 0


def test_a_recall_says_a_regular_check_is_due() -> None:
    world = CampaignWorld()
    world.enable(RebookingRuleKind.RECALL, delay_days=30)
    tamar = world.guest("Tamar", "en")
    world.visit(tamar, VISIT_STARTS, VISIT_ENDS)

    world.run_campaigns()

    [text] = world.outbox_texts()
    assert "regular check-up" in text and "STOP" in text


def test_a_pre_arrival_note_names_the_day_of_the_arrival() -> None:
    world = CampaignWorld()
    world.enable(RebookingRuleKind.PRE_ARRIVAL, delay_days=2)
    guest = world.guest("Emma", "en")
    world.visit(
        guest,
        "2026-10-06T19:00:00+04:00",
        "2026-10-06T21:00:00+04:00",
        status=BookingStatus.CONFIRMED,
    )
    tonight = world.guest("Tonight", "en")
    world.visit(
        tonight,
        "2026-10-05T20:00:00+04:00",
        "2026-10-05T22:00:00+04:00",
        status=BookingStatus.CONFIRMED,
    )

    world.run_campaigns()

    [text] = world.outbox_texts()
    assert "Tuesday, October 6, 2026" in text
    assert world.messages_of(tonight) == []


def test_a_guest_who_books_after_the_invitation_counts_for_the_campaign() -> None:
    world = CampaignWorld()
    world.enable()
    nino = world.guest("Nino", "ru")
    world.visit(nino, VISIT_STARTS, VISIT_ENDS)
    world.run_campaigns()

    result = world.create_booking().run(
        CreateBookingCommand(
            business_id=world.business.id,
            contact_id=nino.id,
            contact_name=ContactName("Nino"),
            date=LocalDate("2026-10-08"),
            time=LocalTimeOfDay("19:00"),
            party_size=PartySize(2),
            source_channel=ChannelKind.TELEGRAM,
            language=LanguageTag("ru"),
        )
    )

    booking = world.booking_repo.get(world.business.id, result.booking.id)
    assert booking is not None and booking.origin is BookingOrigin.CAMPAIGN
    [message] = world.messages_of(nino)
    assert message.status is CampaignMessageStatus.BOOKED
    assert message.booking_id == booking.id
