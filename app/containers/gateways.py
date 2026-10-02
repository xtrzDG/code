from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Dict, Factory, List

from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.facilitators import FacilitatorsContainer
from app.containers.operators.operators_container import OperatorsContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.gateways.worker.background_worker import BackgroundWorker, PeriodicJobSpec
from app.gateways.worker.periodic.purge_stale_rows import purge_stale_rows_job
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.autotests.enqueue_autotest_run_use_case import RUN_AUTOTESTS_JOB

MINUTE_SECONDS: int = 60
HOUR_SECONDS: int = 60 * MINUTE_SECONDS
DAY_SECONDS: int = 24 * HOUR_SECONDS

PURGE_EXPIRED_RECORDINGS_JOB: JobName = JobName("purge_expired_recordings")
END_TRIALS_JOB: JobName = JobName("end_trials")
ENFORCE_GRACE_PERIODS_JOB: JobName = JobName("enforce_grace_periods")
CHECK_PACKAGE_USAGE_JOB: JobName = JobName("check_package_usage")
INVOICE_USAGE_OVERAGE_JOB: JobName = JobName("invoice_usage_overage")
SEND_BOOKING_REMINDERS_JOB: JobName = JobName("send_booking_reminders")
FLUSH_LLM_TRACES_JOB: JobName = JobName("flush_llm_traces")


class GatewaysContainer(containers.DeclarativeContainer):
    """
    Transport entry points built from operators. The HTTP routers are
    assembled by `app.gateways.http.router_assembly`; the background worker
    (time-triggered transport) is wired here.
    """

    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    operators: OperatorsContainer = composed_container_edge(OperatorsContainer)  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    # Periodic jobs in the order they run within a tick: trials end before
    # grace periods are enforced, so an expired trial and its grace period
    # are handled in the same hour; minutes above the package are billed
    # before the grace job looks for unpaid bills.
    periodic_jobs: List = List(
        Factory(
            PeriodicJobSpec,
            name=PURGE_EXPIRED_RECORDINGS_JOB,
            interval_seconds=JobIntervalSeconds(DAY_SECONDS),
            operator=operators.compliance.purge_expired_recordings_operator,
        ),
        Factory(
            PeriodicJobSpec,
            name=END_TRIALS_JOB,
            interval_seconds=JobIntervalSeconds(HOUR_SECONDS),
            operator=operators.billing.end_trials_operator,
        ),
        Factory(
            PeriodicJobSpec,
            name=INVOICE_USAGE_OVERAGE_JOB,
            interval_seconds=JobIntervalSeconds(HOUR_SECONDS),
            operator=operators.billing.invoice_usage_overage_operator,
        ),
        Factory(
            PeriodicJobSpec,
            name=ENFORCE_GRACE_PERIODS_JOB,
            interval_seconds=JobIntervalSeconds(HOUR_SECONDS),
            operator=operators.billing.enforce_grace_periods_operator,
        ),
        Factory(
            PeriodicJobSpec,
            name=CHECK_PACKAGE_USAGE_JOB,
            interval_seconds=JobIntervalSeconds(DAY_SECONDS),
            operator=operators.billing.check_package_usage_operator,
        ),
        Factory(
            PeriodicJobSpec,
            name=SEND_BOOKING_REMINDERS_JOB,
            interval_seconds=JobIntervalSeconds(15 * MINUTE_SECONDS),
            operator=operators.operations.send_booking_reminders_operator,
        ),
        Factory(
            PeriodicJobSpec,
            name=FLUSH_LLM_TRACES_JOB,
            interval_seconds=JobIntervalSeconds(MINUTE_SECONDS),
            operator=operators.platform.flush_llm_traces_operator,
        ),
        Factory(
            purge_stale_rows_job, operator=operators.platform.purge_stale_rows_operator
        ),
    )
    # Handlers of queued jobs by job name (the queue is filled by use cases
    # through the job queue facilitator).
    queued_job_operators: Dict = Dict(
        {RUN_AUTOTESTS_JOB: operators.assistants.run_queued_autotests_operator}
    )
    background_worker: Factory[BackgroundWorker] = Factory(
        BackgroundWorker,
        periodic_jobs=periodic_jobs,
        queued_job_operators=queued_job_operators,
        job_repo=repositories.queued_job_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        error_reporter=facilitators.error_reporter,
        poll_seconds=config.app_settings.provided.worker_poll_seconds,
        storage_scope=utilities.storage_scope,
    )
