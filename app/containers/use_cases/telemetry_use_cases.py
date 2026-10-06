from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.telemetry import JobQueueMeasurement, JobQueueQuery
from app.use_cases.observability.measure_job_queues_use_case import (
    MeasureJobQueuesUseCase,
)


class TelemetryUseCasesContainer(containers.DeclarativeContainer):
    """
    The platform measuring itself (docs/operations/observability.md): the
    job queue for metrics scrapes, the hourly service level indicators and
    the error budgets they spend.
    """

    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]

    measure_job_queues_use_case: Factory[
        UseCaseContract[JobQueueQuery, JobQueueMeasurement]
    ] = Factory(
        MeasureJobQueuesUseCase,
        system_health_repo=repositories.system_health_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
