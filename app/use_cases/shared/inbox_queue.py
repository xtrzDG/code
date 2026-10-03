"""Storing an event in the inbox and queuing the job that processes it."""

from typed_time_provider import Microseconds

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.delivery_repositories import InboundEventRepoContract
from app.schemas.constants.deliveries import InboundEventStatus
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.utilities.deliveries.delivery_jobs import encode_inbound_event_payload


def store_and_queue(
    event_repo: InboundEventRepoContract,
    job_queue: JobQueueFacilitatorContract,
    event: InboundEventDocument,
    job_name: JobName,
    serial_key: JobSerialKey | None,
    run_at: Microseconds | None = None,
) -> bool:
    """
    Store a new event and queue its job on the inbound lane; True for a new
    event. A redelivered event is not stored again, but when it is still
    RECEIVED (the first request may have died between storing and queuing)
    its job is queued once more: processing an event twice is harmless,
    the job finds it finished.
    """

    if event_repo.insert_if_new(event):
        queue_inbound_job(job_queue, event, job_name, serial_key, run_at)
        return True

    stored: InboundEventDocument | None = event_repo.get(event.business_id, event.id)
    if stored is not None and stored.status is InboundEventStatus.RECEIVED:
        queue_inbound_job(job_queue, stored, job_name, serial_key, run_at)

    return False


def queue_inbound_job(
    job_queue: JobQueueFacilitatorContract,
    event: InboundEventDocument,
    job_name: JobName,
    serial_key: JobSerialKey | None,
    run_at: Microseconds | None = None,
) -> None:
    job_queue.enqueue(
        job_name,
        encode_inbound_event_payload(event.id),
        event.business_id,
        run_at=run_at,
        lane=JobLane.INBOUND,
        serial_key=serial_key,
    )
