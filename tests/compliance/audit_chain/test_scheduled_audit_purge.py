"""
The daily `purge_expired_audit_log` job (PRIV-07) on a fake clock: the
entries past the 1,095-day retention leave every chain, younger ones stay
even when the 365-day floor would allow them, a second run the same day
removes nothing, and each chain still verifies.
"""

from typed_time_provider import Microseconds, WallClock

from app.adapters.compliance.in_memory_audit_chain_purge_adapter import (
    InMemoryAuditChainPurgeAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.gateways.worker.periodic.purge_expired_audit_log import (
    PURGE_EXPIRED_AUDIT_LOG_JOB,
)
from app.repositories.business_repositories import BusinessRepository
from app.schemas.constants.compliance import AuditAction, AuditChainStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.compliance.constrained_integers import AuditChainPosition
from app.schemas.typings.compliance.constrained_strings import AuditChainKey
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.compliance.audit_chain.audit_chain_verification import (
    AuditChainVerification,
)
from app.use_cases.maintenance.purge_audit_log_use_case import PurgeAuditLogUseCase
from app.use_cases.maintenance.purge_expired_audit_log_use_case import (
    PurgeExpiredAuditLogUseCase,
)
from app.utilities.compliance.audit_chain_hashing import (
    PLATFORM_CHAIN_KEY,
    chain_key_of,
)
from tests.compliance.audit_chain.audit_entries import MINUTE, START, entry
from tests.compliance.audit_trail_store import AuditTrailStore
from tests.notifications.alert_world import build_business

DAY: int = 24 * 60 * MINUTE
RETENTION: int = 1_095 * DAY


class FakeClock:
    """A wall clock the test moves by hand."""

    def __init__(self, now: int) -> None:
        self.now: int = now
        self.wall_clock: WallClock[Microseconds] = WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: self.now * 1_000,
        )


class ScheduledPurgeWorld:
    """One business's chain and the platform's, five entries a minute apart."""

    def __init__(self, now: int) -> None:
        self.clock = FakeClock(now)
        self.store = AuditTrailStore()
        businesses = BusinessRepository(
            InMemoryDocumentCollectionAdapter[BusinessDocument](BusinessDocument)
        )
        self.business: BusinessDocument = build_business(UserId(), UserId())
        businesses.save(self.business)
        for minute in range(5):
            self.store.log.append(entry(None, minute, action=AuditAction.LOGIN))
            self.store.log.append(entry(self.business.id, minute))
        self.job = PurgeExpiredAuditLogUseCase(
            purge_audit_log=PurgeAuditLogUseCase(
                purges=InMemoryAuditChainPurgeAdapter(
                    self.store.entries, self.store.checkpoints, self.clock.wall_clock
                ),
                business_repo=businesses,
                audit_log_repo=self.store.log,
                wall_clock=self.clock.wall_clock,
            ),
            wall_clock=self.clock.wall_clock,
        )

    @property
    def chains(self) -> list[AuditChainKey]:
        return [PLATFORM_CHAIN_KEY, chain_key_of(self.business.id)]

    def run(self) -> JobReport:
        return self.job.run(
            JobTick(
                job_name=PURGE_EXPIRED_AUDIT_LOG_JOB,
                scheduled_at=Microseconds(self.clock.now),
            )
        )

    def actions(self, chain: AuditChainKey) -> list[tuple[AuditAction, int]]:
        """Each entry left on the chain: its action and its minute after START."""

        return [
            (stored.action, (int(stored.created_at) - START) // MINUTE)
            for stored in self.store.chains.entries_from(
                chain, AuditChainPosition(1), DocumentQueryLimit(50)
            )
        ]

    def status(self, chain: AuditChainKey) -> AuditChainStatus:
        return (
            AuditChainVerification(self.store.chains)
            .verify(chain, None, Microseconds(self.clock.now))
            .status
        )


def test_the_entries_past_the_retention_leave_every_chain() -> None:
    # Three entries (minutes 0, 1 and 2) are past 1,095 days.
    world = ScheduledPurgeWorld(START + RETENTION + 2 * MINUTE + MINUTE // 2)

    report = world.run()

    assert int(report.processed_count) == 6
    for chain in world.chains:
        left = world.actions(chain)
        assert [minute for _, minute in left[:2]] == [3, 4]
        assert left[2][0] is AuditAction.RETENTION_PURGE
        assert world.status(chain) is AuditChainStatus.INTACT


def test_a_second_run_the_same_day_removes_nothing_more() -> None:
    world = ScheduledPurgeWorld(START + RETENTION + 2 * MINUTE + MINUTE // 2)
    world.run()
    before = {chain: world.actions(chain) for chain in world.chains}

    again = world.run()

    assert int(again.processed_count) == 0
    assert {chain: world.actions(chain) for chain in world.chains} == before


def test_the_next_day_purges_what_has_aged_past_the_retention() -> None:
    world = ScheduledPurgeWorld(START + RETENTION + 2 * MINUTE + MINUTE // 2)
    world.run()
    world.clock.now += DAY

    report = world.run()

    assert int(report.processed_count) == 4
    for chain in world.chains:
        # Only the purges' own entries are left, both of them recent.
        assert [action for action, _ in world.actions(chain)] == [
            AuditAction.RETENTION_PURGE,
            AuditAction.RETENTION_PURGE,
        ]
        assert world.status(chain) is AuditChainStatus.INTACT


def test_entries_younger_than_the_retention_stay_past_the_yearly_floor() -> None:
    # Two years on: the 365-day floor of the operator's command would allow
    # a purge, the 1,095-day retention does not.
    world = ScheduledPurgeWorld(START + 2 * 365 * DAY)

    report = world.run()

    assert int(report.processed_count) == 0
    for chain in world.chains:
        assert [minute for _, minute in world.actions(chain)] == [0, 1, 2, 3, 4]
