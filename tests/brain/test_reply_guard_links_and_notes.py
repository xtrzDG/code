"""
The reply guard holds back links the business did not publish and quotes
of the team's internal notes: the reply is rewritten once, then handed
over; the business's own links, the platform's pages and well-known map
links pass, and a note stays useful as context.
"""

from datetime import timedelta

from app.schemas.constants.conversations import MessageAuthor, ReplyGuardVerdict
from app.schemas.constants.reply_safety import ReplyGuardReason
from app.schemas.domain.conversations import MessageDocument
from tests.brain.brain_orchestrators import GuardOptions
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.engine_helpers import requests_of, user_turn_text
from tests.brain.memory_helpers import add_note
from tests.brain.scripted_turns import say, scripted
from tests.brain.test_customer_memory_greeting import first_visit

WEBSITE_FACT: tuple[str, str, str] = (
    "website",
    "Website",
    "https://www.sakhli-restaurant.ge/menu",
)
PLATFORM: GuardOptions = GuardOptions(
    platform_base_urls=("https://app.workshop.example",)
)
NOTE: str = "Always asks for a discount and complains about the waiters"


def last_reply(world: BrainWorld, conversation_id: object) -> MessageDocument:
    replies = [
        message
        for message in world.messages(conversation_id)
        if message.author is MessageAuthor.ASSISTANT
    ]
    return replies[-1]


def test_an_invented_link_is_rewritten_once() -> None:
    world = build_world(
        scripted(
            say("Book online at https://sakhli-bookings.com/table, please."),
            say("You can book right here in the chat."),
        ),
        facts=[WEBSITE_FACT],
        guard=PLATFORM,
    )

    reply = world.send("Where can I book?")

    assert reply.guard_verdict is ReplyGuardVerdict.REWRITTEN
    assert reply.text is not None
    assert "sakhli-bookings.com" not in reply.text
    note = user_turn_text(requests_of(world)[1].transcript[-1])
    assert "links the business did not publish" in note
    assert "https://sakhli-bookings.com/table" in note
    stored = last_reply(world, reply.conversation_id)
    assert stored.guard_reasons == [ReplyGuardReason.UNVERIFIED_VALUES]
    assert stored.unverified_values == ["https://sakhli-bookings.com/table"]


def test_a_link_still_invented_after_the_rewrite_is_handed_over() -> None:
    world = build_world(
        scripted(say("See www.fake-offers.it"), say("Or see www.fake-offers.it/2")),
        guard=PLATFORM,
    )

    reply = world.send("Any offers?")

    assert reply.guard_verdict is ReplyGuardVerdict.HANDED_OFF
    assert reply.is_handed_off is True
    assert reply.text is not None
    assert "fake-offers" not in reply.text
    (handoff,) = world.handoffs()
    assert handoff.flagged_values == ["www.fake-offers.it/2"]


def test_the_business_platform_and_map_links_pass() -> None:
    text = (
        "Our menu: https://sakhli-restaurant.ge/menu, booking: "
        "https://app.workshop.example/r/AbC123, directions: "
        "https://maps.app.goo.gl/x1Y2"
    )
    world = build_world(scripted(say(text)), facts=[WEBSITE_FACT], guard=PLATFORM)

    reply = world.send("Menu and directions, please")

    assert reply.guard_verdict is ReplyGuardVerdict.CLEAN
    assert reply.text is not None
    assert reply.text.endswith(text)


def notes_world(*replies: str) -> BrainWorld:
    world = build_world(scripted(say("Yes."), *(say(reply) for reply in replies)))
    first_visit(world)
    add_note(world, world.conversations()[0].id, NOTE)
    world.memory.settings_repo.change(
        world.business.id,
        lambda stored: setattr(stored, "shares_team_notes", True),
        world.clock.wall_clock().now_unix(),
    )
    world.clock.advance(timedelta(days=2))
    return world


def test_a_reply_that_quotes_a_team_note_is_rewritten() -> None:
    world = notes_world(
        "Welcome back! Our team notes that you always asks for a discount and "
        "complains about the waiters.",
        "Welcome back! How can I help you today?",
    )

    reply = world.send("Hello again")

    assert reply.guard_verdict is ReplyGuardVerdict.REWRITTEN
    assert reply.text is not None
    assert "complains" not in reply.text
    note = user_turn_text(requests_of(world)[-1].transcript[-1])
    assert "quotes an internal note of the business's team" in note
    assert NOTE not in note
    stored = last_reply(world, reply.conversation_id)
    assert stored.guard_reasons == [ReplyGuardReason.PERSONAL_DATA]


def test_a_note_still_serves_as_context() -> None:
    world = notes_world("Welcome back! Shall I ask about a discount for you?")

    reply = world.send("Hello again")

    assert reply.guard_verdict is ReplyGuardVerdict.CLEAN
    assert f"<team_note>{NOTE}</team_note>" in user_turn_text(
        requests_of(world)[-1].transcript[0]
    )


def test_a_note_quoted_in_a_later_turn_is_still_found() -> None:
    world = notes_world(
        "Welcome back!",
        "Noted: always asks for a discount and complains about the waiters.",
        "Noted, thank you.",
    )
    world.send("Hello again")

    reply = world.send("What do you know about me?")

    assert reply.guard_verdict is ReplyGuardVerdict.REWRITTEN
    assert reply.text is not None
    assert reply.text.endswith("Noted, thank you.")
