from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.adapters.rate_limits.rate_limit_bucket_queries import (
    COUNT_REQUEST_WITHIN_LIMITS,
    DELETE_EXPIRED_BATCH,
    RATE_LIMIT_BUCKETS_TABLE,
    READ_COUNTS,
)
from app.adapters.storage.postgres.platform_transaction import (
    platform_statement,
    platform_transaction,
)
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
    previous_window_start,
    window_microseconds,
)

DELETE_BATCH_SIZE: int = 5_000


class PostgresRateLimitBucketAdapter(RateLimitBucketAdapterContract):
    """
    Request buckets in `workshop.rate_limit_buckets`, shared by every API
    instance and worker.

    A request is one statement: `workshop.count_request_within_limits`
    (migration 1135) upserts one request more for every key (in key
    order), weighs each counter against its limit as `is_within_limit`
    does, and takes the request back out of every key when one is over,
    all inside the database. The rows are locked only while that statement
    runs: concurrent requests of any process wait for the final counts and
    never both take the last place, and a refused request counts nowhere,
    yet no request waits for another one's round trip to the application
    (every widget poll counts the same platform row). Inside a unit of
    work the statement is a savepoint of its transaction
    (`platform_statement`), so its error rolls back only itself. The table is
    UNLOGGED: counters are short-lived and not worth the write-ahead log (a
    crash empties them, which only resets the limits).
    """

    def __init__(self, connection_pool: PostgresConnectionPoolClient) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool

    def count_if_within(
        self,
        counters: Sequence[RateLimitCounter],
        window: RateLimitWindow,
    ) -> RateLimitKey | None:
        with platform_statement(
            self._connection_pool, RATE_LIMIT_BUCKETS_TABLE
        ) as connection:
            row = connection.execute(
                COUNT_REQUEST_WITHIN_LIMITS,
                {
                    "bucket_keys": sorted({str(counter.key) for counter in counters}),
                    "counter_keys": [str(counter.key) for counter in counters],
                    "counter_limits": [int(counter.limit) for counter in counters],
                    "window_seconds": int(window.length_seconds),
                    "window_start": int(window.started_at),
                    "previous_start": previous_window_start(window),
                    "expires_at": bucket_expiry(window),
                    "window_microseconds": window_microseconds(window.length_seconds),
                    "elapsed_microseconds": int(window.now) - int(window.started_at),
                },
            ).fetchone()

        return find_refused_key(counters, None if row is None else row[0])

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


def find_refused_key(
    counters: Sequence[RateLimitCounter],
    refused_key: object,
) -> RateLimitKey | None:
    """The counter key the counting statement refused (None: it counted)."""

    if refused_key is None:
        return None

    for counter in counters:
        if str(counter.key) == refused_key:
            return counter.key

    raise ExternalServiceError(
        f"{RATE_LIMIT_BUCKETS_TABLE} refused a key that no counter of the "
        f"request names ({type(refused_key).__name__})."
    )


def read_count(value: object) -> int:
    """A count column (`integer`, or `bigint` from `sum`) as an int."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise ExternalServiceError(
            f"{RATE_LIMIT_BUCKETS_TABLE} returned a count that is not an "
            f"integer ({type(value).__name__})."
        )

    return value
