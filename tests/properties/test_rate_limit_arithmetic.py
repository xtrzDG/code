"""
The sliding-window rate limit arithmetic (SDLC-07): a moment lies in the
window `locate_window` names; a lease grants exactly the requests the
limit still holds; more requests never fit where fewer did not; and after
the Retry-After `seconds_until_free` answers one more request fits.
"""

from hypothesis import given
from hypothesis import strategies as st
from typed_time_provider import Microseconds

from app.schemas.dto.rate_limits import (
    RateLimitBucketCounts,
    RateLimitCounter,
    RateLimitWindow,
)
from app.schemas.typings.platform.constrained_integers import (
    RateLimitLeaseSize,
    RateLimitRequestCount,
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.limits.sliding_window_limits import (
    MICROSECONDS_PER_SECOND,
    is_within_limit,
    lease_grant,
    locate_window,
    seconds_until_free,
    window_microseconds,
)

KEY: RateLimitKey = RateLimitKey("properties:client")
# 2026 in microseconds and a window of up to an hour: every wait stays
# below the 24-hour cap of a Retry-After.
moments = st.integers(min_value=1_767_225_600_000_000, max_value=1_798_761_600_000_000)
lengths = st.integers(min_value=1, max_value=3_600).map(RateWindowSeconds)
limits = st.integers(min_value=1, max_value=500).map(RequestsPerWindow)
counts = st.integers(min_value=0, max_value=1_500)


def bucket(previous: int, current: int) -> RateLimitBucketCounts:
    return RateLimitBucketCounts(
        key=KEY,
        current_count=RateLimitRequestCount(current),
        previous_count=RateLimitRequestCount(previous),
    )


def counter(limit: RequestsPerWindow) -> RateLimitCounter:
    return RateLimitCounter(key=KEY, limit=limit)


def fits_one_more(
    previous: int, current: int, limit: RequestsPerWindow, window: RateLimitWindow
) -> bool:
    return is_within_limit(bucket(previous, current + 1), counter(limit), window)


@given(moments, lengths)
def test_a_moment_lies_in_the_window_located_for_it(
    now: int, length: RateWindowSeconds
) -> None:
    window = locate_window(Microseconds(now), length)
    span = window_microseconds(length)

    assert int(window.started_at) <= now < int(window.started_at) + span
    assert int(window.started_at) % span == 0
    assert window.now == Microseconds(now)


@given(moments, lengths, limits, counts, counts, st.integers(1, 1_000))
def test_a_lease_grants_exactly_what_the_limit_still_holds(
    now: int,
    length: RateWindowSeconds,
    limit: RequestsPerWindow,
    previous: int,
    current: int,
    units: int,
) -> None:
    window = locate_window(Microseconds(now), length)

    granted = int(
        lease_grant(
            bucket(previous, current),
            counter(limit),
            RateLimitLeaseSize(units),
            window,
        )
    )

    assert 0 <= granted <= units
    if granted > 0:
        assert is_within_limit(
            bucket(previous, current + granted), counter(limit), window
        )
    if granted < units:
        assert not is_within_limit(
            bucket(previous, current + granted + 1), counter(limit), window
        )


@given(moments, lengths, limits, counts, counts, st.integers(0, 50), st.integers(0, 50))
def test_more_requests_never_fit_where_fewer_did_not(
    now: int,
    length: RateWindowSeconds,
    limit: RequestsPerWindow,
    previous: int,
    current: int,
    more_previous: int,
    more_current: int,
) -> None:
    window = locate_window(Microseconds(now), length)
    fewer = is_within_limit(bucket(previous, current), counter(limit), window)
    more = is_within_limit(
        bucket(previous + more_previous, current + more_current),
        counter(limit),
        window,
    )

    assert fewer or not more


@given(moments, lengths, limits, counts, counts)
def test_after_the_retry_after_one_more_request_fits(
    now: int,
    length: RateWindowSeconds,
    limit: RequestsPerWindow,
    previous: int,
    current: int,
) -> None:
    window = locate_window(Microseconds(now), length)
    wait = int(seconds_until_free(bucket(previous, current), counter(limit), window))

    later = locate_window(Microseconds(now + wait * MICROSECONDS_PER_SECOND), length)
    windows_ahead = (int(later.started_at) - int(window.started_at)) // (
        window_microseconds(length)
    )
    # Counts move one window back each window; nothing new arrives meanwhile.
    shifted: tuple[int, int] = {0: (previous, current), 1: (current, 0)}.get(
        windows_ahead, (0, 0)
    )

    assert 1 <= wait <= 2 * int(length) + 1
    assert fits_one_more(*shifted, limit, later)
