"""
The sliding-window approximation of request rate limits.

Requests are counted in fixed windows (one counter per key and window).
The requests of the last full window length before a moment are estimated
as the current window's count plus the previous window's count weighted by
the part of it that still lies inside the sliding window:

    estimate = previous * (length - elapsed) / length + current

This is how shared counters keep a sliding limit with two numbers per key
instead of one timestamp per request; it assumes the previous window's
requests were spread evenly, which errs by a few per cent at most.
"""

from typed_time_provider import Microseconds

from app.schemas.dto.rate_limits import (
    RateLimitBucketCounts,
    RateLimitCounter,
    RateLimitWindow,
)
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RetryAfterSeconds,
)

MICROSECONDS_PER_SECOND: int = 1_000_000
LONGEST_RETRY_AFTER_SECONDS: int = 24 * 60 * 60


def locate_window(now: Microseconds, length: RateWindowSeconds) -> RateLimitWindow:
    """The fixed window of `length` that holds `now`."""

    length_microseconds: int = window_microseconds(length)
    return RateLimitWindow(
        length_seconds=length,
        started_at=Microseconds(int(now) - int(now) % length_microseconds),
        now=now,
    )


def window_microseconds(length: RateWindowSeconds) -> int:
    return int(length) * MICROSECONDS_PER_SECOND


def previous_window_start(window: RateLimitWindow) -> int:
    return int(window.started_at) - window_microseconds(window.length_seconds)


def bucket_expiry(window: RateLimitWindow) -> int:
    """
    When the window's counter is no longer needed: the end of the next
    window (until then it is that window's previous one).
    """

    return int(window.started_at) + 2 * window_microseconds(window.length_seconds)


def is_within_limit(
    counts: RateLimitBucketCounts,
    counter: RateLimitCounter,
    window: RateLimitWindow,
) -> bool:
    """
    Whether the estimate, the request itself counted, stays within the limit.

    The Postgres counters decide the same inequality inside the database
    (`workshop.count_request_within_limits`, migration 1135); keep the two
    in step (`tests/storage/test_rate_limit_parity.py`).
    """

    length: int = window_microseconds(window.length_seconds)
    elapsed: int = int(window.now) - int(window.started_at)
    weighted: int = (
        int(counts.previous_count) * (length - elapsed)
        + int(counts.current_count) * length
    )
    return weighted <= int(counter.limit) * length


def seconds_until_free(
    counts: RateLimitBucketCounts,
    counter: RateLimitCounter,
    window: RateLimitWindow,
) -> RetryAfterSeconds:
    """
    Whole seconds until one more request fits the limit (the Retry-After of
    a refused request, at least 1): later in this window, when the previous
    window's weight has faded enough, or in a later window.
    """

    length: int = window_microseconds(window.length_seconds)
    elapsed: int = int(window.now) - int(window.started_at)
    previous, current = int(counts.previous_count), int(counts.current_count)
    room: int = int(counter.limit) - current - 1
    wait: int
    if room > 0 and previous > 0:
        # previous * (length - at) <= room * length
        wait = max(0, length - room * length // previous - elapsed)
    elif room >= 0 and previous == 0:
        wait = 0
    else:
        # In the next window this window's requests are the previous ones.
        next_window_offset: int = (
            0
            if current == 0
            else max(0, length - (int(counter.limit) - 1) * length // current)
        )
        wait = length - elapsed + next_window_offset

    return RetryAfterSeconds(
        min(LONGEST_RETRY_AFTER_SECONDS, max(1, -(-wait // MICROSECONDS_PER_SECOND)))
    )
