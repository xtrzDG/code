"""
Quick messages in a row get one reply, and a finished question is answered
at once: after a fragment the worker waits until the customer has been
quiet (1.5 s on Telegram, these tests' channel), shows "typing…" meanwhile
and answers every message in one turn; a burst whose newest message reads
as a finished sentence is answered without waiting.
"""

from app.schemas.constants.deliveries import InboundEventStatus
from app.schemas.domain.channels import ChannelDocument
from tests.channels.outbox_reads import inbox
from tests.channels.telegram_updates import build_update, connect_bot, post_update
from tests.resilience.reply_speed_testbed import NO_COALESCING
from tests.resilience.reply_speed_world import ReplySpeedTestbed

CHAT_ID: int = 555_000_111


def sent_texts(testbed: ReplySpeedTestbed) -> list[str]:
    return [
        str(request.json()["text"])
        for request in testbed.telegram_transport.requests_to("/sendMessage")
    ]


def write(
    testbed: ReplySpeedTestbed,
    channel: ChannelDocument,
    texts: list[str],
    gap_seconds: int = 1,
    first_message_id: int = 1,
) -> None:
    for index, text in enumerate(texts):
        if index:
            testbed.clock.advance(gap_seconds)
        post_update(
            testbed,
            channel,
            build_update(text=text, message_id=first_message_id + index),
        )


def test_three_quick_fragments_get_one_reply() -> None:
    testbed = ReplySpeedTestbed()
    _, channel = connect_bot(testbed)
    write(testbed, channel, ["Hi", "Do you have a table for 4", "tonight at 8"])

    testbed.run_worker()
    # The customer may still be writing: "typing…", no answer yet.
    assert sent_texts(testbed) == []
    assert testbed.typing.once
    assert {str(request.channel_user_id) for request in testbed.typing.once} == {
        str(CHAT_ID)
    }

    testbed.clock.advance(2)
    testbed.run_worker()

    assert sent_texts(testbed) == [
        "Reply to: Hi / Do you have a table for 4 / tonight at 8"
    ]
    events = inbox(testbed)
    assert [event.status for event in events] == [InboundEventStatus.ANSWERED] * 3
    assert len({event.outbound_message_id for event in events}) == 1
    assert events[0].outbound_message_id is not None
    assert len({event.conversation_id for event in events}) == 1
    # Each message went through the engine once; only the last was answered,
    # and every one waited since the first.
    turns = testbed.patient.messages
    assert [turn.is_reply_deferred for turn in turns] == [True, True, False]
    assert {turn.waiting_since for turn in turns} == {events[0].created_at}
    [kept] = testbed.typing.kept
    assert kept.replying_to == events[-1].provider_message_id
    # Taken 2 s after the newest message: 4, 3 and 2 s after each was queued.
    assert [event.queue_to_claim_ms for event in events] == [4_000, 3_000, 2_000]


def test_a_finished_question_ends_the_wait_for_the_whole_burst() -> None:
    testbed = ReplySpeedTestbed()
    _, channel = connect_bot(testbed)
    write(testbed, channel, ["Hi", "Do you have a table for 4 tonight at 8?"])

    testbed.run_worker()

    assert sent_texts(testbed) == [
        "Reply to: Hi / Do you have a table for 4 tonight at 8?"
    ]
    assert testbed.typing.once == []
    assert [event.status for event in inbox(testbed)] == [
        InboundEventStatus.ANSWERED
    ] * 2


def test_a_customer_who_keeps_writing_is_answered_within_three_waits() -> None:
    testbed = ReplySpeedTestbed()
    _, channel = connect_bot(testbed)
    # A fragment every second: never 1.5 s of quiet. The last one came 4 s
    # after the first; 4.5 s after the first is the longest wait.
    write(testbed, channel, ["one", "two", "three", "four", "five"])
    testbed.run_worker()
    assert sent_texts(testbed) == []

    testbed.clock.advance(1)
    testbed.run_worker()

    assert sent_texts(testbed) == ["Reply to: one / two / three / four / five"]


def test_a_single_finished_question_is_answered_at_once() -> None:
    testbed = ReplySpeedTestbed()
    _, channel = connect_bot(testbed)
    write(testbed, channel, ["Are you open today?"])

    testbed.run_worker()

    assert sent_texts(testbed) == ["Reply to: Are you open today?"]
    [event] = inbox(testbed)
    assert event.status is InboundEventStatus.ANSWERED
    assert event.queue_to_claim_ms == 0
    assert testbed.patient.messages[0].is_reply_deferred is False
    assert testbed.typing.once == []


def test_a_single_fragment_waits_only_for_the_quiet_time() -> None:
    testbed = ReplySpeedTestbed()
    _, channel = connect_bot(testbed)
    write(testbed, channel, ["Hi"])

    testbed.run_worker()
    assert sent_texts(testbed) == []

    testbed.clock.advance(2)
    testbed.run_worker()

    assert sent_texts(testbed) == ["Reply to: Hi"]
    [event] = inbox(testbed)
    assert event.queue_to_claim_ms == 2_000


def test_messages_far_apart_are_answered_one_by_one() -> None:
    testbed = ReplySpeedTestbed()
    _, channel = connect_bot(testbed)
    write(testbed, channel, ["Hi"])
    testbed.clock.advance(3)
    testbed.run_worker()

    write(testbed, channel, ["And parking?"], first_message_id=9)
    testbed.clock.advance(3)
    testbed.run_worker()

    assert sent_texts(testbed) == ["Reply to: Hi", "Reply to: And parking?"]
    assert [turn.is_reply_deferred for turn in testbed.patient.messages] == [
        False,
        False,
    ]


def test_without_coalescing_every_message_is_answered_at_once() -> None:
    testbed = ReplySpeedTestbed(coalesce_seconds=NO_COALESCING)
    _, channel = connect_bot(testbed)
    write(testbed, channel, ["Hi", "Table for 4?"])

    testbed.run_worker()

    assert sent_texts(testbed) == ["Reply to: Hi", "Reply to: Table for 4?"]
    assert testbed.typing.once == []
    assert len(testbed.typing.kept) == 2
