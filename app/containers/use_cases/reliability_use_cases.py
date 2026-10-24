from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.platform_use_cases import PlatformUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.monitoring import DirectPlatformAlertFacilitatorContract
from app.contracts.use_case_contract import UseCaseContract
from app.facilitators.monitoring.direct_platform_alert_facilitator import (
    DirectPlatformAlertFacilitator,
)
from app.schemas.dto.incidents import (
    CreateIncidentCommand,
    IncidentView,
    LinkIncidentAnnouncementCommand,
)
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.pipeline_health import (
    PipelineHealthQuery,
    PipelineHealthReport,
    PipelineWatchReport,
    PipelineWatchTick,
)
from app.schemas.typings.monitoring.constrained_strings import MonitorHolderName
from app.use_cases.admin.alerts.watch_pipeline_use_case import WatchPipelineUseCase
from app.use_cases.admin.incidents.create_incident_use_case import (
    CreateIncidentUseCase,
)
from app.use_cases.admin.incidents.expand_incident_use_case import (
    ExpandIncidentUseCase,
)
from app.use_cases.admin.incidents.incident_reach import IncidentReach
from app.use_cases.admin.incidents.link_incident_announcement_use_case import (
    LinkIncidentAnnouncementUseCase,
)
from app.use_cases.admin.incidents.owner_breach_notices import OwnerBreachNotices
from app.use_cases.observability.check_pipeline_health_use_case import (
    CheckPipelineHealthUseCase,
)
from app.utilities.monitoring.monitor_holder import this_process_holder


class ReliabilityUseCasesContainer(containers.DeclarativeContainer):
    """
    The platform's reliability seen from outside the workers (1173): GET
    /healthz/pipeline for the external monitor, the API's pipeline
    watchdog with the alerts it sends straight to the team, and recording
    an incident (for named businesses or, walked in batches, for all).
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    platform_use_cases: PlatformUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

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

    # --- Recording an incident, and its walk over every business (1173).
    incident_reach: Factory[IncidentReach] = Factory(
        IncidentReach,
        breach_notices=Factory(
            OwnerBreachNotices,
            user_repo=repositories.user_repo,
            manager_notifier=facilitators.manager_notification_facilitator,
        ),
        audit_log_repo=repositories.audit_log_repo,
    )
    create_incident_use_case: Factory[
        UseCaseContract[CreateIncidentCommand, IncidentView]
    ] = Factory(
        CreateIncidentUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        business_repo=repositories.business_repo,
        incident_repo=repositories.incident_repo,
        reach=incident_reach,
        job_queue=facilitators.job_queue_facilitator,
        unit_of_work=adapters.storage_unit_of_work,
        step_up=utilities.step_up_guard,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    expand_incident_use_case: Factory[UseCaseContract[QueuedJobInput, JobReport]] = (
        Factory(
            ExpandIncidentUseCase,
            incident_repo=repositories.incident_repo,
            business_repo=repositories.business_repo,
            reach=incident_reach,
            job_queue=facilitators.job_queue_facilitator,
            unit_of_work=adapters.storage_unit_of_work,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    link_incident_announcement_use_case: Factory[
        UseCaseContract[LinkIncidentAnnouncementCommand, IncidentView]
    ] = Factory(
        LinkIncidentAnnouncementUseCase,
        incident_repo=repositories.incident_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
