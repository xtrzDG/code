"""
When a webhook delivery is tried again: after 30 s, 2 min, 10 min, 30 min,
then every 1, 2, 4, 6 and 8 hours, each moved by up to a fifth either way
(deliveries that failed together, a receiver's outage, come back spread
out), and never after the delivery's 24 hours ran out.
"""

MICROSECONDS_PER_SECOND: int = 1_000_000
# How long a delivery is tried, from the event on.
DELIVERY_WINDOW_SECONDS: int = 24 * 60 * 60
# How long the delivery log keeps a delivery.
DELIVERY_RETENTION_SECONDS: int = 30 * 24 * 60 * 60
RETRY_DELAYS_SECONDS: tuple[int, ...] = (
    30,
    2 * 60,
    10 * 60,
    30 * 60,
    60 * 60,
    2 * 60 * 60,
    4 * 60 * 60,
    6 * 60 * 60,
    8 * 60 * 60,
)
JITTER_SHARE: float = 0.2


def retry_delay_seconds(failed_attempts: int, jitter_fraction: float) -> int:
    """
    Seconds until the next attempt after `failed_attempts` failed ones
    (`jitter_fraction` in [0, 1); 0.5 means no jitter).
    """

    index: int = min(max(failed_attempts, 1), len(RETRY_DELAYS_SECONDS)) - 1
    base: int = RETRY_DELAYS_SECONDS[index]
    bounded: float = min(max(jitter_fraction, 0.0), 1.0)
    return max(1, round(base * (1 + JITTER_SHARE * (2 * bounded - 1))))


def give_up_moment(created_at_microseconds: int) -> int:
    """The moment after which a delivery is not tried again."""

    return created_at_microseconds + DELIVERY_WINDOW_SECONDS * MICROSECONDS_PER_SECOND


def expiry_moment(created_at_microseconds: int) -> int:
    """The moment the delivery log forgets a delivery."""

    return (
        created_at_microseconds + DELIVERY_RETENTION_SECONDS * MICROSECONDS_PER_SECOND
    )
