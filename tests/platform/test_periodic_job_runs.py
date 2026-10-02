"""Periodic jobs run once per period across workers and restarts."""

import pytest
from typed_time_provider import Microseconds

from app.gateways.worker.background_worker import BackgroundWorker, PeriodicJobSpec
from app.schemas.constants.jobs import PeriodicJobRunStatus
from app.schemas.domain.jobs import PeriodicJobRunDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.platform.constrained_integers import (
    JobAttemptCount,
    JobIntervalSeconds,
    ProcessedItemCount,
)
from app.schemas.typings.platform.constrained_strings import (
    JobLeaseToken,
    JobName,
    JobPeriodKey,
)
from app.utilities.jobs.periodic_runs import compute_period_key
from tests.platform.worker_fakes import (
    ControlledClock,
    CountingPeriodicOperator,
    build_job_stores,
    build_worker,
)

DAY: JobIntervalSeconds = JobIntervalSeconds(86_400)
DAILY_DIGEST: JobName = JobName("send_daily_digest")
STALE_TOKEN: JobLeaseToken = JobLeaseToken("0" * 32)


def daily(operator: object, name: JobName = DAILY_DIGEST) -> PeriodicJobSpec:
    return PeriodicJobSpec(
        name=name,
        interval_seconds=DAY,
        operator=operator,  # type: ignore[arg-type]
    )


def test_a_worker_restart_does_not_rerun_todays_daily_job() -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    digest = CountingPeriodicOperator()
    before_restart = build_worker(clock, [daily(digest)], stores=stores)
    before_restart.worker.run_once()

    clock.advance(10 * 60)  # the deploy
    after_restart = build_worker(clock, [daily(digest)], stores=stores)
    restarted = after_restart.worker.run_once()
    clock.advance(10 * 3600)  # 2026-09-22, 00:13 UTC
    next_day = after_restart.worker.run_once()

    assert restarted.periodic_runs == 0
    assert next_day.periodic_runs == 1
    assert len(digest.ticks) == 2
    first = stores.periodic_run_repo.get(DAILY_DIGEST, JobPeriodKey("2026-09-21"))
    second = stores.periodic_run_repo.get(DAILY_DIGEST, JobPeriodKey("2026-09-22"))
    assert first is not None and first.status is PeriodicJobRunStatus.SUCCEEDED
    assert first.processed_count == 1 and first.lease_token is None
    assert second is not None and second.status is PeriodicJobRunStatus.SUCCEEDED


class SecondWorkerTicksMeanwhile:
    """While the job runs, another worker ticks (as during a deploy)."""

    def __init__(self) -> None:
        self.ticks: list[JobTick] = []
        self.other_worker: BackgroundWorker | None = None
        self.other_runs: int = -1

    def operate(self, input_data: JobTick) -> JobReport:
        self.ticks.append(input_data)
        if self.other_worker is not None and len(self.ticks) == 1:
            self.other_runs = int(self.other_worker.run_once().periodic_runs)

        return JobReport(processed_count=ProcessedItemCount(1))


def test_two_workers_never_run_the_same_period_twice() -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    digest = SecondWorkerTicksMeanwhile()
    first = build_worker(clock, [daily(digest)], stores=stores)
    digest.other_worker = build_worker(clock, [daily(digest)], stores=stores).worker

    first.worker.run_once()

    assert len(digest.ticks) == 1
    assert digest.other_runs == 0


def test_a_run_whose_worker_died_is_taken_over_after_its_lease() -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    digest = CountingPeriodicOperator()
    now: Microseconds = clock.wall_clock().now_unix()
    period: JobPeriodKey = compute_period_key(DAY, now)
    abandoned = PeriodicJobRunDocument(
        job_name=DAILY_DIGEST,
        period_key=period,
        started_at=now,
        lease_until=Microseconds(int(now) + 60_000_000),
        lease_token=STALE_TOKEN,
        created_at=now,
        updated_at=now,
    )
    assert stores.periodic_run_repo.claim(DAILY_DIGEST, period, lambda _: abandoned)
    kit = build_worker(clock, [daily(digest)], stores=stores)

    while_leased = kit.worker.run_once()
    clock.advance(61)
    after_lease = kit.worker.run_once()

    assert while_leased.periodic_runs == 0
    assert after_lease.periodic_runs == 1
    run = stores.periodic_run_repo.get(DAILY_DIGEST, period)
    assert run is not None
    assert run.status is PeriodicJobRunStatus.SUCCEEDED
    assert run.attempts == JobAttemptCount(2)
    # The worker that died cannot overwrite the result later.
    assert not stores.periodic_run_repo.finish(abandoned, STALE_TOKEN)


def test_process_local_jobs_run_in_every_worker() -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    flush = CountingPeriodicOperator()
    spec = PeriodicJobSpec(
        name=JobName("flush_llm_traces"),
        interval_seconds=JobIntervalSeconds(60),
        operator=flush,
        is_process_local=True,
    )
    workers = [build_worker(clock, [spec], stores=stores).worker for _ in range(2)]

    for worker in workers:
        worker.run_once()
    clock.advance(30)
    for worker in workers:
        worker.run_once()
    clock.advance(30)
    for worker in workers:
        worker.run_once()

    assert len(flush.ticks) == 4
    assert (
        stores.periodic_run_repo.get(
            spec.name, spec.period_key(clock.wall_clock().now_unix())
        )
        is None
    )


@pytest.mark.parametrize(
    ("interval_seconds", "unix_seconds", "expected"),
    [
        (86_400, 1_790_000_000, "2026-09-21"),
        (86_400, 1_790_035_199, "2026-09-21"),  # 23:59:59
        (86_400, 1_790_035_200, "2026-09-22"),  # midnight UTC
        (7 * 86_400, 1_790_000_000, "2026-W39"),
        (7 * 86_400, 1_767_225_600, "2026-W01"),  # 2026-01-01, a Thursday
        (7 * 86_400, 1_766_966_400, "2026-W01"),  # Monday 2025-12-29
        (3_600, 1_790_000_000, "2026-09-21T14:00:00Z"),
        (900, 1_790_000_000, "2026-09-21T14:00:00Z"),
        (900, 1_790_000_900, "2026-09-21T14:15:00Z"),
        (60, 1_790_000_000, "2026-09-21T14:13:00Z"),
    ],
)
def test_period_keys_are_dates_iso_weeks_or_interval_starts(
    interval_seconds: int,
    unix_seconds: int,
    expected: str,
) -> None:
    period = compute_period_key(
        JobIntervalSeconds(interval_seconds),
        Microseconds(unix_seconds * 1_000_000),
    )

    assert period == expected
    assert type(period) is JobPeriodKey
