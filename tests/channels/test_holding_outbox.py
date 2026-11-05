"""
The holding reply ("one moment…") goes through the outbox like every
assistant reply: once per holding message, before the answer queued after it.
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import (
    InboundEventKind,
    OutboundMessageKind,
    OutboundMessageStatus,
)
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.inbound_events import (
    InboundCustomerMessage,
    InboundEventDocument,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.use_cases.channels.inbox.holding_outbox import queue_holding_reply
from app.utilities.deliveries.delivery_keys import (
    customer_recipient_key,
    derive_inbound_event_id,
    derive_outbound_message_id,
    outbound_serial_key,
    reply_idempotency_key,
)
from tests.channels.outbox_fakes import (
    RecordingJobQueue,
    RecordingOutbox,
    VanishingOutbox,
)

NOW: Microseconds = Microseconds(1_790_000_000_000_000)
HOLDING: MessageText = MessageText("One moment, I am checking the tables.")


def customer_event(
    business_id: BusinessId | None = None,
    channel_id: ChannelId | None = None,
    with_message: bool = True,
) -> InboundEventDocument:
    provider_message_id = ProviderMessageId("update_77")
    return InboundEventDocument(
        id=derive_inbound_event_id(
            business_id, ChannelKind.TELEGRAM, provider_message_id
        ),
        business_id=business_id,
        kind=InboundEventKind.CUSTOMER_MESSAGE,
        channel=ChannelKind.TELEGRAM,
        channel_id=channel_id,
        provider_message_id=provider_message_id,
        customer_message=(
            InboundCustomerMessage(
                channel_user_id=ChannelUserId("9001"),
                text=MessageText("A table for 4?"),
            )
            if with_message
            else None
        ),
    )


def queue(
    outbox: RecordingOutbox,
    jobs: RecordingJobQueue,
    event: InboundEventDocument,
    conversation_id: ConversationId,
    holding_id: MessageId,
) -> None:
    queue_holding_reply(outbox, jobs, event, conversation_id, holding_id, HOLDING, NOW)


def test_a_holding_message_is_one_customer_reply_with_its_own_key() -> None:
    outbox, jobs = RecordingOutbox(), RecordingJobQueue()
    event = customer_event(BusinessId(), ChannelId())
    assert event.business_id is not None and event.channel_id is not None
    conversation_id, holding_id = ConversationId(), MessageId()

    queue(outbox, jobs, event, conversation_id, holding_id)

    key = reply_idempotency_key(conversation_id, holding_id)
    stored = outbox.get(
        event.business_id, derive_outbound_message_id(event.business_id, key)
    )
    assert stored is not None
    assert stored.kind is OutboundMessageKind.CUSTOMER_REPLY
    assert stored.text == HOLDING
    assert stored.source_message_id == holding_id
    recipient = customer_recipient_key(event.channel_id, ChannelUserId("9001"))
    assert stored.recipient_key == recipient
    [call] = jobs.calls
    assert call.lane is JobLane.OUTBOUND
    assert call.serial_key == outbound_serial_key(event.business_id, recipient)
    # Sent now, ahead of the answer queued after it for the same recipient.
    assert call.run_at is None


@pytest.mark.parametrize(
    "event",
    [
        customer_event(None, ChannelId()),
        customer_event(BusinessId(), None),
        customer_event(BusinessId(), ChannelId(), with_message=False),
    ],
    ids=["platform event", "no channel", "no customer message"],
)
def test_an_event_without_a_customer_to_answer_queues_nothing(
    event: InboundEventDocument,
) -> None:
    outbox, jobs = RecordingOutbox(), RecordingJobQueue()

    queue(outbox, jobs, event, ConversationId(), MessageId())

    assert outbox.insert_depths == []
    assert jobs.calls == []


def test_a_retried_turn_queues_a_pending_holding_reply_again_but_stores_it_once() -> (
    None
):
    outbox, jobs = RecordingOutbox(), RecordingJobQueue()
    event = customer_event(BusinessId(), ChannelId())
    conversation_id, holding_id = ConversationId(), MessageId()

    queue(outbox, jobs, event, conversation_id, holding_id)
    queue(outbox, jobs, event, conversation_id, holding_id)

    # Its delivery job may have been lost with the crashed turn; delivery
    # itself is idempotent, so the customer still gets it once.
    assert len(jobs.calls) == 2
    assert outbox.insert_depths == [0, 0]
    assert len({call.payload for call in jobs.calls}) == 1


def test_a_holding_reply_already_delivered_is_not_sent_again() -> None:
    outbox, jobs = RecordingOutbox(), RecordingJobQueue()
    event = customer_event(BusinessId(), ChannelId())
    assert event.business_id is not None
    conversation_id, holding_id = ConversationId(), MessageId()
    queue(outbox, jobs, event, conversation_id, holding_id)
    key = reply_idempotency_key(conversation_id, holding_id)
    message_id = derive_outbound_message_id(event.business_id, key)
    stored = outbox.get(event.business_id, message_id)
    assert stored is not None
    outbox.upsert_for_test(
        stored.model_copy(update={"status": OutboundMessageStatus.DELIVERED})
    )

    queue(outbox, jobs, event, conversation_id, holding_id)

    assert len(jobs.calls) == 1


def test_a_holding_reply_whose_row_is_gone_is_not_queued() -> None:
    jobs = RecordingJobQueue()

    queue(
        VanishingOutbox(),
        jobs,
        customer_event(BusinessId(), ChannelId()),
        ConversationId(),
        MessageId(),
    )

    assert jobs.calls == []
