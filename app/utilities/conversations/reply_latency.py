"""How long a customer waited for a reply."""

from typed_time_provider import Microseconds

from app.schemas.typings.conversations.constrained_integers import (
    ReplyLatencyMilliseconds,
)

MICROSECONDS_PER_MILLISECOND: int = 1_000


def measure_reply_latency(
    waiting_since: Microseconds | None,
    replied_at: Microseconds,
) -> ReplyLatencyMilliseconds | None:
    """
    Milliseconds from the customer's first unanswered message to the
    stored reply; None when the wait was not measured. A clock that went
    backwards between processes counts as no wait.
    """

    if waiting_since is None:
        return None

    return ReplyLatencyMilliseconds(
        max(0, int(replied_at) - int(waiting_since)) // MICROSECONDS_PER_MILLISECOND
    )
