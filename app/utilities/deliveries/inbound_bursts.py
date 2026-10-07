"""
Which inbox events of one customer are answered together, and when.

A customer who writes three quick messages gets one reply, and a customer
who writes one finished question is not kept waiting for messages that
will not come:

- when their newest message reads as finished (a sentence of more than 12
  characters that ends with ".", "?" or "!", `message_completeness`), the
  burst is answered at once;
- after a fragment ("Hi", "table for 4") the worker waits until they have
  been quiet for MESSAGE_COALESCE_SECONDS; on Telegram, where customers
  write in quick short lines and a bot never learns they are typing, for
  1.5 s;
- never longer than BURST_MAX_WAIT_FACTOR times that wait after their
  first message, so a customer who keeps typing is still answered.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import InboundEventKind
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.typings.conversations.constrained_integers import (
    MessageCoalesceSeconds,
)
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.utilities.deliveries.inbound_claims import (
    MICROSECONDS_PER_SECOND,
    is_inbound_event_finished,
    is_inbound_event_held_by_another,
)
from app.utilities.deliveries.message_completeness import is_complete_message

BURST_MAX_WAIT_FACTOR: int = 3
# The other messages of a burst are looked for this long around the job's
# own one (a backlog is answered in bursts of this span at most).
BURST_WINDOW_SECONDS: int = 60
# The wait after a fragment on channels whose customers write in quick
# short lines and whose bots never learn that the customer is typing.
QUICK_LINES_WAIT_MICROSECONDS: int = 1_500_000
QUICK_LINE_CHANNELS: frozenset[ChannelKind] = frozenset({ChannelKind.TELEGRAM})


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


def is_open_event(
    event: InboundEventDocument, now: Microseconds, job_id: QueuedJobId
) -> bool:
    """Not answered yet and not being answered by another job than `job_id`."""

    return not is_inbound_event_finished(
        event
    ) and not is_inbound_event_held_by_another(event, now, job_id)


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
    job_id: QueuedJobId,
) -> list[InboundEventDocument]:
    """
    The trigger and the same customer's other open messages, oldest first
    (by when the platform delivered them; the inbox order breaks ties).
    Messages job `job_id` held on an attempt its worker died in are open.
    """

    burst: dict[str, InboundEventDocument] = {str(trigger.id): trigger}
    for event in candidates:
        if is_same_customer(trigger, event) and is_open_event(event, now, job_id):
            burst.setdefault(str(event.id), event)

    return sorted(burst.values(), key=lambda event: int(event.created_at))


def fragment_wait(
    channel: ChannelKind, coalesce_seconds: MessageCoalesceSeconds
) -> int:
    """Microseconds of quiet the customer gets after a fragment."""

    wait: int = int(coalesce_seconds) * MICROSECONDS_PER_SECOND
    if channel in QUICK_LINE_CHANNELS:
        return min(wait, QUICK_LINES_WAIT_MICROSECONDS)

    return wait


def is_finished_message(event: InboundEventDocument) -> bool:
    """The customer's message reads as a finished sentence."""

    return event.customer_message is not None and is_complete_message(
        event.customer_message.text
    )


def burst_answer_at(
    burst: list[InboundEventDocument],
    coalesce_seconds: MessageCoalesceSeconds,
) -> Microseconds:
    """
    When the burst is answered: at its newest message when that one reads
    as finished, else the fragment wait after it; at the latest
    BURST_MAX_WAIT_FACTOR fragment waits after its first message.
    """

    newest_event: InboundEventDocument = max(
        burst, key=lambda event: int(event.created_at)
    )
    wait: int = fragment_wait(newest_event.channel, coalesce_seconds)
    quiet: int = 0 if is_finished_message(newest_event) else wait
    newest: int = int(newest_event.created_at)
    oldest: int = min(int(event.created_at) for event in burst)
    return Microseconds(min(newest + quiet, oldest + wait * BURST_MAX_WAIT_FACTOR))
