"""
Never lose a customer message: faults injected at every step of the path
(provider, between the model's reply and the send, a killed worker, a
platform that redelivers) still give exactly one delivered answer.
"""

import pytest

from app.schemas.constants.deliveries import InboundEventStatus, OutboundMessageStatus
from app.schemas.exceptions.application_errors import ExternalServiceError
from tests.channels.channels_payloads import telegram_ok
from tests.channels.outbox_reads import inbox, outbox_of
from tests.channels.telegram_updates import build_update, connect_bot, post_update
from tests.channels.testbed import ChannelsTestbed

ANSWER: str = "Reply: Do you have a table for 4 tonight?"
# Past the job's lease (120 s), well before the inbox event's (180 s) ends:
# the job's next attempt takes the event over from its dead worker at once.
PAST_THE_JOB_LEASE_SECONDS: int = 121


class WorkerKilled(BaseException):
    """A worker process dying mid-turn (deploy, OOM): nothing catches it."""


def delivered_texts(testbed: ChannelsTestbed) -> list[str]:
    return [
        str(request.json()["text"])
        for request in testbed.telegram_transport.requests_to("/sendMessage")
    ]


def test_a_provider_500_on_the_first_send_gives_exactly_one_message() -> None:
    testbed = ChannelsTestbed()
    business, channel = connect_bot(testbed)
    testbed.telegram_transport.respond_in_turn(
        "POST",
        r"/sendMessage$",
        [
            (500, {"ok": False, "error_code": 500, "description": "Internal"}),
            (200, telegram_ok({"message_id": 99})),
        ],
    )

    post_update(testbed, channel, build_update())
    testbed.run_worker()
    [waiting] = outbox_of(testbed, business.id)
    assert waiting.status is OutboundMessageStatus.PENDING
    assert waiting.attempts == 1

    testbed.clock.advance(10)
    testbed.run_worker()

    # Two attempts reached Telegram; only the second was accepted.
    assert delivered_texts(testbed) == [ANSWER, ANSWER]
    [delivered] = outbox_of(testbed, business.id)
    assert delivered.status is OutboundMessageStatus.DELIVERED
    assert delivered.attempts == 2
    assert delivered.provider_message_id == "555000111:99"
    assert len(testbed.pipeline.messages) == 1


def test_a_crash_between_the_reply_and_the_send_gives_exactly_one_message() -> None:
    testbed = ChannelsTestbed()
    business, channel = connect_bot(testbed)
    testbed.outbound_message_repo.insert_failures = [
        ExternalServiceError("database connection lost")
    ]

    post_update(testbed, channel, build_update())
    testbed.run_worker()
    assert delivered_texts(testbed) == []
    [event] = inbox(testbed)
    assert event.status is InboundEventStatus.PROCESSING
    assert str(event.last_error) == "database connection lost"

    # The job runs again after its backoff: the reply the model already
    # wrote is sent, the model is not asked again.
    testbed.clock.advance(30)
    testbed.run_worker()

    assert delivered_texts(testbed) == [ANSWER]
    assert len(testbed.pipeline.messages) == 1
    [answered] = inbox(testbed)
    assert answered.status is InboundEventStatus.ANSWERED
    [message] = outbox_of(testbed, business.id)
    assert message.source_message_id == answered.reply_message_id


def test_a_worker_killed_mid_turn_is_answered_once_the_job_lease_ends() -> None:
    testbed = ChannelsTestbed()
    _, channel = connect_bot(testbed)
    testbed.pipeline.interruptions = [WorkerKilled()]

    post_update(testbed, channel, build_update())
    with pytest.raises(WorkerKilled):
        testbed.run_worker()

    # A new worker starts; the turn is held until the job's lease runs out.
    testbed.worker = testbed.build_worker()
    testbed.run_worker()
    assert delivered_texts(testbed) == []

    testbed.clock.advance(PAST_THE_JOB_LEASE_SECONDS)
    testbed.run_worker()

    assert delivered_texts(testbed) == [ANSWER]
    [event] = inbox(testbed)
    assert event.status is InboundEventStatus.ANSWERED
    assert event.attempts == 2
    # The customer's message is in the transcript once, under the inbox's id.
    customer_messages = [
        message
        for message in testbed.message_repo.list_by_conversation(
            event.business_id or channel.business_id, testbed.pipeline.conversation_id
        )
        if message.id == event.customer_message_id
    ]
    assert len(customer_messages) == 1


def test_the_same_webhook_delivered_three_times_gets_one_answer() -> None:
    testbed = ChannelsTestbed()
    _, channel = connect_bot(testbed)

    responses = [post_update(testbed, channel, build_update()) for _ in range(3)]
    testbed.run_worker()
    late = post_update(testbed, channel, build_update())
    testbed.run_worker()

    assert [response.json()["queued"] for response in responses] == [1, 0, 0]
    assert late.json()["duplicates"] == 1
    assert delivered_texts(testbed) == [ANSWER]
    assert len(testbed.pipeline.messages) == 1
    assert len(inbox(testbed)) == 1
