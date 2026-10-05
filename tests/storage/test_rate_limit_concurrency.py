"""
Shared request counters on Postgres under many concurrent requests: no key
ever admits more than its limit, a refused request counts for no key and
leaves no bucket behind, and the counting statement gives the caller's
row-level security scope back.
"""

import threading
from collections import Counter

import psycopg
import pytest
from typed_time_provider import Microseconds

from app.adapters.rate_limits.postgres_rate_limit_bucket_adapter import (
    PostgresRateLimitBucketAdapter,
    find_refused_key,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
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
# Five seconds into a minute: no previous window weighs in.
NOW: Microseconds = Microseconds(1_789_999_980 * SECOND + 5 * SECOND)
THREADS: int = 32
REQUESTS_PER_THREAD: int = 10
PROCESSES: int = 4
VISITOR_LIMIT: int = 6
ADDRESS_LIMIT: int = 20
BUSINESS_LIMIT: int = 50
PLATFORM_LIMIT: int = 75
BUSINESS: RateLimitKey = RateLimitKey("widget-poll:business:biz_1")
PLATFORM: RateLimitKey = RateLimitKey("widget-poll:platform")


def counters_of(thread_index: int) -> list[RateLimitCounter]:
    """A visitor of its own, an address shared by four threads, one business."""

    return [
        RateLimitCounter(
            key=RateLimitKey(f"widget-poll:visitor:biz_1:v{thread_index:02d}"),
            limit=RequestsPerWindow(VISITOR_LIMIT),
        ),
        RateLimitCounter(
            key=RateLimitKey(f"widget-poll:address:10.0.0.{thread_index // 4}"),
            limit=RequestsPerWindow(ADDRESS_LIMIT),
        ),
        RateLimitCounter(key=BUSINESS, limit=RequestsPerWindow(BUSINESS_LIMIT)),
        RateLimitCounter(key=PLATFORM, limit=RequestsPerWindow(PLATFORM_LIMIT)),
    ]


def stored_counts(database_url: DatabaseUrl) -> dict[str, int]:
    with (
        psycopg.connect(str(database_url), autocommit=True) as connection,
        connection.transaction(),
    ):
        connection.execute("select set_config('app.bypass_rls', 'on', true)")
        rows = connection.execute(
            "select bucket_key, request_count from workshop.rate_limit_buckets"
        ).fetchall()
    return {str(key): int(count) for key, count in rows}


def test_concurrent_requests_never_pass_a_limit(database_url: DatabaseUrl) -> None:
    pools = [
        PostgresConnectionPoolClient(database_url, max_size=THREADS // PROCESSES)
        for _ in range(PROCESSES)
    ]
    adapters = [PostgresRateLimitBucketAdapter(pool) for pool in pools]
    window = locate_window(NOW, MINUTE)
    start = threading.Barrier(THREADS)
    admitted: Counter[str] = Counter()
    refusals: Counter[str] = Counter()
    guard = threading.Lock()

    def send(thread_index: int) -> None:
        adapter = adapters[thread_index % PROCESSES]
        counters = counters_of(thread_index)
        start.wait()
        for _ in range(REQUESTS_PER_THREAD):
            refused = adapter.count_if_within(counters, window)
            with guard:
                if refused is None:
                    admitted.update(str(counter.key) for counter in counters)
                else:
                    refusals[str(refused)] += 1

    threads = [threading.Thread(target=send, args=(index,)) for index in range(THREADS)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    finally:
        for pool in pools:
            pool.close()

    # The business limit binds: exactly its 50 got through, no more.
    assert admitted[str(BUSINESS)] == BUSINESS_LIMIT
    assert admitted[str(PLATFORM)] == BUSINESS_LIMIT
    assert sum(refusals.values()) == THREADS * REQUESTS_PER_THREAD - BUSINESS_LIMIT
    for thread_index in range(THREADS):
        visitor, address, _, _ = counters_of(thread_index)
        assert admitted[str(visitor.key)] <= VISITOR_LIMIT
        assert admitted[str(address.key)] <= ADDRESS_LIMIT
    # Every bucket holds exactly the admitted requests: refused ones counted
    # nowhere and left no empty bucket behind.
    assert stored_counts(database_url) == dict(admitted)


def test_counting_keeps_the_callers_scope_inside_a_transaction(
    database_url: DatabaseUrl,
) -> None:
    pool = PostgresConnectionPoolClient(database_url, max_size=1)
    adapter = PostgresRateLimitBucketAdapter(pool)
    window = locate_window(NOW, MINUTE)
    limit = [RateLimitCounter(key=BUSINESS, limit=RequestsPerWindow(1))]
    try:
        with pool.pinned_connection() as connection, pool.transaction():
            connection.execute(
                "select set_config('app.business_id', 'biz_1', true), "
                "set_config('app.bypass_rls', 'off', true)"
            )
            first = adapter.count_if_within(limit, window)
            second = adapter.count_if_within(limit, window)
            scope = connection.execute(
                "select current_setting('app.business_id', true), "
                "current_setting('app.bypass_rls', true)"
            ).fetchone()
    finally:
        pool.close()

    assert (first, second) == (None, BUSINESS)
    assert scope == ("biz_1", "off")
    assert stored_counts(database_url) == {str(BUSINESS): 1}


def test_a_refused_key_no_counter_names_is_a_storage_error() -> None:
    counters = counters_of(0)

    assert find_refused_key(counters, None) is None
    assert find_refused_key(counters, str(PLATFORM)) == PLATFORM
    with pytest.raises(ExternalServiceError):
        find_refused_key(counters, "widget-poll:someone-else")
