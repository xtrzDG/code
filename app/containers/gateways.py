from dependency_injector import containers
from dependency_injector.providers import (
    DependenciesContainer,
    Dict,
    Factory,
    List,
    Singleton,
)

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.facilitators import FacilitatorsContainer
from app.containers.operators.operators_container import OperatorsContainer
from app.containers.periodic_jobs import periodic_job_specs
from app.containers.queued_jobs import queued_job_operator_map
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.gateways.metrics.api_availability_tally import ApiAvailabilityTally
from app.gateways.worker.background_worker import BackgroundWorker
from app.gateways.worker.heartbeat_recorder import WorkerHeartbeatRecorder
from app.gateways.worker.job_telemetry import JobTelemetry


class GatewaysContainer(containers.DeclarativeContainer):
    """
    Transport entry points built from operators. The HTTP routers are
    assembled by `app.gateways.http.router_assembly`; the background worker
    (time-triggered transport) is wired here.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    operators: OperatorsContainer = composed_container_edge(OperatorsContainer)  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    # Periodic jobs in the order they run within a tick
    # (`periodic_jobs.py`) and the handlers of queued jobs by job name
    # (`queued_jobs.py`), each built from operators.
    periodic_jobs: List = periodic_job_specs(operators)
    queued_job_operators: Dict = queued_job_operator_map(operators)
    # The pulse of this worker process (GET /readyz reports its age).
    worker_heartbeat_recorder: Factory[WorkerHeartbeatRecorder] = Factory(
        WorkerHeartbeatRecorder,
        heartbeat_repo=repositories.worker_heartbeat_repo,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
        release=config.app_settings.provided.release_version,
    )
    # Pickup delays, dead jobs and the spans of queued jobs.
    job_telemetry: Factory[JobTelemetry] = Factory(
        JobTelemetry,
        metrics=utilities.service_metrics,
        tracer=utilities.span_tracer,
    )
    background_worker: Factory[BackgroundWorker] = Factory(
        BackgroundWorker,
        periodic_jobs=periodic_jobs,
        queued_job_operators=queued_job_operators,
        job_repo=repositories.queued_job_repo,
        periodic_run_repo=repositories.periodic_job_run_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        error_reporter=facilitators.error_reporter,
        poll_seconds=config.app_settings.provided.worker_poll_seconds,
        storage_scope=utilities.storage_scope,
        job_wakeup=adapters.job_wakeup,
        lane_concurrency=config.app_settings.provided.worker_lane_concurrency,
        job_monitor=facilitators.job_monitor,
        heartbeat_recorder=worker_heartbeat_recorder,
        inbound_poll_seconds=config.app_settings.provided.worker_inbound_poll_seconds,
        lanes=config.app_settings.provided.worker_lanes,
        job_telemetry=job_telemetry,
    )
    # The API availability SLI of this API process, flushed every 15 s
    # (started by `start_telemetry` of the API, closed on shutdown).
    api_availability_tally: Singleton[ApiAvailabilityTally] = Singleton(
        ApiAvailabilityTally,
        operator=operators.telemetry.add_api_request_counts_operator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
