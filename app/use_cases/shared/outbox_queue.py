"""Putting a message into the outbox together with the job that sends it."""

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.contracts.storage import StorageUnitOfWorkContract
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.use_cases.shared.storage_transaction import in_unit_of_work
from app.utilities.deliveries.delivery_jobs import (
    DELIVER_OUTBOUND_JOB,
    encode_outbound_message_payload,
)
from app.utilities.deliveries.delivery_keys import outbound_serial_key


def queue_outbound_message(
    outbound_message_repo: OutboundMessageRepoContract,
    job_queue: JobQueueFacilitatorContract,
    message: OutboundMessageDocument,
    unit_of_work: StorageUnitOfWorkContract | None,
) -> OutboundMessageDocument:
    """
    Store a new outbox message and queue its `deliver_outbound` job (the
    outbound lane, one recipient's messages one at a time) in one unit of
    work, so neither exists without the other: the worker retries it until
    it is delivered or given up. A message whose idempotency key was queued
    before is not queued again; the stored one is returned.
    """

    with in_unit_of_work(unit_of_work):
        if outbound_message_repo.insert_if_new(message):
            job_queue.enqueue(
                DELIVER_OUTBOUND_JOB,
                encode_outbound_message_payload(message.id),
                message.business_id,
                run_at=message.next_attempt_at,
                lane=JobLane.OUTBOUND,
                serial_key=outbound_serial_key(
                    message.business_id, message.recipient_key
                ),
            )
            return message

    stored: OutboundMessageDocument | None = outbound_message_repo.get(
        message.business_id, message.id
    )
    return message if stored is None else stored
