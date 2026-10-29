"""A caller is remembered like a chatter: the call's summary reaches the next chat."""

from datetime import timedelta

from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import ConversationDocument
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.call_memory_world import (
    call_transcript,
    finish_call,
    summarize_call,
    summary_answer,
)
from tests.brain.engine_helpers import requests_of, user_turn_text
from tests.brain.scripted_turns import say, scripted

MEMORY: str = "Called to book a table for 4 on Saturday at 20:00; booked by the window."
TRANSCRIPT = call_transcript(
    (MessageAuthor.ASSISTANT, "Hello! How can I help?"),
    (MessageAuthor.CUSTOMER, "A table for four on Saturday at eight, by the window."),
)


def stored(
    world: BrainWorld, conversation: ConversationDocument
) -> ConversationDocument:
    found = world.conversation_repo.get(world.business.id, conversation.id)
    assert found is not None
    return found


def test_the_call_summary_reaches_the_next_chat_turns_context() -> None:
    world = build_world(scripted(say("Welcome back! Your table is booked.")))
    finished = finish_call(world)
    model = scripted(summary_answer(MEMORY))

    outcome = summarize_call(world, finished, model, TRANSCRIPT)

    assert outcome.is_generated is True
    assert outcome.is_remembered is True
    assert str(stored(world, finished.conversation).summary) == MEMORY
    [request] = model.requests
    assert "Memory: yes" in user_turn_text(request.transcript[0])
    # The next day the caller writes on WhatsApp from the same phone.
    world.clock.advance(timedelta(days=1))

    world.send("Hello again!")

    turn: str = user_turn_text(requests_of(world)[-1].transcript[0])
    assert "Returning customer: 1 earlier conversation with the business" in turn
    assert f"(phone): <untrusted>{MEMORY}</untrusted>" in turn


def test_the_memory_is_written_once() -> None:
    world = build_world(scripted())
    finished = finish_call(world)
    summarize_call(world, finished, scripted(summary_answer(MEMORY)), TRANSCRIPT)
    later = scripted(summary_answer("Something else."))

    outcome = summarize_call(world, finished, later, TRANSCRIPT)

    assert outcome.is_remembered is False
    assert later.requests == []
    assert str(stored(world, finished.conversation).summary) == MEMORY


def test_summaries_to_staff_off_still_remember_the_caller() -> None:
    world = build_world(scripted())
    finished = finish_call(world)
    model = scripted(summary_answer(MEMORY))

    outcome = summarize_call(
        world, finished, model, TRANSCRIPT, is_summary_enabled=False
    )

    assert outcome.is_remembered is True
    assert outcome.is_generated is False
    assert "Languages: none\nMemory: yes" in user_turn_text(
        model.requests[0].transcript[0]
    )
    call = world.call_repo.get(world.business.id, finished.call.call_id)  # type: ignore[arg-type]
    assert call is not None and call.summaries == []


def test_a_business_that_forgets_customers_keeps_no_call_memory() -> None:
    world = build_world(scripted())
    world.memory.settings_repo.change(
        world.business.id,
        lambda settings: setattr(settings, "remembers_customers", False),
        world.clock.wall_clock().now_unix(),
    )
    finished = finish_call(world)
    model = scripted(summary_answer(MEMORY))

    outcome = summarize_call(world, finished, model, TRANSCRIPT)

    assert outcome.is_remembered is False
    assert stored(world, finished.conversation).summary is None
    assert "Memory: no" in user_turn_text(model.requests[0].transcript[0])


def test_a_declined_recording_is_summarized_without_identifiers() -> None:
    world = build_world(scripted())
    finished = finish_call(world, declined=True)
    model = scripted(summary_answer("Called to book; wrote +995 555 12 34 56 down."))

    summarize_call(
        world,
        finished,
        model,
        call_transcript(
            (MessageAuthor.CUSTOMER, "My card is 4111 1111 1111 1111, mail a@b.ge"),
        ),
    )

    sent: str = user_turn_text(model.requests[0].transcript[0])
    assert "4111" not in sent and "a@b.ge" not in sent
    assert "[card number]" in sent and "[email]" in sent
    summary = str(stored(world, finished.conversation).summary)
    assert summary == "Called to book; wrote [phone] down."
