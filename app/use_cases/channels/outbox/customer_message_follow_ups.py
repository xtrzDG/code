"""
What the delivery of a message to a customer changes besides the outbox:
the conversation card that shows a staff reply's delivery state, and the
text-back of a missed call, which goes on once WhatsApp delivered or
refused its template.
"""

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.live_events import EventPublisherFacilitatorContract
from app.schemas.constants.deliveries import OutboundMessageKind, OutboundMessageStatus
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.utilities.calls.text_back_jobs import (
    SEND_TEXT_BACK_JOB,
    encode_text_back_payload,
)

SETTLED_STATUSES: frozenset[OutboundMessageStatus] = frozenset(
    {OutboundMessageStatus.DELIVERED, OutboundMessageStatus.DEAD}
)


def announce_staff_reply_delivery(
    live_events: EventPublisherFacilitatorContract,
    message: OutboundMessageDocument,
) -> None:
    """
    Every attempt of a staff reply changes what its conversation card shows
    next to it (sending, retrying, failed, delivered): open cabinets reload
    the card.
    """

    if (
        message.kind is not OutboundMessageKind.STAFF_REPLY
        or message.conversation_id is None
    ):
        return

    live_events.publish(
        message.business_id,
        LiveEventKind.CONVERSATION_MESSAGE,
        (message.conversation_id,),
    )


def continue_text_back(
    job_queue: JobQueueFacilitatorContract,
    message: OutboundMessageDocument,
) -> None:
    """
    A text-back's WhatsApp template was delivered or given up: its
    `send_missed_call_text_back` job runs again to record it (and to send
    the SMS fallback after a refusal).
    """

    if message.missed_call_id is None or message.status not in SETTLED_STATUSES:
        return

    job_queue.enqueue(
        SEND_TEXT_BACK_JOB,
        encode_text_back_payload(message.missed_call_id),
        message.business_id,
        lane=JobLane.OUTBOUND,
    )
