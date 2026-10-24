from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.platform_use_cases import PlatformUseCasesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.service_levels import (
    ApiRequestCounts,
    ErrorBudgetQuery,
    ErrorBudgetView,
)
from app.schemas.dto.telemetry import JobQueueMeasurement, JobQueueQuery
from app.use_cases.observability.add_api_request_counts_use_case import (
    AddApiRequestCountsUseCase,
)
from app.use_cases.observability.get_error_budget_use_case import (
    GetErrorBudgetUseCase,
)
from app.use_cases.observability.measure_job_queues_use_case import (
    MeasureJobQueuesUseCase,
)
from app.use_cases.observability.record_service_levels_use_case import (
    RecordServiceLevelsUseCase,
)


class TelemetryUseCasesContainer(containers.DeclarativeContainer):
    """
    The platform measuring itself (docs/operations/observability.md): the
    job queue for metrics scrapes, the hourly service level indicators and
    the error budgets they spend.
    """

    platform_use_cases: PlatformUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]

    measure_job_queues_use_case: Factory[
        UseCaseContract[JobQueueQuery, JobQueueMeasurement]
    ] = Factory(
        MeasureJobQueuesUseCase,
        system_health_repo=repositories.system_health_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # The API processes' request counts, flushed every 15 s (1163).
    add_api_request_counts_use_case: Factory[
        UseCaseContract[ApiRequestCounts, JobReport]
    ] = Factory(
        AddApiRequestCountsUseCase,
        slot_repo=repositories.service_level_slot_repo,
    )
    # The `record_sli` periodic job.
    record_service_levels_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            RecordServiceLevelsUseCase,
            slot_repo=repositories.service_level_slot_repo,
            hour_repo=repositories.service_level_hour_repo,
            source_repo=repositories.service_level_source_repo,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    # The error budget card of /admin/system.
    get_error_budget_use_case: Factory[
        UseCaseContract[ErrorBudgetQuery, ErrorBudgetView]
    ] = Factory(
        GetErrorBudgetUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        slot_repo=repositories.service_level_slot_repo,
        hour_repo=repositories.service_level_hour_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
