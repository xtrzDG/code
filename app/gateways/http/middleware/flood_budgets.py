"""
Flood budgets of one API process: requests per key (a provider and a
client network, a route and a client network) in a token bucket that
refills at the budget per minute. They cost no database round trip, so
they can refuse a flood before anything else runs; each process keeps its
own, and the shared limits (`RequestRateLimitRegistryContract`) stay what
bounds one caller across every process.

Memory is bounded: at most `max_keys` buckets, the least recently used
forgotten first (a forgotten key starts full again).
"""

import math
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

from app.schemas.typings.compliance.strings import ClientIpAddress
from app.utilities.channels.widget_rate_limits import describe_client_network

type MonotonicClock = Callable[[], float]

SECONDS_PER_MINUTE: float = 60.0
DEFAULT_MAX_KEYS: int = 10_000


@dataclass
class TokenBucket:
    tokens: float
    updated_at: float
    # Whether the last request of the key was refused: a refusal is
    # reported when it starts, not for every refused request after it.
    is_refusing: bool = False


@dataclass(frozen=True)
class BudgetDecision:
    """Admitted, or refused with the whole seconds until one more fits."""

    is_admitted: bool
    retry_after_seconds: int = 0
    # The first refusal after an admitted request (worth one log line).
    is_new_refusal: bool = False


class FloodBudget:
    """`per_minute` requests of one key, refilled evenly (thread-safe)."""

    def __init__(
        self,
        per_minute: int,
        clock: MonotonicClock = time.monotonic,
        max_keys: int = DEFAULT_MAX_KEYS,
    ) -> None:
        if per_minute < 1 or max_keys < 1:
            raise ValueError("A flood budget needs at least one request and key.")

        self.per_minute: int = per_minute
        self._refill_per_second: float = per_minute / SECONDS_PER_MINUTE
        self._clock: MonotonicClock = clock
        self._max_keys: int = max_keys
        self._buckets: OrderedDict[str, TokenBucket] = OrderedDict()
        self._lock: threading.Lock = threading.Lock()

    def spend(self, key: str) -> BudgetDecision:
        """Take one request of `key`'s budget, or say how long to wait."""

        now: float = self._clock()
        with self._lock:
            bucket: TokenBucket = self._bucket_of(key, now)
            elapsed: float = max(0.0, now - bucket.updated_at)
            bucket.tokens = min(
                float(self.per_minute),
                bucket.tokens + elapsed * self._refill_per_second,
            )
            bucket.updated_at = now
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                bucket.is_refusing = False
                return BudgetDecision(is_admitted=True)

            is_new_refusal: bool = not bucket.is_refusing
            bucket.is_refusing = True
            wait: float = (1.0 - bucket.tokens) / self._refill_per_second
            return BudgetDecision(
                is_admitted=False,
                retry_after_seconds=max(1, math.ceil(wait)),
                is_new_refusal=is_new_refusal,
            )

    def _bucket_of(self, key: str, now: float) -> TokenBucket:
        bucket: TokenBucket | None = self._buckets.get(key)
        if bucket is None:
            bucket = TokenBucket(tokens=float(self.per_minute), updated_at=now)
            self._buckets[key] = bucket
            if len(self._buckets) > self._max_keys:
                self._buckets.popitem(last=False)
        else:
            self._buckets.move_to_end(key)

        return bucket


def network_key(scope_label: str, client_address: str | None) -> str:
    """
    The budget key of a caller: the label (a provider, a route) and its
    client network (an IPv4 address, the /64 of an IPv6 address).
    """

    if client_address is None:
        return f"{scope_label}:unknown"

    return f"{scope_label}:{describe_client_network(ClientIpAddress(client_address))}"
