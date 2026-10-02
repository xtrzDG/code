import threading
from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.rate_limits import RateLimitBucketAdapterContract
from app.schemas.dto.rate_limits import (
    RateLimitBucketCounts,
    RateLimitCounter,
    RateLimitWindow,
)
from app.schemas.typings.platform.constrained_integers import RateLimitRequestCount
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.utilities.limits.sliding_window_limits import (
    bucket_expiry,
    is_within_limit,
    previous_window_start,
)

# Expired buckets are dropped every this many counted requests, so a
# development process stays small without the sweep job.
SWEEP_EVERY_CALLS: int = 1_000

type BucketId = tuple[RateLimitKey, int, int]


class InMemoryRateLimitBucketAdapter(RateLimitBucketAdapterContract):
    """
    Request buckets of this process (tests, development without a
    database): `(key, window length, window start) -> (count, expiry)`
    under one lock.
    """

    def __init__(self) -> None:
        self._buckets: dict[BucketId, tuple[int, int]] = {}
        self._lock: threading.Lock = threading.Lock()
        self._calls: int = 0

    def count_if_within(
        self,
        counters: Sequence[RateLimitCounter],
        window: RateLimitWindow,
    ) -> RateLimitKey | None:
        with self._lock:
            self._calls += 1
            if self._calls % SWEEP_EVERY_CALLS == 0:
                self._drop_expired(int(window.now))

            for counter in counters:
                counts = self._counts(counter.key, window)
                with_this_request = counts.model_copy(
                    update={
                        "current_count": RateLimitRequestCount(
                            int(counts.current_count) + 1
                        )
                    }
                )
                if not is_within_limit(with_this_request, counter, window):
                    return counter.key

            for key in {counter.key for counter in counters}:
                bucket_id = _current_bucket(key, window)
                count, _ = self._buckets.get(bucket_id, (0, 0))
                self._buckets[bucket_id] = (count + 1, bucket_expiry(window))

            return None

    def read_counts(
        self,
        key: RateLimitKey,
        window: RateLimitWindow,
    ) -> RateLimitBucketCounts:
        with self._lock:
            return self._counts(key, window)

    def delete_expired(self, now: Microseconds) -> DocumentCount:
        with self._lock:
            return DocumentCount(self._drop_expired(int(now)))

    def _counts(
        self,
        key: RateLimitKey,
        window: RateLimitWindow,
    ) -> RateLimitBucketCounts:
        length: int = int(window.length_seconds)
        current, _ = self._buckets.get(_current_bucket(key, window), (0, 0))
        previous, _ = self._buckets.get(
            (key, length, previous_window_start(window)), (0, 0)
        )
        return RateLimitBucketCounts(
            key=key,
            current_count=RateLimitRequestCount(current),
            previous_count=RateLimitRequestCount(previous),
        )

    def _drop_expired(self, now: int) -> int:
        expired: list[BucketId] = [
            bucket_id
            for bucket_id, (_, expires_at) in self._buckets.items()
            if expires_at <= now
        ]
        for bucket_id in expired:
            del self._buckets[bucket_id]

        return len(expired)


def _current_bucket(key: RateLimitKey, window: RateLimitWindow) -> BucketId:
    return (key, int(window.length_seconds), int(window.started_at))
