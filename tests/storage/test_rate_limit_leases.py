"""
Leased rate-limit counters (migration 1215, `RateLimitLeases`): a lease
counts as many requests as the limit still holds and never more, in memory
and on Postgres alike (request by request the same grants), a refused
lease leaves nothing behind and keeps the caller's scope, and processes
leasing one counter together with per-request counters never admit more
than any limit. The Postgres counters run on the platform role, as the
platform pool does (only workshop_platform may call the functions).
"""

import random
import threading
from collections import Counter
from collections.abc import Generator

import psycopg
import pytest
from typed_time_provider import Microseconds

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.adapters.rate_limits.postgres_rate_limit_bucket_adapter import (
    PostgresRateLimitBucketAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.rate_limits import RateLimitBucketAdapterContract
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.typings.platform.constrained_integers import (
    RateLimitLeaseSize,
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.limits.sliding_window_limits import locate_window
from tests.storage.postgres_roles import RoleDatabase

SECOND: int = 1_000_000
MINUTE: RateWindowSeconds = RateWindowSeconds(60)
WINDOW_START: int = 1_789_999_980 * SECOND
BUSINESS: RateLimitKey = RateLimitKey("widget-poll:business:biz_1")
PLATFORM: RateLimitKey = RateLimitKey("widget-poll:platform")
PROCESSES: int = 4
THREADS: int = 32
REQUESTS_PER_THREAD: int = 10
BUSINESS_LIMIT: int = 50
BUSINESS_LEASE: int = 5
# High enough never to bind here: the business limit does.
PLATFORM_LIMIT: int = 200
PLATFORM_LEASE: int = 8


def leased(key: RateLimitKey, limit: int, lease: int) -> RateLimitCounter:
    return RateLimitCounter(
        key=key, limit=RequestsPerWindow(limit), lease_size=RateLimitLeaseSize(lease)
    )


def at(seconds: int) -> Microseconds:
    return Microseconds(WINDOW_START + seconds * SECOND)


@pytest.fixture(params=["in_memory", "postgres"])
def buckets(
    request: pytest.FixtureRequest,
) -> Generator[RateLimitBucketAdapterContract]:
    if request.param == "in_memory":
        yield InMemoryRateLimitBucketAdapter()
        return

    role_urls: RoleDatabase = request.getfixturevalue("role_urls")
    pool = PostgresConnectionPoolClient(role_urls.platform_url, max_size=2)
    try:
        yield PostgresRateLimitBucketAdapter(pool)
    finally:
        pool.close()


def test_a_lease_counts_what_the_limit_still_holds(
    buckets: RateLimitBucketAdapterContract,
) -> None:
    business = leased(BUSINESS, 10, 4)
    window = locate_window(at(5), MINUTE)
    units = RateLimitLeaseSize(4)

    grants = [int(buckets.lease_within(business, units, window)) for _ in range(4)]

    assert grants == [4, 4, 2, 0]
    assert int(buckets.read_counts(BUSINESS, window).current_count) == 10
    # A request counted per request finds the limit used up by the leases.
    assert buckets.count_if_within([business], window) == BUSINESS


def test_a_refused_lease_leaves_no_bucket(
    buckets: RateLimitBucketAdapterContract,
) -> None:
    business = leased(BUSINESS, 3, 2)
    full = locate_window(at(5), MINUTE)
    for _ in range(3):
        assert buckets.count_if_within([business], full) is None
    # At the start of the next minute the previous one still weighs fully.
    next_minute = locate_window(at(60), MINUTE)

    granted = buckets.lease_within(business, RateLimitLeaseSize(2), next_minute)

    assert int(granted) == 0
    assert int(buckets.read_counts(BUSINESS, next_minute).current_count) == 0
    # Half a minute later half the previous minute's weight is gone.
    later = locate_window(at(90), MINUTE)
    assert int(buckets.lease_within(business, RateLimitLeaseSize(2), later)) == 1


def test_postgres_grants_every_lease_like_memory(role_urls: RoleDatabase) -> None:
    chance = random.Random(1194)
    memory = InMemoryRateLimitBucketAdapter()
    pool = PostgresConnectionPoolClient(role_urls.platform_url, max_size=1)
    postgres = PostgresRateLimitBucketAdapter(pool)
    moment: int = WINDOW_START
    grants: list[tuple[int, int]] = []
    try:
        for _ in range(300):
            moment += chance.choice([0, 1, 2, 5, 30, 60]) * SECOND
            moment += chance.randint(0, SECOND - 1)
            window = locate_window(Microseconds(moment), MINUTE)
            counter = leased(BUSINESS, chance.randint(1, 12), chance.randint(1, 5))
            if chance.random() < 0.3:
                assert memory.count_if_within(
                    [counter], window
                ) == postgres.count_if_within([counter], window)
                continue

            units = RateLimitLeaseSize(chance.randint(1, 6))
            grants.append(
                (
                    int(memory.lease_within(counter, units, window)),
                    int(postgres.lease_within(counter, units, window)),
                )
            )
            assert postgres.read_counts(BUSINESS, window) == memory.read_counts(
                BUSINESS, window
            )
    finally:
        pool.close()

    assert all(in_memory == on_postgres for in_memory, on_postgres in grants)
    # Full, partial and refused grants all happened.
    assert {0, 1} <= {in_memory for in_memory, _ in grants}
    assert any(in_memory > 1 for in_memory, _ in grants)


def test_a_lease_keeps_the_callers_scope(role_urls: RoleDatabase) -> None:
    pool = PostgresConnectionPoolClient(role_urls.platform_url, max_size=1)
    postgres = PostgresRateLimitBucketAdapter(pool)
    window = locate_window(at(5), MINUTE)
    try:
        with pool.pinned_connection() as connection, pool.transaction():
            connection.execute(
                "select set_config('app.business_id', 'biz_1', true), "
                "set_config('app.bypass_rls', 'off', true)"
            )
            granted = postgres.lease_within(
                leased(BUSINESS, 5, 3), RateLimitLeaseSize(3), window
            )
            scope = connection.execute(
                "select current_setting('app.business_id', true), "
                "current_setting('app.bypass_rls', true)"
            ).fetchone()
    finally:
        pool.close()

    assert int(granted) == 3
    assert scope == ("biz_1", "off")


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


def poll_counters(thread_index: int) -> list[RateLimitCounter]:
    """A visitor of its own, an address of four threads, leased shared rows."""

    return [
        RateLimitCounter(
            key=RateLimitKey(f"widget-poll:visitor:biz_1:v{thread_index:02d}"),
            limit=RequestsPerWindow(6),
        ),
        RateLimitCounter(
            key=RateLimitKey(f"widget-poll:address:10.0.0.{thread_index // 4}"),
            limit=RequestsPerWindow(20),
        ),
        leased(BUSINESS, BUSINESS_LIMIT, BUSINESS_LEASE),
        leased(PLATFORM, PLATFORM_LIMIT, PLATFORM_LEASE),
    ]


def test_processes_leasing_together_never_pass_a_limit(
    database_url: DatabaseUrl, role_urls: RoleDatabase
) -> None:
    pools = [
        PostgresConnectionPoolClient(
            role_urls.platform_url, max_size=THREADS // PROCESSES
        )
        for _ in range(PROCESSES)
    ]
    # One registry per process: each holds its own leases.
    registries = [
        RequestRateLimitRegistry(PostgresRateLimitBucketAdapter(pool)) for pool in pools
    ]
    start = threading.Barrier(THREADS)
    admitted: Counter[str] = Counter()
    guard = threading.Lock()

    def send(thread_index: int) -> None:
        registry = registries[thread_index % PROCESSES]
        counters = poll_counters(thread_index)
        start.wait()
        for _ in range(REQUESTS_PER_THREAD):
            if registry.try_acquire_all(counters, MINUTE, at(5)) is None:
                with guard:
                    admitted.update(str(counter.key) for counter in counters)

    threads = [threading.Thread(target=send, args=(index,)) for index in range(THREADS)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        stored = stored_counts(database_url)
        drained: int = sum(drain(registry) for registry in registries)
    finally:
        for pool in pools:
            pool.close()

    # The business limit binds and is never passed; what the processes
    # still hold stays counted.
    assert admitted[str(BUSINESS)] <= stored[str(BUSINESS)] <= BUSINESS_LIMIT
    assert admitted[str(PLATFORM)] == admitted[str(BUSINESS)]
    assert admitted[str(PLATFORM)] <= stored[str(PLATFORM)] <= PLATFORM_LIMIT
    for thread_index in range(THREADS):
        visitor, address, _, _ = poll_counters(thread_index)
        assert admitted[str(visitor.key)] <= 6
        assert admitted[str(address.key)] <= 20
        # Counted per request: exactly the admitted ones, none refused.
        assert stored.get(str(visitor.key), 0) == admitted[str(visitor.key)]
        assert stored.get(str(address.key), 0) == admitted[str(address.key)]
    # Drained by requests no per-request limit stops, every unit counted is
    # admitted once: exactly the limit in all.
    assert admitted[str(BUSINESS)] + drained == BUSINESS_LIMIT
    assert stored_counts(database_url)[str(BUSINESS)] == BUSINESS_LIMIT


def drain(registry: RequestRateLimitRegistry) -> int:
    """How many more requests of the shared rows the registry admits."""

    counters = [
        leased(BUSINESS, BUSINESS_LIMIT, BUSINESS_LEASE),
        leased(PLATFORM, PLATFORM_LIMIT, PLATFORM_LEASE),
    ]
    admitted: int = 0
    while registry.try_acquire_all(counters, MINUTE, at(5)) is None:
        admitted += 1
    return admitted
