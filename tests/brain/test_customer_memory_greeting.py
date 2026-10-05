"""A returning customer is greeted with what the assistant remembers."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.dto.conversations import LlmRequest
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId
from tests.brain.brain_world import CUSTOMER_PHONE, BrainWorld, build_world
from tests.brain.engine_helpers import requests_of, user_turn_text
from tests.brain.memory_helpers import (
    add_booking,
    add_note,
    build_summarizer,
    only_contact,
    run_summary_job,
    summary_jobs,
)
from tests.brain.scripted_turns import say, scripted

TBILISI: ZoneInfo = ZoneInfo("Asia/Tbilisi")
SATURDAY_EVENING: datetime = datetime(2026, 10, 3, 20, 0, tzinfo=TBILISI)
WELCOME_BACK: str = (
    "Welcome back, Giorgi! Your table for 4 is booked for Saturday 2026-10-03 at 20:00."
)


def first_visit(world: BrainWorld) -> None:
    """A conversation about the terrace, summarized two quiet hours later."""

    world.send("Hi, do you have a terrace?", name="Giorgi")
    world.clock.advance(timedelta(hours=2, minutes=1))
    summarizer = build_summarizer(
        world, scripted(say("Asked whether the restaurant has a terrace."))
    )
    report = run_summary_job(summarizer, summary_jobs(world)[0])
    assert int(report.processed_count) == 1


def last_request(world: BrainWorld) -> LlmRequest:
    return requests_of(world)[-1]


def test_a_returning_customer_is_greeted_with_their_booking() -> None:
    world = build_world(scripted(say("Yes, we have a terrace."), say(WELCOME_BACK)))
    first_visit(world)
    add_booking(world, only_contact(world), SATURDAY_EVENING)
    # The next day: a new conversation (the last one had no message for 24 h).
    world.clock.advance(timedelta(days=1))

    reply = world.send("Hello again! What time is my booking?")

    turn: str = user_turn_text(last_request(world).transcript[0])
    assert (
        "Returning customer: 1 earlier conversation with the business, the last "
        "on Thursday 2026-10-01." in turn
    )
    assert "welcome them back, by name when it is known" in turn
    assert "- Saturday 2026-10-03 20:00, Table 4, 4 people, status confirmed" in turn
    assert "<untrusted>Asked whether the restaurant has a terrace.</untrusted>" in turn
    # The booking's date, time and guests come from the platform: the reply
    # guard lets the greeting through as written (after the AI disclosure).
    assert reply.text is not None
    assert str(reply.text).endswith(WELCOME_BACK)
    assert len(world.conversations()) == 2


def test_a_first_time_customer_gets_no_memory() -> None:
    world = build_world(scripted(say("Hello!")))

    world.send("Hi, do you have a terrace?", name="Giorgi")

    turn: str = user_turn_text(last_request(world).transcript[0])
    assert "Returning customer" not in turn
    assert "Their bookings still to come" not in turn


def test_a_customer_booked_by_staff_hears_about_the_booking_first_time() -> None:
    world = build_world(scripted(say("Your table is on Saturday at 20:00.")))
    contact = ContactDocument(
        business_id=world.business.id,
        name=ContactName("Giorgi"),
        phone_number=CUSTOMER_PHONE,
        verified_phone_number=CUSTOMER_PHONE,
        channel_identities=[
            ChannelIdentity(
                channel=ChannelKind.WHATSAPP,
                channel_user_id=ChannelUserId("995555123456"),
            )
        ],
    )
    world.contact_repo.save(contact)
    add_booking(world, contact, SATURDAY_EVENING, party_size=2)

    world.send("Is my table still booked?")

    turn: str = user_turn_text(last_request(world).transcript[0])
    assert "Returning customer" not in turn
    assert "- Saturday 2026-10-03 20:00, Table 4, 2 people, status confirmed" in turn


def test_the_memory_joins_only_the_first_reply_of_a_conversation() -> None:
    world = build_world(
        scripted(say("Yes."), say(WELCOME_BACK), say("You are welcome."))
    )
    first_visit(world)
    add_booking(world, only_contact(world), SATURDAY_EVENING)
    world.clock.advance(timedelta(days=1))
    world.send("Hello again! What time is my booking?")

    world.send("Thanks!")

    later_turn: str = user_turn_text(last_request(world).transcript[-1])
    assert "Returning customer" not in later_turn
    assert "Table 4" not in later_turn


def test_team_notes_reach_the_memory_only_when_the_owner_shares_them() -> None:
    world = build_world(scripted(say("Yes."), say("Hello!"), say("Hi!"), say("Hi!")))
    first_visit(world)
    add_note(world, world.conversations()[0].id, "Prefers the window table")
    world.clock.advance(timedelta(days=2))

    world.send("Hello again")
    assert "Prefers the window table" not in user_turn_text(
        last_request(world).transcript[0]
    )

    world.memory.settings_repo.change(
        world.business.id,
        lambda stored: setattr(stored, "shares_team_notes", True),
        world.clock.wall_clock().now_unix(),
    )
    world.clock.advance(timedelta(days=2))
    world.send("Hello once more")

    turn: str = user_turn_text(last_request(world).transcript[0])
    assert "Internal notes of the business's team about them" in turn
    assert "<untrusted>Prefers the window table</untrusted>" in turn
    assert "2 earlier conversations" in turn


def test_memory_turned_off_remembers_nothing_and_writes_no_summaries() -> None:
    world = build_world(scripted(say("Yes."), say("Hello!")))
    world.memory.settings_repo.change(
        world.business.id,
        lambda stored: setattr(stored, "remembers_customers", False),
        world.clock.wall_clock().now_unix(),
    )
    world.send("Hi, do you have a terrace?", name="Giorgi")
    add_booking(world, only_contact(world), SATURDAY_EVENING)
    world.clock.advance(timedelta(days=2))

    world.send("Hello again")

    turn: str = user_turn_text(last_request(world).transcript[0])
    assert "Returning customer" not in turn
    assert "Table 4" not in turn
    assert summary_jobs(world) == []
