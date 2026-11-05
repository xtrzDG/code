"""
One process's leases of shared rate-limit counters (`RateLimitLeases`) at
the edges: the request that finds a fifth of a lease left tops it up
ahead (once a window's limit is used up, no more), a request that read the
clock just before a window ended uses the next window's units, a lease of
an older window never replaces a newer one, a unit given back while its
lease is topped up is kept, one whose lease a newer window replaced stays
counted unused, and a request whose per-request count fails gives its
leased units back.
"""

from collections.abc import Sequence

import pytest
from typed_time_provider import Microseconds

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.registries.limits.rate_limit_leases import RateLimitLeases, TakenUnit
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.schemas.dto.rate_limits import RateLimitCounter, RateLimitWindow
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.constrained_integers import (
    RateLimitLeaseGrant,
    RateLimitLeaseSize,
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.limits.sliding_window_limits import locate_window

SECOND: int = 1_000_000
MINUTE: RateWindowSeconds = RateWindowSeconds(60)
START: int = 1_789_999_980 * SECOND
UNITS: RateLimitLeaseSize = RateLimitLeaseSize(3)
BUSINESS: RateLimitCounter = RateLimitCounter(
    key=RateLimitKey("widget-poll:business:biz_1"),
    limit=RequestsPerWindow(1_000),
    lease_size=UNITS,
)


def at(seconds: int) -> RateLimitWindow:
    return locate_window(Microseconds(START + seconds * SECOND), MINUTE)


class LeaseCounting(InMemoryRateLimitBucketAdapter):
    """Shared counters that count leases (and may act while granting one)."""

    def __init__(self) -> None:
        super().__init__()
        self.leases: int = 0
        self.while_leasing: list[TakenUnit] = []
        self.book: RateLimitLeases | None = None

    def lease_within(
        self,
        counter: RateLimitCounter,
        units: RateLimitLeaseSize,
        window: RateLimitWindow,
    ) -> RateLimitLeaseGrant:
        self.leases += 1
        if self.book is not None and self.while_leasing:
            # Another thread's refused request returns its unit meanwhile.
            self.book.give_back(self.while_leasing)
            self.while_leasing = []
        return super().lease_within(counter, units, window)


def counter_of(limit: int, units: int) -> RateLimitCounter:
    return RateLimitCounter(
        key=BUSINESS.key,
        limit=RequestsPerWindow(limit),
        lease_size=RateLimitLeaseSize(units),
    )


def take_times(
    book: RateLimitLeases, counter: RateLimitCounter, seconds: int, times: int
) -> list[TakenUnit | None]:
    units = counter.lease_size or UNITS
    return [book.take(counter, units, at(seconds)) for _ in range(times)]


def test_a_low_lease_is_topped_up_ahead_until_the_limit_is_used_up() -> None:
    buckets = LeaseCounting()
    book = RateLimitLeases(buckets)
    ten = counter_of(1_000, 10)

    take_times(book, ten, 5, 8)
    before_low = buckets.leases
    take_times(book, ten, 5, 1)  # leaves one of ten: below a fifth

    twelve = counter_of(12, 10)
    other = LeaseCounting()
    capped = RateLimitLeases(other)
    taken = take_times(capped, twelve, 5, 12)
    refused = capped.take(twelve, RateLimitLeaseSize(10), at(6))

    assert (before_low, buckets.leases) == (1, 2)
    # Ten, then two more ahead, then none: no more tries in this window
    # until nothing is left, and then one that finds the limit used up.
    assert all(unit is not None for unit in taken)
    assert refused is None
    assert other.leases == 4


def test_a_late_request_uses_the_next_windows_units() -> None:
    buckets = LeaseCounting()
    book = RateLimitLeases(buckets)

    first = book.take(BUSINESS, UNITS, at(61))
    late = book.take(BUSINESS, UNITS, at(59))

    assert first is not None and late is not None
    assert late.window_start == at(61).started_at
    assert buckets.leases == 1


def test_an_older_windows_lease_never_replaces_a_newer_one() -> None:
    buckets = LeaseCounting()
    book = RateLimitLeases(buckets)
    three = counter_of(3, 3)
    take_times(book, three, 61, 3)  # the minute's limit, used up

    late = book.take(three, UNITS, at(59))
    later = book.take(three, UNITS, at(58))

    # The late request leased in its own minute and admitted one; the rest
    # of that lease was dropped, not held (it would have served the next
    # late request without a lease): it stays counted, so the next late
    # request finds the earlier minute's limit used up.
    assert late is not None and late.window_start == at(59).started_at
    assert later is None
    assert buckets.leases == 4


def test_a_unit_given_back_while_the_lease_is_topped_up_is_kept() -> None:
    buckets = LeaseCounting()
    book = RateLimitLeases(buckets)
    buckets.book = book
    first, _ = take_times(book, BUSINESS, 5, 2)
    assert first is not None
    buckets.while_leasing = [first]

    take_times(book, BUSINESS, 5, 1)  # the last unit: topped up ahead
    take_times(book, BUSINESS, 6, 3)

    # The new lease's three units and the one given back: four, so three
    # more takes need no lease.
    assert buckets.leases == 2


def test_a_unit_whose_lease_was_replaced_stays_counted_unused() -> None:
    buckets = LeaseCounting()
    book = RateLimitLeases(buckets)
    old = book.take(BUSINESS, UNITS, at(5))
    assert old is not None
    newer = book.take(BUSINESS, UNITS, at(65))
    assert newer is not None

    book.give_back([old])
    take_times(book, BUSINESS, 66, 2)

    # The old minute's unit did not join the newer lease: its last unit
    # went now, and it was topped up ahead.
    assert buckets.leases == 3


class FailingCounts(LeaseCounting):
    def count_if_within(
        self, counters: Sequence[RateLimitCounter], window: RateLimitWindow
    ) -> RateLimitKey | None:
        raise ExternalServiceError("The database failed.")


def test_a_failed_per_request_count_gives_the_leased_units_back() -> None:
    buckets = FailingCounts()
    registry = RequestRateLimitRegistry(buckets)
    visitor = RateLimitCounter(
        key=RateLimitKey("widget-poll:visitor:biz_1:v1"), limit=RequestsPerWindow(10)
    )
    now = Microseconds(START + 5 * SECOND)

    for _ in range(10):
        with pytest.raises(ExternalServiceError):
            registry.try_acquire_all([visitor, BUSINESS], MINUTE, now)

    # Every failed request returned its unit: the first lease still serves.
    assert buckets.leases == 1
