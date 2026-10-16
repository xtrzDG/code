"""The outbox: retries with backoff, Retry-After, order, parts and give-ups."""

from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.deliveries import OutboundMessageStatus
from app.schemas.constants.handoffs import HandoffSummaryCode
from app.schemas.dto.handoffs import CodedHandoffSummary
from tests.channels.channels_payloads import telegram_ok
from tests.channels.outbox_reads import outbox_of
from tests.channels.telegram_updates import build_update, connect_bot, post_update
from tests.channels.testbed import ChannelsTestbed

DOWN: tuple[int, object] = (
    502,
    {"ok": False, "error_code": 502, "description": "Bad Gateway"},
)
SENT: tuple[int, object] = (200, telegram_ok({"message_id": 1}))


def sent_texts(testbed: ChannelsTestbed) -> list[str]:
    return [
        str(request.json()["text"])
        for request in testbed.telegram_transport.requests_to("/sendMessage")
    ]


def test_a_rate_limit_waits_at_least_as_long_as_the_platform_asks() -> None:
    testbed = ChannelsTestbed()
    business, channel = connect_bot(testbed)
    testbed.telegram_transport.respond_in_turn(
        "POST",
        r"/sendMessage$",
        [
            (
                429,
                {
                    "ok": False,
                    "error_code": 429,
                    "description": "Too Many Requests: retry after 45",
                    "parameters": {"retry_after": 45},
                },
            ),
            SENT,
        ],
    )

    post_update(testbed, channel, build_update())
    testbed.run_worker()

    [waiting] = outbox_of(testbed, business.id)
    assert waiting.status is OutboundMessageStatus.PENDING
    assert waiting.next_attempt_at == testbed.clock.now_microseconds() + 45_000_000
    testbed.clock.advance(44)
    testbed.run_worker()
    assert len(sent_texts(testbed)) == 1

    testbed.clock.advance(1)
    testbed.run_worker()
    [delivered] = outbox_of(testbed, business.id)
    assert delivered.status is OutboundMessageStatus.DELIVERED
    assert len(sent_texts(testbed)) == 2


def test_exhausted_retries_give_the_conversation_to_staff() -> None:
    testbed = ChannelsTestbed()
    business, channel = connect_bot(testbed)
    testbed.telegram_transport.respond_in_turn("POST", r"/sendMessage$", [DOWN])

    post_update(testbed, channel, build_update())
    for _ in range(9):
        testbed.run_worker()
        testbed.clock.advance(30 * 60)

    [dead] = outbox_of(testbed, business.id)
    assert dead.status is OutboundMessageStatus.DEAD
    assert dead.attempts == 8
    assert "502" in str(dead.last_error)
    [handoff] = testbed.handoffs_to_human.commands
    assert handoff.conversation_id == testbed.pipeline.conversation_id
    assert isinstance(handoff.summary, CodedHandoffSummary)
    assert handoff.summary.code is HandoffSummaryCode.REPLY_UNDELIVERED
    # The reply that never arrived is quoted; the platform's error is not.
    assert str(handoff.summary.quoted_text).startswith("Reply: Do you have a table")
    assert "502" not in str(handoff.summary.quoted_text)
    # The owner sees why replies of this channel do not arrive.
    stored = testbed.channel_repo.get(channel.id)
    assert stored is not None and "502" in str(stored.last_error)


def test_no_second_handoff_when_staff_already_own_the_conversation() -> None:
    testbed = ChannelsTestbed()
    business, channel = connect_bot(testbed)
    testbed.telegram_transport.respond(
        "POST",
        r"/sendMessage$",
        {"ok": False, "error_code": 400, "description": "chat not found"},
        status_code=400,
    )

    post_update(testbed, channel, build_update())
    testbed.run_worker()

    [dead] = outbox_of(testbed, business.id)
    assert dead.status is OutboundMessageStatus.DEAD
    assert dead.attempts == 1  # a refusal is not retried
    assert len(testbed.handoffs_to_human.commands) == 1
    conversation = testbed.conversation_repo.get(
        business.id, testbed.pipeline.conversation_id
    )
    assert conversation is not None
    conversation.status = ConversationStatus.HANDOFF
    testbed.conversation_repo.save(conversation)

    assert testbed.build_undelivered_reply_handoff.run(dead) is None


def test_replies_to_one_customer_arrive_in_the_order_they_were_written() -> None:
    testbed = ChannelsTestbed()
    business, channel = connect_bot(testbed)
    testbed.telegram_transport.respond_in_turn("POST", r"/sendMessage$", [DOWN, SENT])

    post_update(testbed, channel, build_update(message_id=1, text="First"))
    post_update(testbed, channel, build_update(message_id=2, text="Second"))
    testbed.run_worker()

    # The first reply failed and waits for its retry; the second waits too.
    assert sent_texts(testbed) == ["Reply: First"]
    assert [m.status for m in outbox_of(testbed, business.id)] == [
        OutboundMessageStatus.PENDING,
        OutboundMessageStatus.PENDING,
    ]

    testbed.clock.advance(11)
    testbed.run_worker()

    assert sent_texts(testbed) == ["Reply: First", "Reply: First", "Reply: Second"]
    assert [m.status for m in outbox_of(testbed, business.id)] == [
        OutboundMessageStatus.DELIVERED,
        OutboundMessageStatus.DELIVERED,
    ]


def test_a_retry_sends_only_the_parts_the_customer_did_not_get() -> None:
    testbed = ChannelsTestbed()
    business, channel = connect_bot(testbed)
    testbed.pipeline.reply_text = ("Меню и цены. " * 400).strip()
    testbed.telegram_transport.respond_in_turn(
        "POST", r"/sendMessage$", [SENT, DOWN, SENT]
    )

    post_update(testbed, channel, build_update())
    testbed.run_worker()
    [partial] = outbox_of(testbed, business.id)
    assert partial.delivered_parts == 1

    testbed.clock.advance(10)
    testbed.run_worker()

    texts = sent_texts(testbed)
    assert len(texts) == 3
    assert texts[1] == texts[2]  # the second part was tried again, not the first
    assert texts[0] != texts[2]
    [delivered] = outbox_of(testbed, business.id)
    assert delivered.status is OutboundMessageStatus.DELIVERED
    assert delivered.delivered_parts == 2
