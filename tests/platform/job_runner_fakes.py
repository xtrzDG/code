"""A queued job runner and lease heartbeat over shared job stores."""

from app.gateways.worker.held_leases import HeldLeases
from app.gateways.worker.job_failure_reporter import JobFailureReporter
from app.gateways.worker.lease_heartbeat import LeaseHeartbeat
from app.gateways.worker.queued_job_runner import QueuedJobRunner
from app.schemas.typings.platform.constrained_integers import JobLeaseSeconds
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.platform.worker_fakes import (
    RUN_AUTOTESTS,
    ControlledClock,
    FlakyQueuedOperator,
    JobStores,
    RecordingErrorReporter,
)

LEASE: JobLeaseSeconds = JobLeaseSeconds(120)


def build_runner(
    clock: ControlledClock,
    stores: JobStores,
    operator: FlakyQueuedOperator,
    error_reporter: RecordingErrorReporter | None = None,
) -> tuple[QueuedJobRunner, HeldLeases, LeaseHeartbeat]:
    held_leases = HeldLeases()
    reporter = JobFailureReporter(
        RecordingErrorReporter() if error_reporter is None else error_reporter
    )
    runner = QueuedJobRunner(
        queued_job_operators={RUN_AUTOTESTS: operator},
        job_repo=stores.job_repo,
        wall_clock=clock.wall_clock(),
        storage_scope=StorageScopeContext(),
        held_leases=held_leases,
        failure_reporter=reporter,
        lease_seconds=LEASE,
    )
    heartbeat = LeaseHeartbeat(
        job_repo=stores.job_repo,
        periodic_run_repo=stores.periodic_run_repo,
        held_leases=held_leases,
        wall_clock=clock.wall_clock(),
        failure_reporter=reporter,
        lease_seconds=LEASE,
    )
    return runner, held_leases, heartbeat
