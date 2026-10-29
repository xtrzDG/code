"""
The engine's side of reply speed: a burst's earlier messages are stored
without a model call and read by the last one's turn; every reply records
how long the customer waited, how many model rounds it took and whether
the fallback model wrote it.
"""

from datetime import timedelta

from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.conversations import AssistantReply, InboundMessage
from app.schemas.typings.conversations.booleans import IsReplyDeferred
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from tests.brain.brain_world import CUSTOMER_PHONE, BrainWorld, build_world
from tests.resilience.failover_fakes import answering

CUSTOMER_ID: str = "995555123456"


def burst_message(
    world: BrainWorld,
    text: str,
    waiting_since: Microseconds,
    is_reply_deferred: bool,
) -> AssistantReply:
    return world.pipeline.start(
        InboundMessage(
            business_id=world.business.id,
            channel=ChannelKind.WHATSAPP,
            channel_user_id=ChannelUserId(CUSTOMER_ID),
            text=MessageText(text),
            contact_phone_number=CUSTOMER_PHONE,
            waiting_since=waiting_since,
            is_reply_deferred=IsReplyDeferred(is_reply_deferred),
        )
    )


def stored(world: BrainWorld, author: MessageAuthor) -> list[MessageDocument]:
    [conversation] = world.conversations()
    return [
        message
        for message in world.messages(conversation.id)
        if message.author is author
    ]


def now_of(world: BrainWorld) -> Microseconds:
    return world.clock.wall_clock().now_unix()


def test_a_burst_is_one_model_call_that_reads_every_message() -> None:
    llm = answering("Yes, a table for 4 at 8 pm is free.")
    world = build_world(llm)
    first_at: Microseconds = now_of(world)

    replies: list[AssistantReply] = []
    texts = ["Hi", "Do you have a table for 4", "tonight at 8?"]
    for index, text in enumerate(texts):
        if index:
            world.clock.advance(timedelta(seconds=1))
        replies.append(burst_message(world, text, first_at, index < len(texts) - 1))

    assert [reply.text is None for reply in replies] == [True, True, False]
    assert not any(reply.is_handed_off for reply in replies)
    [request] = llm.requests
    transcript = " ".join(str(turn) for turn in request.transcript)
    assert all(text in transcript for text in texts)
    assert len(stored(world, MessageAuthor.CUSTOMER)) == 3
    [answer] = stored(world, MessageAuthor.ASSISTANT)
    assert answer.direction is MessageDirection.OUTBOUND
    assert answer.channel is ChannelKind.WHATSAPP
    assert answer.llm_round_count == 1
    assert answer.is_fallback_model is False
    # From the first message to the stored answer.
    assert answer.reply_latency_ms is not None
    assert (
        int(answer.reply_latency_ms) == (int(answer.created_at) - int(first_at)) // 1000
    )
    assert int(answer.reply_latency_ms) >= 2000


def test_a_reply_without_a_waiting_customer_records_no_latency() -> None:
    world = build_world(answering("Hello! How can I help?"))

    world.send("Hi")

    [answer] = stored(world, MessageAuthor.ASSISTANT)
    assert answer.reply_latency_ms is None
    assert answer.llm_round_count == 1
    assert answer.channel is ChannelKind.WHATSAPP


def test_a_deferred_message_is_stored_without_a_model_call() -> None:
    llm = answering("unused")
    world = build_world(llm)
    first_at: Microseconds = now_of(world)

    reply = burst_message(world, "Hi", first_at, is_reply_deferred=True)

    assert reply.text is None
    assert llm.requests == []
    assert stored(world, MessageAuthor.ASSISTANT) == []
