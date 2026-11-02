"""
A conversation is answered for MAX_CONVERSATION_MESSAGES customer messages:
the next one gets its own closing message once (not the hourly limit's),
later ones silence, and every message still reaches the inbox.
"""

from datetime import timedelta

from typed_time_provider import Microseconds

from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import MessageDocument
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.conversations.turns.turn_gate import MAX_CONVERSATION_MESSAGES
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.engine_helpers import requests_of
from tests.brain.scripted_turns import say, scripted

# Its own closing text, not the hourly limit's "write again a little later".
STOP_MESSAGE: str = (
    "We have talked a lot in this conversation, so I will stop here. Our team "
    "sees all your messages and will get back to you if needed."
)
HOURLY_STOP_MESSAGE: str = (
    "You have sent a lot of messages in a short time. Please write again a "
    "little later, and we will gladly continue."
)


def seed_customer_messages(world: BrainWorld, count: int) -> None:
    """Earlier messages of the conversation, older than the hourly window."""

    conversation = world.conversations()[0]
    for _ in range(count):
        world.message_repo.save(
            MessageDocument(
                conversation_id=conversation.id,
                business_id=world.business.id,
                direction=MessageDirection.INBOUND,
                author=MessageAuthor.CUSTOMER,
                text=MessageText("One more question"),
                created_at=Microseconds(int(conversation.created_at) - 10),
                updated_at=Microseconds(int(conversation.created_at) - 10),
            )
        )


def test_a_conversation_past_its_length_is_closed_politely() -> None:
    world = build_world(
        scripted(say("Hello!"), say("Of course.")), contact_message_limit=1000
    )
    world.send("Hi")
    seed_customer_messages(world, MAX_CONVERSATION_MESSAGES - 2)

    last_answer = world.send("And the terrace?")
    notice = world.send("Still there?")
    silence = world.send("Hello?")

    assert last_answer.text == "Of course."
    assert notice.text == STOP_MESSAGE
    assert silence.text is None
    assert len(requests_of(world)) == 2
    inbound = [
        message
        for message in world.messages(world.conversations()[0].id)
        if message.direction is MessageDirection.INBOUND
    ]
    assert len(inbound) == MAX_CONVERSATION_MESSAGES + 2


def test_a_new_conversation_is_answered_again() -> None:
    world = build_world(
        scripted(say("Hello!"), say("Welcome back!")), contact_message_limit=1000
    )
    world.send("Hi")
    seed_customer_messages(world, MAX_CONVERSATION_MESSAGES)
    assert world.send("Anyone?").text is None

    world.clock.advance(timedelta(hours=25))
    reply = world.send("Good morning")

    assert reply.text is not None and reply.text.endswith("Welcome back!")
    assert len(world.conversations()) == 2


def test_the_hourly_limit_keeps_its_own_text() -> None:
    world = build_world(scripted(say("Hello!")), contact_message_limit=1)
    world.send("Hi")

    notice = world.send("And the terrace?")

    assert notice.text == HOURLY_STOP_MESSAGE


def test_the_closing_text_is_said_in_the_customers_language() -> None:
    world = build_world(
        scripted(say("Ciao!"), say("Certo.")), contact_message_limit=1000
    )
    world.send("Ciao")
    seed_customer_messages(world, MAX_CONVERSATION_MESSAGES - 1)

    notice = world.send("Ci siete ancora?")

    assert notice.text is not None
    assert notice.text.startswith("Abbiamo scritto molto in questa conversazione")
