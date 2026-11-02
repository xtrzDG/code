"""
The platform's own watchers as alerts: the daily budget stop (SEV1, from
the stop share of the budget on), periodic jobs whose heartbeat is past
due (without Sentry), and the latest payment reconciliation's mismatches.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.jobs import JobLane
from app.schemas.constants.monitoring import PlatformAlertCode
from app.schemas.constants.payment_reconciliation import PaymentMismatchKind
from app.schemas.constants.payments import PaymentProvider, PaymentStatus
from app.schemas.domain.payment_reconciliations import (
    PaymentMismatch,
    PaymentReconciliationDocument,
)
from app.schemas.domain.periodic_job_heartbeats import PeriodicJobHeartbeatDocument
from app.schemas.dto.platform_alerts import AlertObservation
from app.schemas.typings.billing.constrained_integers import ReconciledOrderCount
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName, ReleaseVersion
from app.schemas.typings.spend.constrained_integers import (
    PlatformDailySpendBudgetMicroUsd,
)
from app.use_cases.admin.alerts.alert_rules import PLATFORM_ALERT_RULES
from app.use_cases.admin.alerts.safety_alert_checks import PlatformSafetyAlertChecks
from app.use_cases.shared.payment_reconciliation_days import reconciliation_day
from tests.platform_ops.ops_documents import DAY, HOUR, MINUTE, NOW
from tests.platform_ops.ops_world import OpsWorld
from tests.platform_ops.test_alert_spend import DOLLAR, spend


def observe(world: OpsWorld, code: PlatformAlertCode) -> AlertObservation:
    (observation,) = world.checks().run({code: PLATFORM_ALERT_RULES[code]}, NOW)
    return observation


def test_the_budget_stop_fires_from_the_whole_budget_on() -> None:
    world = OpsWorld()
    world.spend_budget = PlatformDailySpendBudgetMicroUsd(100 * DOLLAR)
    spend(world, 99 * DOLLAR, int(NOW) - HOUR)
    almost = observe(world, PlatformAlertCode.SPEND_BUDGET_STOP)
    spend(world, 1 * DOLLAR, int(NOW) - MINUTE)

    stopped = observe(world, PlatformAlertCode.SPEND_BUDGET_STOP)

    assert not almost.is_firing and int(almost.figure) == 99
    assert stopped.is_firing and int(stopped.figure) == 100
    assert int(stopped.threshold) == 100
    assert "hand customers to the team" in str(stopped.detail)


def test_without_a_budget_the_stop_never_fires() -> None:
    world = OpsWorld()
    spend(world, 1_000 * DOLLAR, int(NOW) - HOUR)

    assert not observe(world, PlatformAlertCode.SPEND_BUDGET_STOP).is_firing


def heartbeat(
    name: str,
    *,
    due_in: int,
    succeeded_ago: int | None,
    release: str | None = None,
) -> PeriodicJobHeartbeatDocument:
    return PeriodicJobHeartbeatDocument(
        job_name=JobName(name),
        interval_seconds=JobIntervalSeconds(3_600),
        lane=JobLane.DEFAULT,
        release=None if release is None else ReleaseVersion(release),
        registered_at=Microseconds(int(NOW) - DAY),
        last_succeeded_at=(
            None if succeeded_ago is None else Microseconds(int(NOW) - succeeded_ago)
        ),
        due_by=Microseconds(int(NOW) + due_in),
        created_at=Microseconds(int(NOW) - DAY),
        updated_at=NOW,
    )


def test_jobs_past_their_heartbeat_are_missed_runs() -> None:
    world = OpsWorld()
    world.job_heartbeats.save(
        heartbeat("end_trials", due_in=-MINUTE, succeeded_ago=3 * HOUR)
    )
    world.job_heartbeats.save(heartbeat("retention", due_in=-HOUR, succeeded_ago=None))
    world.job_heartbeats.save(
        heartbeat("platform_alerts", due_in=HOUR, succeeded_ago=0)
    )

    missed = observe(world, PlatformAlertCode.MISSED_JOB_RUNS)

    assert missed.is_firing and int(missed.figure) == 2
    assert "end_trials (every 1 h, lane default): last success 3 h ago" in str(
        missed.detail
    )
    assert "retention" in str(missed.detail) and "no success since" in str(
        missed.detail
    )
    assert "platform_alerts" not in str(missed.detail)


def test_heartbeats_of_another_release_are_not_this_release_s_jobs() -> None:
    world = OpsWorld()
    world.job_heartbeats.save(
        heartbeat("removed_job", due_in=-DAY, succeeded_ago=2 * DAY, release="r41")
    )

    current = PlatformSafetyAlertChecks(
        world.job_heartbeats, world.reconciliations, ReleaseVersion("r42")
    )
    rule = PLATFORM_ALERT_RULES[PlatformAlertCode.MISSED_JOB_RUNS]

    assert not current.missed_job_runs(rule, NOW).is_firing
    assert not observe(world, PlatformAlertCode.MISSED_JOB_RUNS).is_firing


def test_the_latest_reconciliation_s_mismatches_page() -> None:
    world = OpsWorld()
    assert not observe(world, PlatformAlertCode.PAYMENT_MISMATCH).is_firing

    world.reconciliations.save(
        PaymentReconciliationDocument(
            day=reconciliation_day(NOW),
            ran_at=NOW,
            checked_count=ReconciledOrderCount(12),
            unreadable_count=ReconciledOrderCount(1),
            mismatches=[
                PaymentMismatch(
                    payment_order_id=PaymentOrderId(),
                    business_id=BusinessId(),
                    provider=PaymentProvider.FLITT,
                    recorded_status=PaymentStatus.CREATED,
                    provider_status=PaymentStatus.APPROVED,
                    kind=PaymentMismatchKind.PAID_AT_PROVIDER,
                )
            ],
            created_at=NOW,
            updated_at=NOW,
        )
    )
    mismatch = observe(world, PlatformAlertCode.PAYMENT_MISMATCH)

    assert mismatch.is_firing and int(mismatch.figure) == 1
    assert "compared 12 payments" in str(mismatch.detail)
