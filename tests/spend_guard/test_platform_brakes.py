"""
The platform's brakes in the spend guard: while a platform admin paused
every assistant, or the platform's spend of the UTC day reached its daily
budget stop, every business is at HARD_LIMIT, whatever it spent itself,
and nothing is marked, audited or told per business. The budget stop
reads the platform's spend once a minute per process.
"""

from datetime import timedelta

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.registries.limits.platform_spend_gauge_registry import (
    PlatformSpendGaugeRegistry,
)
from app.repositories.spend_guard_repositories import UsageSpendRepository
from app.schemas.constants.spend import SpendLevel
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.dto.spend_guard import (
    SpendCheckRequest,
    SpendVerdict,
    UsageKindTotal,
)
from app.schemas.dto.storage import StorageScope
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.spend_guard.platform_brake_helpers import (
    budget_settings,
    pause,
    spend_elsewhere,
)
from tests.spend_guard.spend_world import (
    DOLLAR,
    NOON,
    CountingUsageSpend,
    SpendWorld,
    build_spend_world,
    micros,
)


def check(world: SpendWorld, minutes_later: int = 0) -> SpendVerdict:
    return world.check.run(
        SpendCheckRequest(
            business=world.business,
            now=micros(NOON + timedelta(minutes=minutes_later)),
        )
    )


def test_a_paused_platform_holds_every_business_back_until_it_resumes() -> None:
    world = build_spend_world()
    pause(world)

    paused = check(world)

    assert paused.level is SpendLevel.HARD_LIMIT
    assert int(paused.spend_micro_usd) == 0
    # Not the business's own limit: no mark, no audit entry, no notice.
    assert world.usage_spend.business_sums == 0
    assert world.marks.list_by_day(paused.day) == []
    assert world.audit_entries() == []
    assert world.notifier.notifications == []

    pause(world, is_paused=False)
    assert check(world).level is SpendLevel.NORMAL


def test_the_budget_stop_holds_every_business_from_the_stop_share_on() -> None:
    world = build_spend_world(settings=budget_settings(10))
    spend_elsewhere(world, 10 * DOLLAR - 1)
    assert check(world).level is SpendLevel.NORMAL

    stopped = build_spend_world(settings=budget_settings(10))
    spend_elsewhere(stopped, 10 * DOLLAR)
    verdict = check(stopped)

    assert verdict.level is SpendLevel.HARD_LIMIT
    assert stopped.audit_entries() == []
    assert stopped.notifier.notifications == []


def test_the_stop_share_is_configurable() -> None:
    world = build_spend_world(settings=budget_settings(10, stop_percent=150))
    spend_elsewhere(world, 14 * DOLLAR)
    assert check(world).level is SpendLevel.NORMAL

    later = build_spend_world(settings=budget_settings(10, stop_percent=150))
    spend_elsewhere(later, 15 * DOLLAR)
    assert check(later).level is SpendLevel.HARD_LIMIT


def test_without_a_budget_nothing_stops_the_platform() -> None:
    world = build_spend_world()
    spend_elsewhere(world, 1_000 * DOLLAR)

    assert check(world).level is SpendLevel.NORMAL


class ScopeRecordingUsageSpend(CountingUsageSpend):
    """Counts the platform sums and remembers the scope they ran in."""

    def __init__(self, inner: UsageSpendRepository, scope: StorageScopeContext) -> None:
        super().__init__(inner)
        self._scope: StorageScopeContext = scope
        self.platform_scopes: list[StorageScope] = []

    def sum_platform(
        self, occurred_from: Microseconds, occurred_to: Microseconds
    ) -> list[UsageKindTotal]:
        self.platform_scopes.append(self._scope.current())
        return super().sum_platform(occurred_from, occurred_to)


def test_the_gauge_reads_once_a_minute_platform_wide_and_anew_each_day() -> None:
    scope = StorageScopeContext()
    collection = InMemoryDocumentCollectionAdapter(UsageEventDocument)
    usage = ScopeRecordingUsageSpend(UsageSpendRepository(collection), scope)
    gauge = PlatformSpendGaugeRegistry(usage, scope)
    now = micros(NOON)

    # A turn asks from inside its business's scope; the sum escalates.
    with scope.scoped_to_business(BusinessId()):
        first = gauge.spend_today(now)
        again = gauge.spend_today(Microseconds(int(now) + 59 * 1_000_000))
    assert first == again
    assert usage.platform_scopes == [StorageScope.platform_wide()]

    gauge.spend_today(Microseconds(int(now) + 60 * 1_000_000))
    gauge.spend_today(micros(NOON + timedelta(days=1)))
    assert len(usage.platform_scopes) == 3
