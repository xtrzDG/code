"""
Who may process an inbox event now: the first taker of a stored event,
or the next one after the holder's lease ran out (its worker or request
died). A finished event is never processed again.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.deliveries import InboundEventStatus
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.typings.deliveries.constrained_integers import (
    InboundProcessingAttemptCount,
)

MICROSECONDS_PER_SECOND: int = 1_000_000
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


def take_inbound_event(
    event: InboundEventDocument,
    now: Microseconds,
) -> InboundEventDocument | None:
    """
    The event as held by a new processing until `inbound_lease_end(now)`,
    or None when it is finished or held by another processing.
    """

    if is_inbound_event_finished(event) or is_inbound_event_held(event, now):
        return None

    event.status = InboundEventStatus.PROCESSING
    event.attempts = InboundProcessingAttemptCount(int(event.attempts) + 1)
    event.lease_until = inbound_lease_end(now)
    event.updated_at = now
    return event
