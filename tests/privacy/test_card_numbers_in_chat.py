"""
A customer who types a card number in a chat: the inbox, the stored
message, the model's turn, the stored transcript of model turns, the
quality journal and the log lines all get it masked
('4242 4242 4242 4242 cvv 123' is the PCI test message of PAY-05).
"""

import io
import logging
from collections.abc import Iterator
from datetime import timedelta

import pytest
from typed_time_provider import Microseconds, MonotonicClock, Nanoseconds, WallClock

from app.adapters.llm.tracing_llm_adapter import TracingLlmAdapter
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.media import AttachmentKind
from app.schemas.domain.message_media import InboundAttachment
from app.schemas.dto.conversations import InboundMessage
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.media.strings import AttachmentCaption
from app.utilities.deliveries.inbox_messages import build_inbound_customer_message
from app.utilities.observability.log_formatting import JsonLogFormatter
from tests.brain.brain_world import build_world
from tests.brain.engine_helpers import requests_of, user_turn_text
from tests.brain.scripted_turns import say, scripted
from tests.channels.outbox_reads import inbox
from tests.channels.telegram_updates import build_update, connect_bot, post_update
from tests.channels.testbed import ChannelsTestbed
from tests.platform.test_observability import (
    STARTED_AT_NANOSECONDS,
    RecordingTraceFacilitator,
    build_request,
)
from tests.privacy.test_trace_minimization import scripted as scripted_reply

CARD_MESSAGE: str = "4242 4242 4242 4242 cvv 123"
MASKED_MESSAGE: str = "[card number] cvv [security code]"
PAYMENT_LINK_REPLY: str = (
    "Please never send card details here: pay the deposit on the secure "
    "payment link I send you."
)


@pytest.fixture
def json_log_lines() -> Iterator[io.StringIO]:
    """Every log line of the test, formatted as production writes it."""

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLogFormatter())
    root: logging.Logger = logging.getLogger()
    level: int = root.level
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    try:
        yield stream
    finally:
        root.removeHandler(handler)
        root.setLevel(level)


def test_the_inbox_and_the_engine_get_the_card_masked() -> None:
    testbed = ChannelsTestbed()
    _, channel = connect_bot(testbed)

    post_update(testbed, channel, build_update(text=CARD_MESSAGE))
    testbed.run_worker()

    [event] = inbox(testbed)
    assert event.customer_message is not None
    assert str(event.customer_message.text) == MASKED_MESSAGE
    [received] = testbed.pipeline.messages
    assert str(received.text) == MASKED_MESSAGE


def test_captions_are_masked_in_the_inbox() -> None:
    message = build_inbound_customer_message(
        ChannelUserId("555000111"),
        MessageText("my card"),
        None,
        None,
        [
            InboundAttachment(
                kind=AttachmentKind.IMAGE,
                caption=AttachmentCaption(f"front: {CARD_MESSAGE}"),
            ),
            InboundAttachment(kind=AttachmentKind.IMAGE),
        ],
    )

    captioned, plain = message.attachments
    assert str(captioned.caption) == f"front: {MASKED_MESSAGE}"
    assert plain.caption is None


def test_the_stored_message_the_model_and_the_logs_never_see_the_card(
    json_log_lines: io.StringIO,
) -> None:
    world = build_world(scripted(say(PAYMENT_LINK_REPLY)))

    reply = world.send(CARD_MESSAGE)

    assert PAYMENT_LINK_REPLY in str(reply.text)
    customer_texts = [
        str(message.text)
        for message in world.messages(reply.conversation_id)
        if message.author is MessageAuthor.CUSTOMER
    ]
    assert customer_texts == [MASKED_MESSAGE]
    [request] = requests_of(world)
    turn_text = user_turn_text(request.transcript[-1])
    assert MASKED_MESSAGE in turn_text
    assert "4242" not in turn_text
    stored_turns = " ".join(
        str(turn.payload) for turn in world.turns(reply.conversation_id)
    )
    assert "4242" not in stored_turns and "cvv 123" not in stored_turns
    lines = json_log_lines.getvalue()
    assert "4242" not in lines and "cvv 123" not in lines


def test_a_message_stored_before_masking_is_masked_for_the_model() -> None:
    world = build_world(scripted(say(PAYMENT_LINK_REPLY)))
    deferred = world.pipeline.start(
        InboundMessage(
            business_id=world.business.id,
            channel=ChannelKind.WHATSAPP,
            channel_user_id=ChannelUserId("995555123456"),
            text=MessageText("Here is my card"),
            is_reply_deferred=True,
        )
    )
    # A message kept before masking at intake existed.
    [stored] = world.messages(deferred.conversation_id)
    stored.text = MessageText(f"Here is my card {CARD_MESSAGE}")
    world.message_repo.save(stored)
    world.clock.advance(timedelta(seconds=5))

    world.send("Did you get it?")

    [request] = requests_of(world)
    turn_text = user_turn_text(request.transcript[-1])
    assert f"Here is my card {MASKED_MESSAGE}" in turn_text
    assert "4242" not in turn_text


def test_the_quality_journal_never_keeps_a_card_even_with_raw_text() -> None:
    inner = scripted_reply(f"You wrote {CARD_MESSAGE}; use the payment link.")
    facilitator = RecordingTraceFacilitator()
    adapter = TracingLlmAdapter(
        inner_adapter=inner,
        trace_facilitator=facilitator,
        wall_clock=WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: STARTED_AT_NANOSECONDS,
        ),
        monotonic_clock=MonotonicClock(
            preferred_time_unit_type=Nanoseconds,
            monotonic_nanosecond_factory=lambda: 0,
        ),
        is_content_traced=True,
        is_raw_text_traced=True,
    )
    request = build_request(inner).model_copy(
        update={"transcript": [inner.build_user_text_turn(MessageText(CARD_MESSAGE))]}
    )

    adapter.complete(request)

    [trace] = facilitator.traces
    assert str(trace.input_text) == MASKED_MESSAGE
    assert (
        str(trace.output_text) == f"You wrote {MASKED_MESSAGE}; use the payment link."
    )
