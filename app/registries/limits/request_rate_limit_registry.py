from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.rate_limits import RateLimitBucketAdapterContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.typings.platform.constrained_integers import (
    RateLimitRequestCount,
    RateWindowSeconds,
    RetryAfterSeconds,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.utilities.limits.sliding_window_limits import (
    is_within_limit,
    locate_window,
    seconds_until_free,
)


class RequestRateLimitRegistry(RequestRateLimitRegistryContract):
    """
    Sliding-window request limits over shared counters.

    Guards public endpoints (the website widget's messages, polling and
    error reports, login code checks) against scripts that would make the
    API read a business's data or call the model over and over. The
    counters live in `rate_limit_buckets` (Postgres), so every API instance
    counts against the same limit: two instances do not double what a
    script may send. Each counter keeps the requests of a fixed window and
    the window before it, and a request is allowed while the sliding
    estimate stays within the limit (`sliding_window_limits`).
    """

    def __init__(self, buckets: RateLimitBucketAdapterContract) -> None:
        self._buckets: RateLimitBucketAdapterContract = buckets

    def try_acquire_all(
        self,
        counters: Sequence[RateLimitCounter],
        window: RateWindowSeconds,
        now: Microseconds,
    ) -> RateLimitKey | None:
        return self._buckets.count_if_within(counters, locate_window(now, window))

    def seconds_until_free(
        self,
        counter: RateLimitCounter,
        window: RateWindowSeconds,
        now: Microseconds,
    ) -> RetryAfterSeconds:
        position = locate_window(now, window)
        return seconds_until_free(
            self._buckets.read_counts(counter.key, position), counter, position
        )

    def has_room(
        self,
        counter: RateLimitCounter,
        window: RateWindowSeconds,
        now: Microseconds,
    ) -> bool:
        position = locate_window(now, window)
        counts = self._buckets.read_counts(counter.key, position)
        with_one_more = counts.model_copy(
            update={
                "current_count": RateLimitRequestCount(int(counts.current_count) + 1)
            }
        )
        return is_within_limit(with_one_more, counter, position)

    def forget_expired(self, now: Microseconds) -> DocumentCount:
        return self._buckets.delete_expired(now)
