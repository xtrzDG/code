"""What staff wrote reaches the model, so the assistant stays consistent with it."""

from datetime import timedelta

from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.domain.conversations import MessageDocument
from app.schemas.typings.conversations.strings import MessageText
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.engine_helpers import requests_of, user_turn_text
from tests.brain.scripted_turns import call_tool, say, scripted

STAFF_TEXT: str = "Yes, 10% for 8+ guests, Friday 19:00 is held for you"


def write_as_staff(world: BrainWorld, text: str) -> None:
    conversation = world.conversations()[0]
    now = Microseconds(world.clock.now_nanoseconds() // 1000)
    world.message_repo.save(
        MessageDocument(
            conversation_id=conversation.id,
            business_id=world.business.id,
            direction=MessageDirection.OUTBOUND,
            author=MessageAuthor.STAFF,
            text=MessageText(text),
            sent_by=world.owner_id,
            created_at=now,
            updated_at=now,
        )
    )


def reopen(world: BrainWorld) -> None:
    conversation = world.conversations()[0]
    conversation.status = ConversationStatus.OPEN
    world.conversation_repo.save(conversation)


def last_user_turn(world: BrainWorld) -> str:
    return user_turn_text(requests_of(world)[-1].transcript[-1])


def test_staff_reply_after_a_handoff_reaches_the_model_and_backs_its_numbers() -> None:
    world = build_world(
        scripted(
            call_tool(
                AssistantToolName.HANDOFF_TO_HUMAN,
                '{"reason":"customer_request","summary":"Group discount",'
                '"urgency":"normal"}',
            ),
            say("A colleague will contact you soon."),
            say("Done: 10% off for 8 guests, Friday at 19:00."),
        )
    )
    world.send("Do you give a discount for 8 people on Friday?")
    world.clock.advance(timedelta(minutes=1))
    world.send("any news?")
    world.clock.advance(timedelta(minutes=1))
    write_as_staff(world, STAFF_TEXT)
    reopen(world)
    world.clock.advance(timedelta(minutes=1))

    reply = world.send("Great, please confirm")

    turn = last_user_turn(world)
    assert "- Customer: any news?" in turn
    assert f"- Staff: {STAFF_TEXT}" in turn
    assert turn.index("- Customer: any news?") < turn.index(f"- Staff: {STAFF_TEXT}")
    assert turn.endswith("Great, please confirm")
    # Staff are the business speaking: repeating their 10% is not invented.
    assert reply.text == "Done: 10% off for 8 guests, Friday at 19:00."
    assert reply.is_handed_off is False


def test_staff_message_in_an_open_conversation_reaches_the_next_turn() -> None:
    world = build_world(scripted(say("Hello!"), say("See you on Friday!")))
    world.send("Hi")
    world.clock.advance(timedelta(minutes=1))
    write_as_staff(world, "We hold a table for you on Friday at 19:00.")
    world.clock.advance(timedelta(minutes=1))

    world.send("Thanks!")

    turn = last_user_turn(world)
    assert "- Staff: We hold a table for you on Friday at 19:00." in turn
    assert turn.endswith("Thanks!")
