"""The requests this process took ahead from shared rate-limit counters."""

import threading
from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.rate_limits import RateLimitBucketAdapterContract
from app.schemas.dto.rate_limits import RateLimitCounter, RateLimitWindow
from app.schemas.typings.platform.constrained_integers import (
    RateLimitLeaseGrant,
    RateLimitLeaseSize,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey

# A lease is topped up ahead once less than a fifth of it is left.
TOP_UP_AHEAD_SHARE: int = 5


@dataclass
class HeldLease:
    """
    Units of one key this process may still admit, and their window;
    whether the shared counter granted none to a top-up ahead in it.
    """

    window_start: Microseconds
    remaining: int
    is_used_up: bool = False


@dataclass(frozen=True)
class TakenUnit:
    """One unit a request took: of which key, from which window's lease."""

    key: RateLimitKey
    window_start: Microseconds


class RateLimitLeases:
    """
    Leased counters of one process (thread-safe).

    A leased counter (`RateLimitCounter.lease_size`) admits a request from
    the units this process holds for the current window, and takes
    `lease_size` more from the shared counter
    (`RateLimitBucketAdapterContract.lease_within`, one statement) only
    when they are used up: as many as the limit still holds, none once it
    is used up. Every unit is counted in the shared counter before it
    admits a request, so all processes together never admit more than the
    limit. Units a window leaves unused stay counted there (the limit may
    bind up to a lease and a fifth per process early, never late); a
    request refused by another of its counters gives its unit back to the
    lease it came from while that lease is held. The request that finds
    less than a fifth of a lease left tops it up ahead, while the others
    go on with what is left, so requests seldom wait for the shared row;
    one thread at a time tops a key's lease up, and a request that finds
    none left waits for it and uses what it took.
    """

    def __init__(self, buckets: RateLimitBucketAdapterContract) -> None:
        self._buckets: RateLimitBucketAdapterContract = buckets
        self._lock: threading.Lock = threading.Lock()
        self._held: dict[RateLimitKey, HeldLease] = {}
        self._top_up_locks: dict[RateLimitKey, threading.Lock] = {}

    def take(
        self,
        counter: RateLimitCounter,
        units: RateLimitLeaseSize,
        window: RateLimitWindow,
    ) -> TakenUnit | None:
        """
        One unit for a request of the counter: from the lease, or after
        topping it up. None when the shared counter grants nothing (the
        limit is used up); nothing is taken then.
        """

        held: tuple[TakenUnit, int] | None = self._take_held(counter.key, window)
        if held is not None:
            unit, remaining = held
            if (
                remaining * TOP_UP_AHEAD_SHARE < int(units)
                and unit.window_start == window.started_at
            ):
                self._top_up_ahead(counter, units, window)
            return unit

        with self._top_up_lock(counter.key):
            held = self._take_held(counter.key, window)
            if held is not None:
                return held[0]

            granted: RateLimitLeaseGrant = self._buckets.lease_within(
                counter, units, window
            )
            if int(granted) == 0:
                return None

            self._hold(counter.key, window.started_at, int(granted) - 1)
            return TakenUnit(key=counter.key, window_start=window.started_at)

    def give_back(self, taken: list[TakenUnit]) -> None:
        """
        Return the units of a refused request to the leases they came from
        (a unit whose lease a newer window's replaced stays counted unused).
        """

        with self._lock:
            for unit in taken:
                held: HeldLease | None = self._held.get(unit.key)
                if held is not None and held.window_start == unit.window_start:
                    held.remaining += 1

    def _take_held(
        self, key: RateLimitKey, window: RateLimitWindow
    ) -> tuple[TakenUnit, int] | None:
        """
        One unit of the key's lease and how many are left after it, when
        this process holds one for the request's window or a later one (a
        request that read the clock just before a window ended may use the
        next window's units: they are counted there, which only weighs on
        the limit sooner).
        """

        with self._lock:
            held: HeldLease | None = self._held.get(key)
            if (
                held is None
                or held.window_start < window.started_at
                or held.remaining <= 0
            ):
                return None

            held.remaining -= 1
            return (
                TakenUnit(key=key, window_start=held.window_start),
                held.remaining,
            )

    def _top_up_ahead(
        self,
        counter: RateLimitCounter,
        units: RateLimitLeaseSize,
        window: RateLimitWindow,
    ) -> None:
        """
        Top a low lease up without making anyone wait: skipped while
        another request tops it up, once it is no longer low, and for the
        rest of a window in which the shared counter had none left.
        """

        top_up_lock: threading.Lock = self._top_up_lock(counter.key)
        if not top_up_lock.acquire(blocking=False):
            return

        try:
            with self._lock:
                held: HeldLease | None = self._held.get(counter.key)
                is_low: bool = (
                    held is not None
                    and held.window_start == window.started_at
                    and not held.is_used_up
                    and held.remaining * TOP_UP_AHEAD_SHARE < int(units)
                )
            if not is_low:
                return

            granted: RateLimitLeaseGrant = self._buckets.lease_within(
                counter, units, window
            )
            if int(granted) == 0:
                self._mark_used_up(counter.key, window.started_at)
                return

            self._hold(counter.key, window.started_at, int(granted))
        finally:
            top_up_lock.release()

    def _mark_used_up(self, key: RateLimitKey, window_start: Microseconds) -> None:
        with self._lock:
            held: HeldLease | None = self._held.get(key)
            if held is not None and held.window_start == window_start:
                held.is_used_up = True

    def _hold(self, key: RateLimitKey, window_start: Microseconds, units: int) -> None:
        """
        Keep a granted lease's units: added to a lease of the same window
        (what was left of it, or a unit given back meanwhile), replacing an
        older window's (its unused units stay counted in the shared
        counter), dropped when this process already holds a newer window's.
        """

        with self._lock:
            held: HeldLease | None = self._held.get(key)
            if held is not None and held.window_start == window_start:
                held.remaining += units
                held.is_used_up = False
            elif held is None or held.window_start < window_start:
                self._held[key] = HeldLease(window_start=window_start, remaining=units)

    def _top_up_lock(self, key: RateLimitKey) -> threading.Lock:
        with self._lock:
            return self._top_up_locks.setdefault(key, threading.Lock())
