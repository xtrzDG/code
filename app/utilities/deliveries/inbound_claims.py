"""
Who may process an inbox event now: the first taker of a stored event,
the next one after the holder's lease ran out (its worker died), or at
once a later attempt of the very job that holds it. The queue runs a job
in one place at a time, so that job's earlier attempt is over (its worker
died and the reaper put the job back): the customer is answered within
moments of the job lease's end, not after the processing lease. A
finished event is never processed again.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.deliveries import InboundEventStatus
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.typings.deliveries.constrained_integers import (
    InboundProcessingAttemptCount,
    QueueToClaimMilliseconds,
)
from app.schemas.typings.platform.prefixed_id import QueuedJobId

MICROSECONDS_PER_SECOND: int = 1_000_000
MICROSECONDS_PER_MILLISECOND: int = 1_000
# How long one processing of an event may hold it: longer than any turn of
# the model with its tools (a request or job that runs longer is dead).
INBOUND_PROCESSING_LEASE_SECONDS: int = 180
FINISHED_INBOUND_STATUSES: frozenset[InboundEventStatus] = frozenset(
    {
        InboundEventStatus.ANSWERED,
        InboundEventStatus.HANDED_OFF,
        InboundEventStatus.FAILED,
    }
)


def inbound_lease_end(now: Microseconds) -> Microseconds:
    return Microseconds(
        int(now) + INBOUND_PROCESSING_LEASE_SECONDS * MICROSECONDS_PER_SECOND
    )


def is_inbound_event_finished(event: InboundEventDocument) -> bool:
    return event.status in FINISHED_INBOUND_STATUSES


def is_inbound_event_held(event: InboundEventDocument, now: Microseconds) -> bool:
    """Processing right now under a lease that has not run out."""

    return (
        event.status is InboundEventStatus.PROCESSING
        and event.lease_until is not None
        and event.lease_until > now
    )


def is_inbound_event_held_by_another(
    event: InboundEventDocument, now: Microseconds, job_id: QueuedJobId
) -> bool:
    """Held right now by a processing other than an attempt of `job_id`."""

    return is_inbound_event_held(event, now) and event.holder_job_id != job_id


def take_inbound_event(
    event: InboundEventDocument,
    now: Microseconds,
    job_id: QueuedJobId,
) -> InboundEventDocument | None:
    """
    The event as held by job `job_id` until `inbound_lease_end(now)`, or
    None when it is finished or held by another processing. The first take
    records how long the event waited since it was queued.
    """

    if is_inbound_event_finished(event) or is_inbound_event_held_by_another(
        event, now, job_id
    ):
        return None

    event.status = InboundEventStatus.PROCESSING
    event.attempts = InboundProcessingAttemptCount(int(event.attempts) + 1)
    event.lease_until = inbound_lease_end(now)
    event.holder_job_id = job_id
    event.updated_at = now
    if event.queue_to_claim_ms is None:
        event.queue_to_claim_ms = queue_to_claim(event, now)

    return event


def queue_to_claim(
    event: InboundEventDocument, now: Microseconds
) -> QueueToClaimMilliseconds:
    """Milliseconds since the event was stored and queued (0 for a clock step back)."""

    waited: int = max(0, int(now) - int(event.created_at))
    return QueueToClaimMilliseconds(waited // MICROSECONDS_PER_MILLISECOND)
