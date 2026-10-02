"""The periodic sweep of expired rate-limit counters."""

from typing import cast

from typed_time_provider import Microseconds, WallClock

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.containers.app import AppContainer
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.gateways.worker.periodic.sweep_rate_limit_buckets import (
    SWEEP_RATE_LIMIT_BUCKETS_JOB,
    sweep_rate_limit_buckets_job,
)
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.schemas.dto.jobs import JobTick
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.use_cases.maintenance.sweep_rate_limit_buckets_use_case import (
    SweepRateLimitBucketsUseCase,
)

SECOND: int = 1_000_000
START: int = 1_789_999_980 * SECOND


def clock_at(microseconds: int) -> WallClock[Microseconds]:
    return WallClock(
        preferred_time_unit_type=Microseconds,
        unix_nanosecond_factory=lambda: microseconds * 1_000,
    )


def test_the_sweep_reports_the_counters_it_dropped() -> None:
    registry = RequestRateLimitRegistry(InMemoryRateLimitBucketAdapter())
    for index in range(3):
        registry.try_acquire_all(
            [
                RateLimitCounter(
                    key=RateLimitKey(f"widget-poll:visitor:biz_1:v{index}"),
                    limit=RequestsPerWindow(60),
                )
            ],
            RateWindowSeconds(60),
            Microseconds(START),
        )
    tick = JobTick(
        job_name=SWEEP_RATE_LIMIT_BUCKETS_JOB,
        scheduled_at=Microseconds(START + 300 * SECOND),
    )

    report = SweepRateLimitBucketsUseCase(
        rate_limit_registry=registry,
        wall_clock=clock_at(START + 300 * SECOND),
    ).run(tick)

    assert int(report.processed_count) == 3


def test_the_worker_sweeps_every_ten_minutes() -> None:
    specs = cast(list[PeriodicJobSpec], AppContainer().gateways.periodic_jobs())
    sweeps = [spec for spec in specs if spec.name == SWEEP_RATE_LIMIT_BUCKETS_JOB]

    assert len(sweeps) == 1
    assert int(sweeps[0].interval_seconds) == 10 * 60
    assert (
        sweep_rate_limit_buckets_job(sweeps[0].operator).name
        == SWEEP_RATE_LIMIT_BUCKETS_JOB
    )
    # Unscoped: the counters are a platform table, no business is touched.
    assert (
        sweeps[0]
        .operator.operate(
            JobTick(
                job_name=SWEEP_RATE_LIMIT_BUCKETS_JOB, scheduled_at=Microseconds(START)
            )
        )
        .processed_count
        == 0
    )
