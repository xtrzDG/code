from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.platform_ops_orchestrators import (
    PlatformOpsOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class PlatformOpsPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the platform alerts, the admin system page and incidents."""

    platform_ops: PlatformOpsOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    check_platform_alerts_pipeline = orchestrator_pipeline(
        platform_ops.check_platform_alerts_orchestrator
    )
    send_platform_alert_pipeline = orchestrator_pipeline(
        platform_ops.send_platform_alert_orchestrator
    )
    get_admin_system_pipeline = orchestrator_pipeline(
        platform_ops.get_admin_system_orchestrator
    )
    record_maintenance_run_pipeline = orchestrator_pipeline(
        platform_ops.record_maintenance_run_orchestrator
    )
    create_incident_pipeline = orchestrator_pipeline(
        platform_ops.create_incident_orchestrator
    )
    list_incidents_pipeline = orchestrator_pipeline(
        platform_ops.list_incidents_orchestrator
    )
    check_channel_credentials_pipeline = orchestrator_pipeline(
        platform_ops.check_channel_credentials_orchestrator
    )
    sample_conversation_quality_pipeline = orchestrator_pipeline(
        platform_ops.sample_conversation_quality_orchestrator
    )
    get_client_quality_pipeline = orchestrator_pipeline(
        platform_ops.get_client_quality_orchestrator
    )

    # The status page and announcements (1111); the help center and guidance.
    get_platform_status_pipeline = orchestrator_pipeline(
        platform_ops.get_platform_status_orchestrator
    )
    record_platform_status_pipeline = orchestrator_pipeline(
        platform_ops.record_platform_status_orchestrator
    )
    create_announcement_pipeline = orchestrator_pipeline(
        platform_ops.create_announcement_orchestrator
    )
    update_announcement_pipeline = orchestrator_pipeline(
        platform_ops.update_announcement_orchestrator
    )
    list_announcements_pipeline = orchestrator_pipeline(
        platform_ops.list_announcements_orchestrator
    )
    get_help_center_pipeline = orchestrator_pipeline(
        platform_ops.get_help_center_orchestrator
    )
    get_help_article_pipeline = orchestrator_pipeline(
        platform_ops.get_help_article_orchestrator
    )
    search_help_pipeline = orchestrator_pipeline(platform_ops.search_help_orchestrator)
    get_support_contacts_pipeline = orchestrator_pipeline(
        platform_ops.get_support_contacts_orchestrator
    )
    get_help_progress_pipeline = orchestrator_pipeline(
        platform_ops.get_help_progress_orchestrator
    )
    mark_coach_mark_seen_pipeline = orchestrator_pipeline(
        platform_ops.mark_coach_mark_seen_orchestrator
    )
    reset_coach_marks_pipeline = orchestrator_pipeline(
        platform_ops.reset_coach_marks_orchestrator
    )
    read_changelog_pipeline = orchestrator_pipeline(
        platform_ops.read_changelog_orchestrator
    )
