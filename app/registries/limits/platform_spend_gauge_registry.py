import threading

from typed_time_provider import Microseconds

from app.contracts.platform_safety import PlatformSpendGaugeContract
from app.contracts.repositories.spend_guard_repositories import (
    UsageSpendRepoContract,
)
from app.contracts.storage import StorageScopeContract
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.spend.constrained_strings import SpendDay
from app.utilities.spend.spend_days import utc_day
from app.utilities.spend.spend_pricing import price_usage, total_spend

MICROSECONDS_PER_SECOND: int = 1_000_000
# How long one reading of the platform's spend stands in one process.
READING_SECONDS: int = 60


class PlatformSpendGaugeRegistry(PlatformSpendGaugeContract):
    """
    The platform's provider spend of the current UTC day for the daily
    budget stop, which every model turn and call consults: one indexed sum
    of the day's usage events (`sum_platform`, priced like the admin's
    spend tile) stands for READING_SECONDS in this process, so the stop
    costs one query a minute however busy the platform is. It may hold the
    stop back by up to a minute of spend; a new UTC day reads at once.
    The sum runs platform-wide: a turn asks from inside its business's
    scope, which sees only that business's usage.
    """

    def __init__(
        self,
        usage_spend_repo: UsageSpendRepoContract,
        storage_scope: StorageScopeContract,
        reading_seconds: int = READING_SECONDS,
    ) -> None:
        self._usage: UsageSpendRepoContract = usage_spend_repo
        self._storage_scope: StorageScopeContract = storage_scope
        self._reading_microseconds: int = reading_seconds * MICROSECONDS_PER_SECOND
        self._lock: threading.Lock = threading.Lock()
        self._reading: tuple[SpendDay, int, CostMicroUsd] | None = None

    def spend_today(self, now: Microseconds) -> CostMicroUsd:
        day, started_at = utc_day(now)
        with self._lock:
            reading = self._reading
            if (
                reading is not None
                and reading[0] == day
                and 0 <= int(now) - reading[1] < self._reading_microseconds
            ):
                return reading[2]

        with self._storage_scope.platform_wide():
            spend: CostMicroUsd = total_spend(
                price_usage(
                    self._usage.sum_platform(started_at, Microseconds(int(now) + 1))
                )
            )
        with self._lock:
            self._reading = (day, int(now), spend)
        return spend
