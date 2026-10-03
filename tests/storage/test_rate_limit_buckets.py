"""
Shared request counters, in memory and in Postgres alike: all or nothing,
no trace of a refused request, the previous window weighed in, a sweep of
what no limit needs, and on Postgres one limit for many sessions at once.
"""

import threading
from collections.abc import Generator

import pytest
from typed_time_provider import Microseconds

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.adapters.rate_limits.postgres_rate_limit_bucket_adapter import (
    PostgresRateLimitBucketAdapter,
    read_count,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.rate_limits import RateLimitBucketAdapterContract
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.limits.sliding_window_limits import locate_window

SECOND: int = 1_000_000
MINUTE: RateWindowSeconds = RateWindowSeconds(60)
# The start of a minute.
WINDOW_START: Microseconds = Microseconds(1_789_999_980 * SECOND)
VISITOR: RateLimitKey = RateLimitKey("widget-message:visitor:biz_1:v1")
PLATFORM: RateLimitKey = RateLimitKey("widget-message:platform")


def counter(key: RateLimitKey, limit: int) -> RateLimitCounter:
    return RateLimitCounter(key=key, limit=RequestsPerWindow(limit))


def at(seconds: int) -> Microseconds:
    return Microseconds(int(WINDOW_START) + seconds * SECOND)


@pytest.fixture(params=["in_memory", "postgres"])
def buckets(
    request: pytest.FixtureRequest,
) -> Generator[RateLimitBucketAdapterContract]:
    if request.param == "in_memory":
        yield InMemoryRateLimitBucketAdapter()
        return

    database_url: DatabaseUrl = request.getfixturevalue("database_url")
    pool = PostgresConnectionPoolClient(database_url, max_size=2)
    try:
        yield PostgresRateLimitBucketAdapter(pool)
    finally:
        pool.close()


def test_a_request_counts_for_every_counter_or_for_none(
    buckets: RateLimitBucketAdapterContract,
) -> None:
    registry = RequestRateLimitRegistry(buckets)
    counters = [counter(VISITOR, 2), counter(PLATFORM, 100)]

    assert registry.try_acquire_all(counters, MINUTE, at(1)) is None
    assert registry.try_acquire_all(counters, MINUTE, at(2)) is None
    assert registry.try_acquire_all(counters, MINUTE, at(3)) == VISITOR

    window = locate_window(at(3), MINUTE)
    assert int(buckets.read_counts(VISITOR, window).current_count) == 2
    # The refused request did not count for the platform either.
    assert int(buckets.read_counts(PLATFORM, window).current_count) == 2
    # Another visitor still gets through, and one key named twice counts once.
    other = RateLimitKey("widget-message:visitor:biz_1:v2")
    assert (
        registry.try_acquire_all(
            [counter(other, 2), counter(other, 2), counter(PLATFORM, 100)],
            MINUTE,
            at(4),
        )
        is None
    )
    assert int(buckets.read_counts(other, window).current_count) == 1


def test_a_refused_first_request_creates_no_counter(
    buckets: RateLimitBucketAdapterContract,
) -> None:
    registry = RequestRateLimitRegistry(buckets)
    full = RateLimitKey("otp-check:address:203.0.113.7")
    fresh = RateLimitKey("otp-check:challenge:otp_1")
    registry.try_acquire_all([counter(full, 1)], MINUTE, at(1))

    refused = registry.try_acquire_all(
        [counter(fresh, 5), counter(full, 1)], MINUTE, at(2)
    )

    assert refused == full
    assert (
        int(buckets.read_counts(fresh, locate_window(at(2), MINUTE)).current_count) == 0
    )
    assert int(buckets.delete_expired(at(10 * 60))) == 1


def test_the_previous_window_fades_out(buckets: RateLimitBucketAdapterContract) -> None:
    registry = RequestRateLimitRegistry(buckets)
    limit = counter(VISITOR, 10)
    for second in range(10):
        assert registry.try_acquire_all([limit], MINUTE, at(second)) is None

    # 15 s into the next minute, 3/4 of the ten still count: room for 2.
    assert registry.try_acquire_all([limit], MINUTE, at(75)) is None
    assert registry.try_acquire_all([limit], MINUTE, at(75)) is None
    assert registry.try_acquire_all([limit], MINUTE, at(75)) == VISITOR
    # 10 * (60 - t) / 60 + 2 + 1 <= 10 from t = 18 s: in 3 s.
    assert int(registry.seconds_until_free(limit, MINUTE, at(75))) == 3
    assert registry.try_acquire_all([limit], MINUTE, at(77)) == VISITOR
    assert registry.try_acquire_all([limit], MINUTE, at(78)) is None


def test_the_sweep_drops_only_counters_no_window_needs(
    buckets: RateLimitBucketAdapterContract,
) -> None:
    registry = RequestRateLimitRegistry(buckets)
    registry.try_acquire_all([counter(VISITOR, 5)], MINUTE, at(1))
    registry.try_acquire_all([counter(PLATFORM, 5)], MINUTE, at(61))

    # The first minute's counter is still the second minute's previous one.
    assert int(registry.forget_expired(at(119))) == 0
    assert int(registry.forget_expired(at(120))) == 1
    assert int(registry.forget_expired(at(180))) == 1
    assert int(registry.forget_expired(at(180))) == 0


def test_many_sessions_share_one_limit_on_postgres(database_url: DatabaseUrl) -> None:
    pools = [PostgresConnectionPoolClient(database_url, max_size=4) for _ in range(3)]
    registries = [
        RequestRateLimitRegistry(PostgresRateLimitBucketAdapter(pool)) for pool in pools
    ]
    limit = [counter(VISITOR, 25), counter(PLATFORM, 1_000)]
    start = threading.Barrier(12)
    allowed: list[bool] = []
    guard = threading.Lock()

    def send(thread_index: int) -> None:
        registry = registries[thread_index % len(registries)]
        start.wait()
        for _ in range(5):
            is_allowed = registry.try_acquire_all(limit, MINUTE, at(5)) is None
            with guard:
                allowed.append(is_allowed)

    threads = [threading.Thread(target=send, args=(index,)) for index in range(12)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        counts = PostgresRateLimitBucketAdapter(pools[0]).read_counts(
            PLATFORM, locate_window(at(5), MINUTE)
        )
    finally:
        for pool in pools:
            pool.close()

    assert allowed.count(True) == 25
    assert len(allowed) == 60
    # Refused requests counted nowhere: the platform saw the 25.
    assert int(counts.current_count) == 25


def test_a_count_that_is_not_an_integer_is_a_storage_error() -> None:
    assert read_count(7) == 7
    with pytest.raises(ExternalServiceError):
        read_count("7")
