from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.platform_alert_checks_factory import (
    platform_alert_checks_factory,
)
from app.containers.use_cases.platform_use_cases import PlatformUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.admin import AdminClientQuery
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
from app.schemas.dto.platform_announcements import (
    AnnouncementAdminView,
    AnnouncementPage,
    AnnouncementsQuery,
    CreateAnnouncementCommand,
    UpdateAnnouncementCommand,
)
from app.schemas.dto.platform_status import PlatformStatusQuery, PlatformStatusView
from app.schemas.dto.quality import ClientQualityView
from app.schemas.dto.spend_guard import (
    AdminSpendQuery,
    BusinessSpendLimitsCommand,
    BusinessSpendLimitsView,
    PlatformSpendView,
)
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
from app.use_cases.admin.spend.get_platform_spend_use_case import (
    GetPlatformSpendUseCase,
)
from app.use_cases.admin.spend.set_business_spend_limits_use_case import (
    SetBusinessSpendLimitsUseCase,
)
from app.use_cases.admin.system.check_channel_credentials_use_case import (
    CheckChannelCredentialsUseCase,
)
from app.use_cases.admin.system.get_admin_system_use_case import (
    GetAdminSystemUseCase,
)
from app.use_cases.admin.system.record_maintenance_run_use_case import (
    RecordMaintenanceRunUseCase,
)
from app.use_cases.platform_status.create_announcement_use_case import (
    CreateAnnouncementUseCase,
)
from app.use_cases.platform_status.get_platform_status_use_case import (
    GetPlatformStatusUseCase,
)
from app.use_cases.platform_status.list_announcements_use_case import (
    ListAnnouncementsUseCase,
)
from app.use_cases.platform_status.record_platform_status_use_case import (
    RecordPlatformStatusUseCase,
)
from app.use_cases.platform_status.update_announcement_use_case import (
    UpdateAnnouncementUseCase,
)
from app.use_cases.quality.get_client_quality_use_case import (
    GetClientQualityUseCase,
)
from app.use_cases.quality.sample_conversation_quality_use_case import (
    SampleConversationQualityUseCase,
)


class PlatformOpsUseCasesContainer(containers.DeclarativeContainer):
    """
    The platform's own operations (docs/operations/slo.md, incident.md):
    the platform alerts and their delivery, the admin system page, and the
    incident log with its breach notices to owners.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    platform_use_cases: PlatformUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Platform alerts (the `platform_alerts` job and its messages).
    platform_alert_checks: Factory[PlatformAlertChecks] = platform_alert_checks_factory(
        repositories, adapters, config
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

    # --- Production quality: the nightly sample of real conversations the
    # judge scores (cost-capped) and a client's trend for the admin.
    sample_conversation_quality_use_case: Factory[
        UseCaseContract[JobTick, JobReport]
    ] = Factory(
        SampleConversationQualityUseCase,
        business_repo=repositories.business_repo,
        sample_input_repo=repositories.quality_sample_input_repo,
        message_repo=repositories.message_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        conversation_quality_repo=repositories.conversation_quality_repo,
        quality_totals_repo=repositories.quality_totals_repo,
        privacy_settings_repo=repositories.privacy_settings_repo,
        llm_adapter=adapters.llm_adapter,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_client_quality_use_case: Factory[
        UseCaseContract[AdminClientQuery, ClientQualityView]
    ] = Factory(
        GetClientQualityUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        business_repo=repositories.business_repo,
        conversation_quality_repo=repositories.conversation_quality_repo,
        wall_clock=time_provider.microsecond_wall_clock,
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
    # Meta channel tokens that run out (the page's "Tokens running out").
    check_channel_credentials_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            CheckChannelCredentialsUseCase,
            system_health_repo=repositories.system_health_repo,
            channel_repo=repositories.channel_repo,
            secret_cipher=adapters.secret_cipher,
            token_client=clients.meta_token_debug_client,
            meta_app_id=config.app_settings.provided.meta_app_id,
            meta_app_secret=config.app_settings.provided.meta_app_secret,
            wall_clock=time_provider.microsecond_wall_clock,
        )
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

    # --- The public status page, its history and the announcements (1111).
    get_platform_status_use_case: Factory[
        UseCaseContract[PlatformStatusQuery, PlatformStatusView]
    ] = Factory(
        GetPlatformStatusUseCase,
        alert_state_repo=repositories.platform_alert_state_repo,
        announcement_repo=repositories.platform_announcement_repo,
        status_day_repo=repositories.platform_status_day_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    record_platform_status_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            RecordPlatformStatusUseCase,
            alert_state_repo=repositories.platform_alert_state_repo,
            announcement_repo=repositories.platform_announcement_repo,
            status_day_repo=repositories.platform_status_day_repo,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    create_announcement_use_case: Factory[
        UseCaseContract[CreateAnnouncementCommand, AnnouncementAdminView]
    ] = Factory(
        CreateAnnouncementUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        announcement_repo=repositories.platform_announcement_repo,
        audit_log_repo=repositories.audit_log_repo,
        step_up=utilities.step_up_guard,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    update_announcement_use_case: Factory[
        UseCaseContract[UpdateAnnouncementCommand, AnnouncementAdminView]
    ] = Factory(
        UpdateAnnouncementUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        announcement_repo=repositories.platform_announcement_repo,
        audit_log_repo=repositories.audit_log_repo,
        step_up=utilities.step_up_guard,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_announcements_use_case: Factory[
        UseCaseContract[AnnouncementsQuery, AnnouncementPage]
    ] = Factory(
        ListAnnouncementsUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        announcement_repo=repositories.platform_announcement_repo,
    )

    # --- The spend guard for the admin: today's spend, a client's limits.
    get_platform_spend_use_case: Factory[
        UseCaseContract[AdminSpendQuery, PlatformSpendView]
    ] = Factory(
        GetPlatformSpendUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        usage_spend_repo=repositories.usage_spend_repo,
        spend_limit_mark_repo=repositories.spend_limit_mark_repo,
        business_repo=repositories.business_repo,
        settings=config.app_settings.provided.spend_guard,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    set_business_spend_limits_use_case: Factory[
        UseCaseContract[BusinessSpendLimitsCommand, BusinessSpendLimitsView]
    ] = Factory(
        SetBusinessSpendLimitsUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        business_repo=repositories.business_repo,
        business_limits_repo=repositories.business_limits_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
