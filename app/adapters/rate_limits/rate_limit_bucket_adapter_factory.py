"""Choose the request counters for the container wiring."""

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


def build_rate_limit_bucket_adapter(
    connection_pool: PostgresConnectionPoolClient | None,
) -> RateLimitBucketAdapterContract:
    """
    Counters in Postgres, shared by every API instance, when there is a
    database; counters of this process otherwise (tests, development).
    """

    if connection_pool is None:
        return InMemoryRateLimitBucketAdapter()

    return PostgresRateLimitBucketAdapter(connection_pool)
