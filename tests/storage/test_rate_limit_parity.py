"""
The Postgres counters decide like the in-memory ones: the database function
(`workshop.count_request_within_limits`, migration 1135) and
`is_within_limit` admit and refuse the same requests, request by request,
across windows whose previous window weighs in at every moment.
"""

import random
from collections.abc import Generator

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
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.limits.sliding_window_limits import locate_window

SECOND: int = 1_000_000
START: int = 1_789_999_980 * SECOND
KEYS: tuple[RateLimitKey, ...] = tuple(
    RateLimitKey(f"parity:{name}") for name in ("a", "b", "c", "d")
)


@pytest.fixture
def postgres_buckets(
    database_url: DatabaseUrl,
) -> Generator[PostgresRateLimitBucketAdapter]:
    pool = PostgresConnectionPoolClient(database_url, max_size=1)
    try:
        yield PostgresRateLimitBucketAdapter(pool)
    finally:
        pool.close()


def random_request(chance: random.Random) -> list[RateLimitCounter]:
    """One to three counters (a key may repeat), limits small enough to bite."""

    return [
        RateLimitCounter(
            key=chance.choice(KEYS), limit=RequestsPerWindow(chance.randint(1, 6))
        )
        for _ in range(chance.randint(1, 3))
    ]


@pytest.mark.parametrize("length", [10, 60])
def test_postgres_decides_every_request_like_memory(
    postgres_buckets: PostgresRateLimitBucketAdapter, length: int
) -> None:
    chance = random.Random(length)
    memory = InMemoryRateLimitBucketAdapter()
    window_length = RateWindowSeconds(length)
    moment: int = START
    decisions: list[tuple[str | None, str | None]] = []
    for _ in range(400):
        # Mostly inside a window, now and then into the next one or two.
        moment += chance.choice([0, 1, 1, 2, 3, length // 2, length]) * SECOND
        moment += chance.randint(0, SECOND - 1)
        window = locate_window(Microseconds(moment), window_length)
        counters = random_request(chance)
        in_memory = memory.count_if_within(counters, window)
        on_postgres = postgres_buckets.count_if_within(counters, window)
        decisions.append(
            (
                None if in_memory is None else str(in_memory),
                None if on_postgres is None else str(on_postgres),
            )
        )
        for key in KEYS:
            assert postgres_buckets.read_counts(key, window) == memory.read_counts(
                key, window
            )

    assert all(memory_side == postgres_side for memory_side, postgres_side in decisions)
    # Both kinds of answer happened, so the comparison means something.
    assert any(memory_side is None for memory_side, _ in decisions)
    assert any(memory_side is not None for memory_side, _ in decisions)
