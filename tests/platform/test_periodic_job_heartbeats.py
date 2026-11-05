"""
The periodic jobs' heartbeats, the missed-run alert's source without
Sentry: a starting worker registers every shared job it knows (keeping
what earlier workers recorded), and after each tick the jobs that
succeeded get their next due time; a failing job keeps its old one.
"""

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.gateways.worker.background_worker import BackgroundWorker, PeriodicJobSpec
from app.gateways.worker.heartbeat_recorder import WorkerHeartbeatRecorder
from app.gateways.worker.periodic_job_heartbeats import (
    PeriodicJobHeartbeats,
    job_run_allowance,
)
from app.repositories.platform_safety_repositories import (
    PeriodicJobHeartbeatRepository,
)
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.periodic_job_heartbeats import PeriodicJobHeartbeatDocument
from app.schemas.typings.platform.constrained_integers import (
    JobIntervalSeconds,
    WorkerPollSeconds,
)
from app.schemas.typings.platform.constrained_strings import (
    JobName,
    ReleaseVersion,
    WorkerHostName,
)
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.platform.readiness_fakes import build_heartbeat_repo
from tests.platform.worker_fakes import (
    TEST_LANE_CONCURRENCY,
    ControlledClock,
    CountingPeriodicOperator,
    RecordingErrorReporter,
    build_job_stores,
)

SECOND: int = 1_000_000
MINUTE: int = 60 * SECOND
HOURLY: JobIntervalSeconds = JobIntervalSeconds(3_600)
DAILY: JobIntervalSeconds = JobIntervalSeconds(24 * 3_600)
REMINDERS: JobName = JobName("send_booking_reminders")
BROKEN: JobName = JobName("broken_job")
BATCH: JobName = JobName("nightly_batch")


def specs() -> list[PeriodicJobSpec]:
    return [
        PeriodicJobSpec(REMINDERS, HOURLY, CountingPeriodicOperator()),
        PeriodicJobSpec(BROKEN, HOURLY, CountingPeriodicOperator(should_fail=True)),
        # A job of a lane this worker does not serve: registered all the same.
        PeriodicJobSpec(
            BATCH, DAILY, CountingPeriodicOperator(), lane=JobLane.AUTOTESTS
        ),
        PeriodicJobSpec(
            JobName("flush_llm_traces"),
            JobIntervalSeconds(60),
            CountingPeriodicOperator(),
            is_process_local=True,
        ),
    ]


def build(
    clock: ControlledClock, repo: PeriodicJobHeartbeatRepository, release: str = "r42"
) -> BackgroundWorker:
    stores = build_job_stores()
    recorder = WorkerHeartbeatRecorder(
        heartbeat_repo=build_heartbeat_repo(),
        storage_scope=StorageScopeContext(),
        wall_clock=clock.wall_clock(),
        release=ReleaseVersion(release),
        host_name=WorkerHostName("worker-1"),
        job_heartbeats=PeriodicJobHeartbeats(
            specs(), repo, StorageScopeContext(), ReleaseVersion(release)
        ),
    )
    recorder.start()
    return BackgroundWorker(
        periodic_jobs=specs(),
        queued_job_operators={},
        job_repo=stores.job_repo,
        periodic_run_repo=stores.periodic_run_repo,
        wall_clock=clock.wall_clock(),
        error_reporter=RecordingErrorReporter(),
        poll_seconds=WorkerPollSeconds(5),
        storage_scope=StorageScopeContext(),
        job_wakeup=stores.job_wakeup,
        lane_concurrency=TEST_LANE_CONCURRENCY,
        heartbeat_recorder=recorder,
        lanes=(JobLane.DEFAULT,),
    )


def by_name(
    repo: PeriodicJobHeartbeatRepository,
) -> dict[JobName, PeriodicJobHeartbeatDocument]:
    return {
        heartbeat.job_name: heartbeat
        for heartbeat in repo.get_many(
            [REMINDERS, BROKEN, BATCH, JobName("flush_llm_traces")]
        )
    }


def new_repo() -> PeriodicJobHeartbeatRepository:
    return PeriodicJobHeartbeatRepository(
        InMemoryDocumentCollectionAdapter(PeriodicJobHeartbeatDocument)
    )


def test_a_starting_worker_registers_every_shared_job_with_a_full_allowance() -> None:
    clock = ControlledClock()
    repo = new_repo()
    started = Microseconds(clock.nanoseconds // 1_000)

    build(clock, repo)

    heartbeats = by_name(repo)
    assert set(heartbeats) == {REMINDERS, BROKEN, BATCH}
    batch = heartbeats[BATCH]
    assert batch.lane is JobLane.AUTOTESTS and batch.last_succeeded_at is None
    assert int(batch.due_by) == int(started) + job_run_allowance(DAILY)
    assert batch.release == ReleaseVersion("r42")


def test_a_success_moves_the_due_time_and_a_failure_does_not() -> None:
    clock = ControlledClock()
    repo = new_repo()
    started = clock.nanoseconds // 1_000
    worker = build(clock, repo)
    registered = by_name(repo)
    clock.advance(30)

    worker.run_periodic_tick()

    heartbeats = by_name(repo)
    reminders = heartbeats[REMINDERS]
    assert reminders.last_succeeded_at is not None
    assert int(reminders.due_by) == int(
        reminders.last_succeeded_at
    ) + job_run_allowance(HOURLY)
    assert heartbeats[BROKEN] == registered[BROKEN]
    # The batch lane is not this worker's: its heartbeat waits for its worker.
    assert heartbeats[BATCH] == registered[BATCH]
    # Past the registration's allowance the broken job is overdue; the
    # reminders succeeded 30 s after it, so they are not yet.
    overdue = repo.list_overdue(
        Microseconds(started + job_run_allowance(HOURLY) + SECOND),
        DocumentQueryLimit(10),
    )
    assert [heartbeat.job_name for heartbeat in overdue] == [BROKEN]


def test_a_restart_keeps_the_record_and_restamps_the_release() -> None:
    clock = ControlledClock()
    repo = new_repo()
    build(clock, repo).run_periodic_tick()
    before = by_name(repo)
    clock.advance(600)

    build(clock, repo, release="r43")

    after = by_name(repo)
    assert after[REMINDERS].last_succeeded_at == before[REMINDERS].last_succeeded_at
    assert after[REMINDERS].due_by == before[REMINDERS].due_by
    assert after[BROKEN].registered_at == before[BROKEN].registered_at
    assert {heartbeat.release for heartbeat in after.values()} == {
        ReleaseVersion("r43")
    }


def test_the_allowance_is_the_interval_and_a_grace_of_at_least_half_an_hour() -> None:
    assert job_run_allowance(JobIntervalSeconds(60)) == 31 * MINUTE
    assert job_run_allowance(HOURLY) == 90 * MINUTE
    assert job_run_allowance(DAILY) == 30 * 60 * MINUTE


def test_an_old_worker_during_a_deploy_keeps_the_new_release_s_stamp() -> None:
    clock = ControlledClock()
    repo = new_repo()
    old = build(clock, repo, release="r42")
    clock.advance(60)
    # The new release's worker starts while the old one still runs.
    build(clock, repo, release="r43")
    clock.advance(30)

    old.run_periodic_tick()

    reminders = by_name(repo)[REMINDERS]
    assert reminders.last_succeeded_at is not None
    # Still the new release's job: once it fails there, its alert sees it.
    assert reminders.release == ReleaseVersion("r43")


def test_a_starting_worker_forgets_jobs_a_deploy_removed_a_week_ago() -> None:
    repo = new_repo()
    start = Microseconds(1_793_620_800_000_000)
    removed = PeriodicJobSpec(JobName("old_report"), HOURLY, CountingPeriodicOperator())
    PeriodicJobHeartbeats(
        [*specs(), removed], repo, StorageScopeContext(), ReleaseVersion("r42")
    ).register(start)
    later = PeriodicJobHeartbeats(
        specs(), repo, StorageScopeContext(), ReleaseVersion("r43")
    )

    # Overdue for less than a week: kept (it may still be an old worker's).
    later.register(Microseconds(int(start) + 2 * 24 * 3_600 * SECOND))
    assert repo.get_many([removed.name]) != []

    later.register(Microseconds(int(start) + 9 * 24 * 3_600 * SECOND))

    assert repo.get_many([removed.name]) == []
    # The jobs this release knows stay, however overdue.
    assert set(by_name(repo)) == {REMINDERS, BROKEN, BATCH}
