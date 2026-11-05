from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.platform_use_cases import PlatformUseCasesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.data_tasks import (
    DataTasksQuery,
    DataTasksView,
    RetryDataTaskCommand,
    RetryDataTaskResult,
)
from app.schemas.dto.jobs import JobReport, JobTick
from app.use_cases.admin.alerts.data_task_alert_checks import DataTaskAlertChecks
from app.use_cases.admin.system.get_data_tasks_use_case import GetDataTasksUseCase
from app.use_cases.admin.system.retry_data_task_use_case import RetryDataTaskUseCase
from app.use_cases.maintenance.data_tasks.run_data_tasks_use_case import (
    DATA_TASK_BATCH_SIZE,
    RunDataTasksUseCase,
)


class DataTaskUseCasesContainer(containers.DeclarativeContainer):
    """
    Post-deploy data tasks (docs/operations/deploys.md): the batch worker's
    `run_data_tasks` job, the data-task card of the admin system page with
    its "run again", and the check behind the BACKFILL_STALLED alert.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    platform_use_cases: PlatformUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    run_data_tasks_use_case: Factory[UseCaseContract[JobTick, JobReport]] = Factory(
        RunDataTasksUseCase,
        registry=registries.data_task_registry,
        state_repo=repositories.data_task_state_repo,
        batches=adapters.data_task_batches,
        locks=registries.data_task_lock_registry,
        pulse_repo=repositories.system_health_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        release=config.app_settings.provided.release_version,
    )
    get_data_tasks_use_case: Factory[UseCaseContract[DataTasksQuery, DataTasksView]] = (
        Factory(
            GetDataTasksUseCase,
            authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
            registry=registries.data_task_registry,
            state_repo=repositories.data_task_state_repo,
            pulse_repo=repositories.system_health_repo,
            database_size=adapters.database_size,
            wall_clock=time_provider.microsecond_wall_clock,
            release=config.app_settings.provided.release_version,
            batch_size=DATA_TASK_BATCH_SIZE,
        )
    )
    retry_data_task_use_case: Factory[
        UseCaseContract[RetryDataTaskCommand, RetryDataTaskResult]
    ] = Factory(
        RetryDataTaskUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        registry=registries.data_task_registry,
        state_repo=repositories.data_task_state_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # The BACKFILL_STALLED check of the platform alerts job.
    data_task_alert_checks: Factory[DataTaskAlertChecks] = Factory(
        DataTaskAlertChecks,
        registry=registries.data_task_registry,
        state_repo=repositories.data_task_state_repo,
    )
