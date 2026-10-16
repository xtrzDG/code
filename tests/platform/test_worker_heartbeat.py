"""The worker writes its pulse every tick and checks periodic jobs in."""

import socket

import pytest
from typed_time_provider import Microseconds

from app.contracts.health import WorkerHeartbeatRepoContract
from app.gateways.worker.background_worker import BackgroundWorker, PeriodicJobSpec
from app.gateways.worker.heartbeat_recorder import (
    UNKNOWN_HOST_NAME,
    WorkerHeartbeatRecorder,
    current_host_name,
)
from app.schemas.constants.observability import PeriodicJobOutcome
from app.schemas.domain.jobs import WorkerHeartbeatDocument
from app.schemas.dto.observability import JobCheckIn
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.constrained_integers import (
    JobIntervalSeconds,
    WorkerPollSeconds,
)
from app.schemas.typings.platform.constrained_strings import (
    JobName,
    ReleaseVersion,
    WorkerHostName,
)
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.platform.readiness_fakes import build_heartbeat_repo, heartbeat_at
from tests.platform.worker_fakes import (
    TEST_LANE_CONCURRENCY,
    ControlledClock,
    CountingPeriodicOperator,
    CountingStopEvent,
    RecordingErrorReporter,
    build_job_stores,
)

SECOND: int = 1_000_000
HOURLY: JobIntervalSeconds = JobIntervalSeconds(3600)


class RecordingJobMonitor:
    def __init__(self) -> None:
        self.started: list[JobName] = []
        self.finished: list[tuple[JobName, PeriodicJobOutcome]] = []

    def job_started(
        self, job_name: JobName, interval_seconds: JobIntervalSeconds
    ) -> JobCheckIn:
        self.started.append(job_name)
        return JobCheckIn(job_name=job_name, interval_seconds=interval_seconds)

    def job_finished(self, check_in: JobCheckIn, outcome: PeriodicJobOutcome) -> None:
        self.finished.append((check_in.job_name, outcome))


class UnwritableHeartbeats:
    def save(self, heartbeat: WorkerHeartbeatDocument) -> None:
        del heartbeat
        raise ExternalServiceError("The database failed (OperationalError).")

    def find_freshest(self) -> WorkerHeartbeatDocument | None:
        return None

    def delete_beaten_before(self, beaten_before: Microseconds) -> DocumentCount:
        del beaten_before
        raise ExternalServiceError("The database failed (OperationalError).")


def build_recorder(
    clock: ControlledClock,
    repo: WorkerHeartbeatRepoContract | None = None,
) -> WorkerHeartbeatRecorder:
    return WorkerHeartbeatRecorder(
        heartbeat_repo=build_heartbeat_repo() if repo is None else repo,
        storage_scope=StorageScopeContext(),
        wall_clock=clock.wall_clock(),
        release=ReleaseVersion("4718714"),
        host_name=WorkerHostName("worker-1"),
    )


def build_monitored_worker(
    clock: ControlledClock,
    recorder: WorkerHeartbeatRecorder,
    monitor: RecordingJobMonitor,
) -> BackgroundWorker:
    stores = build_job_stores()
    return BackgroundWorker(
        periodic_jobs=[
            PeriodicJobSpec(
                name=JobName("send_booking_reminders"),
                interval_seconds=HOURLY,
                operator=CountingPeriodicOperator(),
            ),
            PeriodicJobSpec(
                name=JobName("broken_job"),
                interval_seconds=HOURLY,
                operator=CountingPeriodicOperator(should_fail=True),
            ),
        ],
        queued_job_operators={},
        job_repo=stores.job_repo,
        periodic_run_repo=stores.periodic_run_repo,
        wall_clock=clock.wall_clock(),
        error_reporter=RecordingErrorReporter(),
        poll_seconds=WorkerPollSeconds(5),
        storage_scope=StorageScopeContext(),
        job_wakeup=stores.job_wakeup,
        lane_concurrency=TEST_LANE_CONCURRENCY,
        job_monitor=monitor,
        heartbeat_recorder=recorder,
    )


def test_every_tick_writes_the_pulse_with_the_last_periodic_results() -> None:
    clock = ControlledClock()
    repo = build_heartbeat_repo()
    recorder = build_recorder(clock, repo)
    monitor = RecordingJobMonitor()
    worker = build_monitored_worker(clock, recorder, monitor)

    worker.run_once()
    clock.advance(15)
    worker.run_periodic_tick()

    pulse = repo.find_freshest()
    assert pulse is not None
    assert pulse.id == recorder.worker_id
    assert int(pulse.beat_at) - int(pulse.started_at) == 15 * SECOND
    assert pulse.release == ReleaseVersion("4718714")
    assert [(result.job_name, result.outcome) for result in pulse.periodic_results] == [
        (JobName("broken_job"), PeriodicJobOutcome.FAILED),
        (JobName("send_booking_reminders"), PeriodicJobOutcome.SUCCEEDED),
    ]
    assert pulse.periodic_results[1].processed_count == 1
    # Each period runs once: one check-in per job, with its outcome.
    assert monitor.finished == [
        (JobName("send_booking_reminders"), PeriodicJobOutcome.SUCCEEDED),
        (JobName("broken_job"), PeriodicJobOutcome.FAILED),
    ]


def test_starting_deletes_pulses_of_processes_gone_for_a_day() -> None:
    clock = ControlledClock()
    repo = build_heartbeat_repo()
    now: int = clock.nanoseconds // 1000
    repo.save(heartbeat_at(now - 2 * 24 * 3600 * SECOND))
    recorder = build_recorder(clock, repo)

    recorder.start()

    pulse = repo.find_freshest()
    assert pulse is not None and pulse.id == recorder.worker_id
    assert int(repo.delete_beaten_before(Microseconds(now - SECOND))) == 0


def test_a_pulse_that_cannot_be_written_never_stops_the_worker(
    caplog: pytest.LogCaptureFixture,
) -> None:
    clock = ControlledClock()
    recorder = build_recorder(clock, UnwritableHeartbeats())
    worker = build_monitored_worker(clock, recorder, RecordingJobMonitor())
    stop = CountingStopEvent(ticks=2)

    worker.run_forever(stop)

    assert len(stop.pauses) == 2
    assert "Old worker heartbeats were not purged" in caplog.text
    assert "Worker heartbeat was not written" in caplog.text


def test_the_host_name_falls_back_when_it_is_not_a_plain_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert current_host_name() == WorkerHostName(socket.gethostname())

    monkeypatch.setattr(socket, "gethostname", lambda: "bad host!")

    assert current_host_name() == UNKNOWN_HOST_NAME
