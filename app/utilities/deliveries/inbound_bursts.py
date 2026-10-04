"""
Which inbox events of one customer are answered together, and when.

A customer who writes three quick messages gets one reply: the worker waits
until they have been quiet for MESSAGE_COALESCE_SECONDS, but never longer
than BURST_MAX_WAIT_FACTOR times that after their first message, so a
customer who keeps typing is still answered.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.deliveries import InboundEventKind
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.typings.conversations.constrained_integers import (
    MessageCoalesceSeconds,
)
from app.utilities.deliveries.inbound_claims import (
    MICROSECONDS_PER_SECOND,
    is_inbound_event_finished,
    is_inbound_event_held,
)

BURST_MAX_WAIT_FACTOR: int = 3
# The other messages of a burst are looked for this long around the job's
# own one (a backlog is answered in bursts of this span at most).
BURST_WINDOW_SECONDS: int = 60


def is_customer_event(event: InboundEventDocument) -> bool:
    return (
        event.kind is InboundEventKind.CUSTOMER_MESSAGE
        and event.customer_message is not None
        and event.business_id is not None
    )


def is_same_customer(event: InboundEventDocument, other: InboundEventDocument) -> bool:
    """Messages of one customer in one channel of one business."""

    return (
        event.customer_message is not None
        and other.customer_message is not None
        and event.business_id == other.business_id
        and event.channel is other.channel
        and event.channel_id == other.channel_id
        and event.customer_message.channel_user_id
        == other.customer_message.channel_user_id
    )


def is_open_event(event: InboundEventDocument, now: Microseconds) -> bool:
    """Not answered yet and not being answered by another worker."""

    return not is_inbound_event_finished(event) and not is_inbound_event_held(
        event, now
    )


def burst_window(event: InboundEventDocument) -> tuple[Microseconds, Microseconds]:
    """Where the other messages of an event's burst are looked for."""

    span: int = BURST_WINDOW_SECONDS * MICROSECONDS_PER_SECOND
    return (
        Microseconds(int(event.created_at) - span),
        Microseconds(int(event.created_at) + span + 1),
    )


def select_burst(
    trigger: InboundEventDocument,
    candidates: list[InboundEventDocument],
    now: Microseconds,
) -> list[InboundEventDocument]:
    """
    The trigger and the same customer's other open messages, oldest first
    (by when the platform delivered them; the inbox order breaks ties).
    """

    burst: dict[str, InboundEventDocument] = {str(trigger.id): trigger}
    for event in candidates:
        if is_same_customer(trigger, event) and is_open_event(event, now):
            burst.setdefault(str(event.id), event)

    return sorted(burst.values(), key=lambda event: int(event.created_at))


def burst_answer_at(
    burst: list[InboundEventDocument],
    coalesce_seconds: MessageCoalesceSeconds,
) -> Microseconds:
    """
    When the burst is answered: `coalesce_seconds` after its newest message,
    at the latest BURST_MAX_WAIT_FACTOR times that after its first.
    """

    quiet: int = int(coalesce_seconds) * MICROSECONDS_PER_SECOND
    newest: int = max(int(event.created_at) for event in burst)
    oldest: int = min(int(event.created_at) for event in burst)
    return Microseconds(min(newest + quiet, oldest + quiet * BURST_MAX_WAIT_FACTOR))
