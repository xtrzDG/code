from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.platform_use_cases import PlatformUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.admin_system import (
    AdminSystemQuery,
    AdminSystemView,
    MaintenanceRunView,
)
from app.schemas.dto.incidents import (
    CreateIncidentCommand,
    IncidentPage,
    IncidentsQuery,
    IncidentView,
)
from app.schemas.dto.jobs import JobReport, JobTick, QueuedJobInput
from app.schemas.dto.maintenance_runs import RecordMaintenanceRunCommand
from app.use_cases.admin.alerts.alert_checks import PlatformAlertChecks
from app.use_cases.admin.alerts.check_platform_alerts_use_case import (
    CheckPlatformAlertsUseCase,
)
from app.use_cases.admin.alerts.send_platform_alert_use_case import (
    SendPlatformAlertUseCase,
)
from app.use_cases.admin.incidents.create_incident_use_case import (
    CreateIncidentUseCase,
)
from app.use_cases.admin.incidents.list_incidents_use_case import ListIncidentsUseCase
from app.use_cases.admin.incidents.owner_breach_notices import OwnerBreachNotices
from app.use_cases.admin.system.get_admin_system_use_case import (
    GetAdminSystemUseCase,
)
from app.use_cases.admin.system.record_maintenance_run_use_case import (
    RecordMaintenanceRunUseCase,
)


class PlatformOpsUseCasesContainer(containers.DeclarativeContainer):
    """
    The platform's own operations (docs/operations/slo.md, incident.md):
    the platform alerts and their delivery, the admin system page, and the
    incident log with its breach notices to owners.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    platform_use_cases: PlatformUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Platform alerts (the `platform_alerts` job and its messages).
    platform_alert_checks: Factory[PlatformAlertChecks] = Factory(
        PlatformAlertChecks,
        system_health_repo=repositories.system_health_repo,
        platform_activity_repo=repositories.platform_activity_repo,
        signal_counter=adapters.signal_counter,
    )
    check_platform_alerts_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            CheckPlatformAlertsUseCase,
            checks=platform_alert_checks,
            state_repo=repositories.platform_alert_state_repo,
            job_queue=facilitators.job_queue_facilitator,
            alert_settings=config.app_settings.provided.platform_alerts,
            cabinet_base_url=config.app_settings.provided.cabinet_base_url,
            wall_clock=time_provider.microsecond_wall_clock,
            unit_of_work=adapters.storage_unit_of_work,
        )
    )
    send_platform_alert_use_case: Factory[
        UseCaseContract[QueuedJobInput, JobReport]
    ] = Factory(
        SendPlatformAlertUseCase,
        staff_sender=facilitators.staff_notification_sender,
    )

    # --- The admin system page.
    get_admin_system_use_case: Factory[
        UseCaseContract[AdminSystemQuery, AdminSystemView]
    ] = Factory(
        GetAdminSystemUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        system_health_repo=repositories.system_health_repo,
        maintenance_run_repo=repositories.maintenance_run_repo,
        alert_state_repo=repositories.platform_alert_state_repo,
        database_size=adapters.database_size,
        backup_max_age=config.app_settings.provided.backup.max_age_hours,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # The backup and restore drill commands report their runs.
    record_maintenance_run_use_case: Factory[
        UseCaseContract[RecordMaintenanceRunCommand, MaintenanceRunView]
    ] = Factory(
        RecordMaintenanceRunUseCase,
        maintenance_run_repo=repositories.maintenance_run_repo,
        release=config.app_settings.provided.release_version,
        wall_clock=time_provider.microsecond_wall_clock,
    )

    # --- The incident log and breach notices.
    owner_breach_notices: Factory[OwnerBreachNotices] = Factory(
        OwnerBreachNotices,
        user_repo=repositories.user_repo,
        manager_notifier=facilitators.manager_notification_facilitator,
    )
    create_incident_use_case: Factory[
        UseCaseContract[CreateIncidentCommand, IncidentView]
    ] = Factory(
        CreateIncidentUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        business_repo=repositories.business_repo,
        incident_repo=repositories.incident_repo,
        audit_log_repo=repositories.audit_log_repo,
        breach_notices=owner_breach_notices,
        step_up=utilities.step_up_guard,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_incidents_use_case: Factory[UseCaseContract[IncidentsQuery, IncidentPage]] = (
        Factory(
            ListIncidentsUseCase,
            authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
            incident_repo=repositories.incident_repo,
        )
    )
