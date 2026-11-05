"""Queuing the holding reply in the outbox, like every assistant reply."""

from typed_time_provider import Microseconds

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.schemas.constants.deliveries import OutboundMessageKind, OutboundMessageStatus
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.outbound_messages import (
    CustomerRecipient,
    OutboundMessageDocument,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deliveries.constrained_strings import (
    OutboundIdempotencyKey,
    OutboundRecipientKey,
)
from app.utilities.deliveries.delivery_jobs import (
    DELIVER_OUTBOUND_JOB,
    encode_outbound_message_payload,
)
from app.utilities.deliveries.delivery_keys import (
    customer_recipient_key,
    derive_outbound_message_id,
    outbound_serial_key,
    reply_idempotency_key,
)


def queue_holding_reply(
    outbound_message_repo: OutboundMessageRepoContract,
    job_queue: JobQueueFacilitatorContract,
    event: InboundEventDocument,
    conversation_id: ConversationId,
    holding_id: MessageId,
    text: MessageText,
    now: Microseconds,
) -> None:
    """
    One CUSTOMER_REPLY per holding message (its own idempotency key), sent
    to the customer before the answer queued after it. The website widget
    has no outbox: it reads the stored message.
    """

    if (
        event.business_id is None
        or event.channel_id is None
        or event.customer_message is None
    ):
        return

    idempotency_key: OutboundIdempotencyKey = reply_idempotency_key(
        conversation_id, holding_id
    )
    recipient_key: OutboundRecipientKey = customer_recipient_key(
        event.channel_id, event.customer_message.channel_user_id
    )
    message = OutboundMessageDocument(
        id=derive_outbound_message_id(event.business_id, idempotency_key),
        business_id=event.business_id,
        kind=OutboundMessageKind.CUSTOMER_REPLY,
        idempotency_key=idempotency_key,
        recipient_key=recipient_key,
        customer=CustomerRecipient(
            channel_id=event.channel_id,
            channel=event.channel,
            channel_user_id=event.customer_message.channel_user_id,
        ),
        text=text,
        conversation_id=conversation_id,
        source_message_id=holding_id,
        created_at=now,
        updated_at=now,
    )
    if not outbound_message_repo.insert_if_new(message):
        stored: OutboundMessageDocument | None = outbound_message_repo.get(
            event.business_id, message.id
        )
        if stored is None or stored.status is not OutboundMessageStatus.PENDING:
            return

    job_queue.enqueue(
        DELIVER_OUTBOUND_JOB,
        encode_outbound_message_payload(message.id),
        event.business_id,
        lane=JobLane.OUTBOUND,
        serial_key=outbound_serial_key(event.business_id, recipient_key),
    )
