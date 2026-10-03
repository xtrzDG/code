from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.adapters.rate_limits.rate_limit_bucket_queries import (
    COUNT_REQUESTS,
    DELETE_EXPIRED_BATCH,
    RATE_LIMIT_BUCKETS_TABLE,
    READ_COUNTS,
)
from app.adapters.storage.postgres.platform_transaction import platform_transaction
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.rate_limits import RateLimitBucketAdapterContract
from app.schemas.dto.rate_limits import (
    RateLimitBucketCounts,
    RateLimitCounter,
    RateLimitWindow,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.constrained_integers import RateLimitRequestCount
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.utilities.limits.sliding_window_limits import (
    bucket_expiry,
    is_within_limit,
    previous_window_start,
)

DELETE_BATCH_SIZE: int = 5_000


class _OverLimit(Exception):
    """Rolls the counting transaction back: one of its limits is used up."""

    def __init__(self, key: RateLimitKey) -> None:
        super().__init__(str(key))
        self.key: RateLimitKey = key


class PostgresRateLimitBucketAdapter(RateLimitBucketAdapterContract):
    """
    Request buckets in `workshop.rate_limit_buckets`, shared by every API
    instance and worker.

    A request is one transaction with one statement: `insert ... on
    conflict do update set request_count = request_count + 1 returning`
    for every key (in key order), joined with the previous window's
    counts. When a limit is over, the transaction is rolled back, so the
    refused request counted nowhere; the upserted rows stay locked until
    then, so concurrent requests of any process see each other's counts
    and never both take the last place. The table is UNLOGGED: counters
    are short-lived and not worth the write-ahead log (a crash empties
    them, which only resets the limits).
    """

    def __init__(self, connection_pool: PostgresConnectionPoolClient) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool

    def count_if_within(
        self,
        counters: Sequence[RateLimitCounter],
        window: RateLimitWindow,
    ) -> RateLimitKey | None:
        keys: list[str] = sorted({str(counter.key) for counter in counters})
        try:
            with platform_transaction(
                self._connection_pool, RATE_LIMIT_BUCKETS_TABLE
            ) as connection:
                rows = connection.execute(
                    COUNT_REQUESTS,
                    {
                        "keys": keys,
                        "window_seconds": int(window.length_seconds),
                        "window_start": int(window.started_at),
                        "previous_start": previous_window_start(window),
                        "expires_at": bucket_expiry(window),
                    },
                ).fetchall()
                counts: dict[str, RateLimitBucketCounts] = {
                    str(row[0]): RateLimitBucketCounts(
                        key=RateLimitKey(str(row[0])),
                        current_count=RateLimitRequestCount(read_count(row[1])),
                        previous_count=RateLimitRequestCount(read_count(row[2])),
                    )
                    for row in rows
                }
                for counter in counters:
                    if not is_within_limit(counts[str(counter.key)], counter, window):
                        raise _OverLimit(counter.key)
        except _OverLimit as over_limit:
            return over_limit.key

        return None

    def read_counts(
        self,
        key: RateLimitKey,
        window: RateLimitWindow,
    ) -> RateLimitBucketCounts:
        with platform_transaction(
            self._connection_pool, RATE_LIMIT_BUCKETS_TABLE
        ) as connection:
            row = connection.execute(
                READ_COUNTS,
                {
                    "key": str(key),
                    "window_seconds": int(window.length_seconds),
                    "window_start": int(window.started_at),
                    "previous_start": previous_window_start(window),
                },
            ).fetchone()

        return RateLimitBucketCounts(
            key=key,
            current_count=RateLimitRequestCount(
                0 if row is None else read_count(row[0])
            ),
            previous_count=RateLimitRequestCount(
                0 if row is None else read_count(row[1])
            ),
        )

    def delete_expired(self, now: Microseconds) -> DocumentCount:
        deleted_total: int = 0
        while True:
            with platform_transaction(
                self._connection_pool, RATE_LIMIT_BUCKETS_TABLE
            ) as connection:
                deleted: int = connection.execute(
                    DELETE_EXPIRED_BATCH,
                    {"now": int(now), "batch_size": DELETE_BATCH_SIZE},
                ).rowcount

            deleted_total += max(deleted, 0)
            if deleted < DELETE_BATCH_SIZE:
                return DocumentCount(deleted_total)


def read_count(value: object) -> int:
    """A count column (`integer`, or `bigint` from `sum`) as an int."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise ExternalServiceError(
            f"{RATE_LIMIT_BUCKETS_TABLE} returned a count that is not an "
            f"integer ({type(value).__name__})."
        )

    return value
