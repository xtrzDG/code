"""The conversation feed's paging, filters and search, and the card's linked items."""

from app.schemas.constants.bookings import BookingStatus, LeadType, ResourceKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
    ResourceCapacity,
)
from app.schemas.typings.bookings.strings import LeadDetails, ResourceName
from app.schemas.typings.handoffs.strings import HandoffSummary
from tests.brain.brain_world import build_world
from tests.brain.cabinet_http import bearer
from tests.brain.conversation_cabinet_helpers import Cabinet, seed_feed
from tests.brain.scripted_turns import say, scripted


def test_feed_pages_by_the_latest_message() -> None:
    world = build_world(scripted(*(say(f"Answer {n}") for n in range(4))))
    seed_feed(world)
    cabinet = Cabinet(world)

    first = cabinet.feed(limit="2")
    second = cabinet.feed(limit="2", cursor=first["next_cursor"])

    assert [row["contact_name"] for row in first["items"]] == ["Giorgi", "José"]
    assert [row["contact_name"] for row in second["items"]] == ["Ниноʼ Беридзе"]
    assert second["next_cursor"] is None


def test_feed_filters_by_status_channel_and_local_period() -> None:
    world = build_world(scripted(*(say(f"Answer {n}") for n in range(4))))
    seed_feed(world)
    cabinet = Cabinet(world)

    assert cabinet.names(status="handoff") == ["Ниноʼ Беридзе"]
    assert cabinet.names(channel="telegram") == ["José"]
    # The world starts on 2026-10-01 at 14:00 in Tbilisi.
    assert cabinet.names(**{"from": "2026-10-02", "to": "2026-10-02"}) == ["José"]
    assert cabinet.names(**{"from": "2026-10-02"}) == ["Giorgi", "José"]
    assert cabinet.names(to="2026-10-01") == ["Ниноʼ Беридзе"]
    assert len(cabinet.feed(include_sandbox="true")["items"]) == 4


def test_search_finds_names_phones_and_words_in_any_script() -> None:
    world = build_world(scripted(*(say(f"Answer {n}") for n in range(4))))
    seed_feed(world)
    cabinet = Cabinet(world)

    assert cabinet.names(search="нино") == ["Ниноʼ Беридзе"]
    assert cabinet.names(search="jose") == ["José"]
    assert cabinet.names(search="599 11-22-33") == ["Ниноʼ Беридзе"]
    assert cabinet.names(search="0599112233") == ["Ниноʼ Беридзе"]
    assert cabinet.names(search="ХИНКАЛИ") == []
    assert cabinet.names(search="ხინკალი") == ["Giorgi"]
    assert cabinet.names(search="mesa") == ["José"]
    assert cabinet.names(search="answer 1") == ["José"]
    assert cabinet.names(search="nobody here") == []
    assert cabinet.names(search="столик", channel="telegram") == []


def test_feed_rejects_bad_filters() -> None:
    world = build_world(scripted(say("Hi")))
    world.send("Hi")
    cabinet = Cabinet(world)

    for params in (
        {"status": "lost"},
        {"from": "2026-02-30"},
        {"from": "yesterday"},
        {"from": "2026-10-05", "to": "2026-10-01"},
        {"search": "x" * 201},
        {"limit": "0"},
        {"limit": "201"},
        {"cursor": "%%%"},
    ):
        response = cabinet.client.get(
            cabinet.url(), params=params, headers=bearer("owner")
        )
        assert response.status_code == 422, params


def test_card_lists_the_bookings_leads_and_handoffs_made_in_it() -> None:
    world = build_world(scripted(say("Да, есть."), say("Hello")))
    reply = world.send("Столик на вечер?", name="Нино")
    other = world.send("Hi", channel=ChannelKind.TELEGRAM, user_id="tg-1", phone=None)
    cabinet = Cabinet(world)
    conversation = next(
        item for item in world.conversations() if item.id == reply.conversation_id
    )
    table = ResourceDocument(
        business_id=world.business.id,
        kind=ResourceKind.TABLE,
        name=ResourceName("Table 4"),
        capacity=ResourceCapacity(4),
    )
    cabinet.storage.resource_repo.save(table)
    for conversation_id, hour in (
        (reply.conversation_id, 19),
        (other.conversation_id, 20),
    ):
        cabinet.storage.booking_repo.save(
            BookingDocument(
                business_id=world.business.id,
                resource_id=table.id,
                contact_id=conversation.contact_id,
                conversation_id=conversation_id,
                starts_at=BookingStartsAtUnixSeconds(1_791_219_600 + hour * 60),
                ends_at=BookingEndsAtUnixSeconds(1_791_226_800 + hour * 60),
                party_size=PartySize(2),
                status=BookingStatus.CONFIRMED,
                source_channel=ChannelKind.WHATSAPP,
            )
        )
    cabinet.storage.lead_repo.save(
        LeadDocument(
            business_id=world.business.id,
            contact_id=conversation.contact_id,
            conversation_id=reply.conversation_id,
            lead_type=LeadType.BANQUET,
            details=LeadDetails("Wedding for 60"),
            source_channel=ChannelKind.WHATSAPP,
        )
    )
    world.handoff_repo.save(
        HandoffDocument(
            business_id=world.business.id,
            conversation_id=reply.conversation_id,
            contact_id=conversation.contact_id,
            reason=HandoffReason.COMPLAINT,
            summary=HandoffSummary("Cold soup"),
        )
    )

    card = cabinet.card(reply.conversation_id)

    [booking] = card["bookings"]
    assert booking["resource_name"] == "Table 4"
    assert booking["contact_name"] == "Нино"
    assert booking["conversation_id"] == str(reply.conversation_id)
    assert [lead["details"] for lead in card["leads"]] == ["Wedding for 60"]
    assert [handoff["summary"] for handoff in card["handoffs"]] == ["Cold soup"]
    assert card["handoffs"][0]["contact_name"] == "Нино"
    assert cabinet.card(other.conversation_id)["leads"] == []
