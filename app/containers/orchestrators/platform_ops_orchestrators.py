from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.help_use_cases import HelpUseCasesContainer
from app.containers.use_cases.platform_ops_use_cases import (
    PlatformOpsUseCasesContainer,
)


class PlatformOpsOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of the platform's own operations (one use case each): the
    platform alerts job and its messages, the admin system page and the
    incident log.
    """

    platform_ops_use_cases: PlatformOpsUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    help_use_cases: HelpUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    check_platform_alerts_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.check_platform_alerts_use_case
    )
    send_platform_alert_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.send_platform_alert_use_case
    )
    get_admin_system_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.get_admin_system_use_case
    )
    record_maintenance_run_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.record_maintenance_run_use_case
    )
    create_incident_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.create_incident_use_case
    )
    list_incidents_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.list_incidents_use_case
    )
    check_channel_credentials_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.check_channel_credentials_use_case
    )
    # Production quality: the nightly sample and a client's trend.
    sample_conversation_quality_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.sample_conversation_quality_use_case
    )
    get_client_quality_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.get_client_quality_use_case
    )

    # The status page and announcements (1111); the help center and guidance.
    get_platform_status_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.get_platform_status_use_case
    )
    record_platform_status_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.record_platform_status_use_case
    )
    create_announcement_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.create_announcement_use_case
    )
    update_announcement_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.update_announcement_use_case
    )
    list_announcements_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.list_announcements_use_case
    )
    get_help_center_orchestrator = use_case_orchestrator(
        help_use_cases.get_help_center_use_case
    )
    get_help_article_orchestrator = use_case_orchestrator(
        help_use_cases.get_help_article_use_case
    )
    search_help_orchestrator = use_case_orchestrator(
        help_use_cases.search_help_use_case
    )
    get_support_contacts_orchestrator = use_case_orchestrator(
        help_use_cases.get_support_contacts_use_case
    )
    get_help_progress_orchestrator = use_case_orchestrator(
        help_use_cases.get_help_progress_use_case
    )
    mark_coach_mark_seen_orchestrator = use_case_orchestrator(
        help_use_cases.mark_coach_mark_seen_use_case
    )
    reset_coach_marks_orchestrator = use_case_orchestrator(
        help_use_cases.reset_coach_marks_use_case
    )
    read_changelog_orchestrator = use_case_orchestrator(
        help_use_cases.read_changelog_use_case
    )
