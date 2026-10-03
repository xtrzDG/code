"""Request counters shared by every API instance (rate limits)."""

from collections.abc import Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.rate_limits import (
    RateLimitBucketCounts,
    RateLimitCounter,
    RateLimitWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.schemas.typings.storage.constrained_integers import DocumentCount


class RateLimitBucketAdapterContract(AdapterContract, Protocol):
    """
    Request counts per key in fixed windows (buckets): in Postgres for every
    process at once, in memory for tests and development.
    """

    def count_if_within(
        self,
        counters: Sequence[RateLimitCounter],
        window: RateLimitWindow,
    ) -> RateLimitKey | None:
        """
        In one atomic step, count one request in the window's bucket of
        every counter when every counter stays within its limit
        (`is_within_limit` of the sliding-window approximation); otherwise
        count none, create no bucket and return the first counter's key
        (in the given order) whose limit is used up. Concurrent calls of
        any process never both pass the last free place.
        """
        raise NotImplementedError

    def read_counts(
        self,
        key: RateLimitKey,
        window: RateLimitWindow,
    ) -> RateLimitBucketCounts:
        """The key's requests in the window and in the one before it."""
        raise NotImplementedError

    def delete_expired(self, now: Microseconds) -> DocumentCount:
        """Drop the buckets no estimate needs any more; how many went."""
        raise NotImplementedError
