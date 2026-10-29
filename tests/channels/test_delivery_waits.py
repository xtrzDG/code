"""
Deliveries that wait: an inbox event held by another processing is taken
when that lease ends, and a reply waits for an older reply to the same
customer unless that one is long overdue.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import InboundEventStatus, OutboundMessageStatus
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.utilities.deliveries.delivery_jobs import (
    DELIVER_OUTBOUND_JOB,
    PROCESS_INBOUND_MESSAGE_JOB,
    encode_inbound_event_payload,
    encode_outbound_message_payload,
)
from app.utilities.deliveries.delivery_keys import derive_inbound_event_id
from tests.channels.channels_payloads import telegram_ok
from tests.channels.outbox_reads import inbox, outbox_of
from tests.channels.telegram_updates import build_update, connect_bot, post_update
from tests.channels.testbed import ChannelsTestbed

MICROSECONDS_PER_SECOND: int = 1_000_000
OTHER_LEASE_SECONDS: int = 60
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


def test_an_event_held_by_another_processing_is_taken_when_its_lease_ends() -> None:
    testbed = ChannelsTestbed()
    _, channel = connect_bot(testbed)
    post_update(testbed, channel, build_update())
    [received] = inbox(testbed)
    lease_end = Microseconds(
        testbed.clock.now_microseconds() + OTHER_LEASE_SECONDS * MICROSECONDS_PER_SECOND
    )

    def held_elsewhere(event: InboundEventDocument) -> InboundEventDocument:
        event.status = InboundEventStatus.PROCESSING
        event.lease_until = lease_end
        return event

    testbed.inbound_event_repo.update(received.business_id, received.id, held_elsewhere)

    testbed.run_worker()
    [still_held] = inbox(testbed)
    assert still_held.status is InboundEventStatus.PROCESSING
    assert testbed.pipeline.messages == []

    testbed.clock.advance(OTHER_LEASE_SECONDS)
    testbed.run_worker()
    [answered] = inbox(testbed)
    assert answered.status is InboundEventStatus.ANSWERED
    assert len(testbed.pipeline.messages) == 1
    assert sent_texts(testbed) == ["Reply: Do you have a table for 4 tonight?"]


def test_a_reply_overdue_for_ten_minutes_no_longer_holds_back_the_next() -> None:
    testbed = ChannelsTestbed()
    business, channel = connect_bot(testbed)
    testbed.telegram_transport.respond_in_turn("POST", r"/sendMessage$", [DOWN, SENT])
    post_update(testbed, channel, build_update(message_id=1, text="First"))
    testbed.run_worker()
    [first] = outbox_of(testbed, business.id)
    long_ago = Microseconds(
        testbed.clock.now_microseconds() - 11 * 60 * MICROSECONDS_PER_SECOND
    )

    # Its retry should have run eleven minutes ago (the job was lost).
    def overdue(message: OutboundMessageDocument) -> OutboundMessageDocument:
        message.next_attempt_at = long_ago
        return message

    testbed.outbound_message_repo.update(business.id, first.id, overdue)

    post_update(testbed, channel, build_update(message_id=2, text="Second"))
    testbed.run_worker()

    assert sent_texts(testbed) == ["Reply: First", "Reply: Second"]
    assert [m.status for m in outbox_of(testbed, business.id)] == [
        OutboundMessageStatus.PENDING,
        OutboundMessageStatus.DELIVERED,
    ]


def test_jobs_naming_nothing_to_do_end_quietly() -> None:
    testbed = ChannelsTestbed()
    business, channel = connect_bot(testbed)
    post_update(testbed, channel, build_update())
    testbed.run_worker()
    [delivered] = outbox_of(testbed, business.id)
    missing_event = derive_inbound_event_id(
        business.id, ChannelKind.TELEGRAM, ProviderMessageId("never-received")
    )

    assert (
        testbed.claim_inbound_event.run(
            QueuedJobInput(
                job_id=QueuedJobId(),
                job_name=PROCESS_INBOUND_MESSAGE_JOB,
                payload=encode_inbound_event_payload(missing_event),
                business_id=business.id,
            )
        )
        is None
    )
    for business_id in (None, business.id):
        assert (
            testbed.take_due_outbound_message.run(
                QueuedJobInput(
                    job_id=QueuedJobId(),
                    job_name=DELIVER_OUTBOUND_JOB,
                    payload=encode_outbound_message_payload(delivered.id),
                    business_id=business_id,
                )
            )
            is None
        )
