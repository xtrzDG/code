from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory, Singleton

from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.contracts.monitoring import DirectPlatformAlertFacilitatorContract
from app.contracts.use_case_contract import UseCaseContract
from app.facilitators.monitoring.direct_platform_alert_facilitator import (
    DirectPlatformAlertFacilitator,
)
from app.schemas.dto.pipeline_health import (
    PipelineHealthQuery,
    PipelineHealthReport,
    PipelineWatchReport,
    PipelineWatchTick,
)
from app.schemas.typings.monitoring.constrained_strings import MonitorHolderName
from app.use_cases.admin.alerts.watch_pipeline_use_case import WatchPipelineUseCase
from app.use_cases.observability.check_pipeline_health_use_case import (
    CheckPipelineHealthUseCase,
)
from app.utilities.monitoring.monitor_holder import this_process_holder


class ReliabilityUseCasesContainer(containers.DeclarativeContainer):
    """
    The platform's reliability seen from outside the workers (1173): GET
    /healthz/pipeline for the external monitor, and the API's pipeline
    watchdog with the alerts it sends straight to the team.
    """

    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]

    check_pipeline_health_use_case: Factory[
        UseCaseContract[PipelineHealthQuery, PipelineHealthReport]
    ] = Factory(
        CheckPipelineHealthUseCase,
        worker_heartbeat_repo=repositories.worker_heartbeat_repo,
        system_health_repo=repositories.system_health_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # The platform bot and SMTP, with no job queue in between.
    direct_platform_alerts: Factory[DirectPlatformAlertFacilitatorContract] = Factory(
        DirectPlatformAlertFacilitator,
        staff_sender=facilitators.staff_notification_sender,
        alert_settings=config.app_settings.provided.platform_alerts,
    )
    # This process's name in the watchdog's lease, fixed for its life.
    watchdog_holder: Singleton[MonitorHolderName] = Singleton(this_process_holder)
    watch_pipeline_use_case: Factory[
        UseCaseContract[PipelineWatchTick, PipelineWatchReport]
    ] = Factory(
        WatchPipelineUseCase,
        locks=registries.platform_alert_lock_registry,
        monitor_repo=repositories.platform_monitor_repo,
        state_repo=repositories.platform_alert_state_repo,
        worker_heartbeat_repo=repositories.worker_heartbeat_repo,
        system_health_repo=repositories.system_health_repo,
        direct_alerts=direct_platform_alerts,
        alert_settings=config.app_settings.provided.platform_alerts,
        holder=watchdog_holder,
        interval=config.app_settings.provided.platform_alerts.provided.watchdog_seconds,
        release=config.app_settings.provided.release_version,
        cabinet_base_url=config.app_settings.provided.cabinet_base_url,
        wall_clock=time_provider.microsecond_wall_clock,
    )
