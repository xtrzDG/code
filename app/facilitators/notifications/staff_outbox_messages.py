"""Queueing one staff notification (a contact's or a device's) in the outbox."""

import logging

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.notifications import StaffDeliveryRecorderContract
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.schemas.constants.deliveries import OutboundMessageStatus
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.typings.deliveries.strings import DeliveryErrorText
from app.utilities.deliveries.delivery_jobs import (
    DELIVER_OUTBOUND_JOB,
    encode_outbound_message_payload,
)
from app.utilities.deliveries.delivery_keys import outbound_serial_key

logger: logging.Logger = logging.getLogger(__name__)

RATE_LIMITED_TEXT: DeliveryErrorText = DeliveryErrorText(
    "Too many notifications to this recipient in the last hour; this one was not sent."
)


def queue_outbox_message(
    message: OutboundMessageDocument,
    refusal: DeliveryErrorText | None,
    outbound_message_repo: OutboundMessageRepoContract,
    job_queue: JobQueueFacilitatorContract,
    delivery_recorder: StaffDeliveryRecorderContract,
) -> bool:
    """
    Store the message once (its id derives from its idempotency key) and
    queue its delivery job for when it is due (`next_attempt_at`: after
    quiet hours, else now). A refused message (no provider, rate limit) is
    stored as DEAD with the reason and not queued. The delivery state of
    its recipient follows. True when it is on its way.
    """

    if refusal is not None:
        message.status = OutboundMessageStatus.DEAD
        message.last_error = refusal

    if not outbound_message_repo.insert_if_new(message):
        stored: OutboundMessageDocument | None = outbound_message_repo.get(
            message.business_id, message.id
        )
        return stored is not None and stored.status is not OutboundMessageStatus.DEAD

    delivery_recorder.record(message)
    if refusal is not None:
        logger.warning("Staff notification cannot be delivered: %s", refusal)
        return False

    job_queue.enqueue(
        DELIVER_OUTBOUND_JOB,
        encode_outbound_message_payload(message.id),
        message.business_id,
        run_at=message.next_attempt_at,
        lane=JobLane.OUTBOUND,
        serial_key=outbound_serial_key(message.business_id, message.recipient_key),
    )
    return True
