"""The sliding-window approximation of the shared rate limits."""

import pytest
from typed_time_provider import Microseconds

from app.schemas.dto.rate_limits import RateLimitBucketCounts, RateLimitCounter
from app.schemas.typings.platform.constrained_integers import (
    RateLimitRequestCount,
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.limits.sliding_window_limits import (
    bucket_expiry,
    is_within_limit,
    locate_window,
    previous_window_start,
    seconds_until_free,
)

SECOND: int = 1_000_000
MINUTE: RateWindowSeconds = RateWindowSeconds(60)
# 20 s into a minute.
NOW: Microseconds = Microseconds(1_790_000_000 * SECOND)
KEY: RateLimitKey = RateLimitKey("widget-message:platform")


def counts(current: int, previous: int) -> RateLimitBucketCounts:
    return RateLimitBucketCounts(
        key=KEY,
        current_count=RateLimitRequestCount(current),
        previous_count=RateLimitRequestCount(previous),
    )


def counter(limit: int) -> RateLimitCounter:
    return RateLimitCounter(key=KEY, limit=RequestsPerWindow(limit))


def test_a_moment_falls_in_one_fixed_window() -> None:
    window = locate_window(NOW, MINUTE)

    assert int(window.started_at) == int(NOW) - 20 * SECOND
    assert previous_window_start(window) == int(window.started_at) - 60 * SECOND
    assert bucket_expiry(window) == int(window.started_at) + 120 * SECOND


@pytest.mark.parametrize(
    ("current", "previous", "limit", "is_allowed"),
    [
        # 40 s of the previous minute are still inside: 2/3 of its weight.
        (10, 15, 20, True),  # 10 + 15 * 2/3 = 20
        (11, 15, 20, False),  # 11 + 10 = 21
        (20, 0, 20, True),
        (21, 0, 20, False),
        (1, 30, 20, False),  # 1 + 20 = 21
    ],
)
def test_the_estimate_weights_the_previous_window(
    current: int, previous: int, limit: int, is_allowed: bool
) -> None:
    window = locate_window(NOW, MINUTE)

    assert is_within_limit(counts(current, previous), counter(limit), window) is (
        is_allowed
    )


@pytest.mark.parametrize(
    ("current", "previous", "limit", "seconds"),
    [
        # Room in this window once the previous one's weight fades:
        # 5 + 30 * (60 - t) / 60 + 1 <= 20 from t = 32 s, 12 s from now.
        (5, 30, 20, 12),
        # This window is full: 40 s to its end, then 6 s for its weight.
        (20, 0, 20, 43),
        # One allowed per window: the full weight must fade, two windows.
        (1, 0, 1, 100),
        # Never less than a second.
        (0, 0, 20, 1),
    ],
)
def test_the_wait_until_one_more_request_fits(
    current: int, previous: int, limit: int, seconds: int
) -> None:
    window = locate_window(NOW, MINUTE)

    assert int(
        seconds_until_free(counts(current, previous), counter(limit), window)
    ) == (seconds)


def test_a_long_window_waits_at_most_a_day() -> None:
    day = RateWindowSeconds(24 * 60 * 60)
    window = locate_window(NOW, day)

    assert int(seconds_until_free(counts(1, 0), counter(1), window)) == 24 * 60 * 60
