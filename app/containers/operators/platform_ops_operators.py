from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.platform_ops_pipelines import (
    PlatformOpsPipelinesContainer,
)
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class PlatformOpsOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the platform's own operations. The alerts job and the
    system page count across every business, the token check reads every
    business's Meta channels, an incident names several
    (each gets its own owner notices and audit entry) and the backup runs
    belong to none, so those run platform-wide; sending an alert message
    reads no storage and runs in the worker's own (unscoped) scope.
    """

    platform_ops_pipelines: PlatformOpsPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    check_platform_alerts_operator = platform_pipeline_operator(
        platform_ops_pipelines.check_platform_alerts_pipeline, storage_scope
    )
    send_platform_alert_operator = pipeline_operator(
        platform_ops_pipelines.send_platform_alert_pipeline, storage_scope
    )
    get_admin_system_operator = platform_pipeline_operator(
        platform_ops_pipelines.get_admin_system_pipeline, storage_scope
    )
    record_maintenance_run_operator = platform_pipeline_operator(
        platform_ops_pipelines.record_maintenance_run_pipeline, storage_scope
    )
    create_incident_operator = platform_pipeline_operator(
        platform_ops_pipelines.create_incident_pipeline, storage_scope
    )
    list_incidents_operator = platform_pipeline_operator(
        platform_ops_pipelines.list_incidents_pipeline, storage_scope
    )
    check_channel_credentials_operator = platform_pipeline_operator(
        platform_ops_pipelines.check_channel_credentials_pipeline, storage_scope
    )
    # Production quality: the nightly sample reads and judges conversations
    # of every business; a client's trend is read in that client's scope.
    sample_conversation_quality_operator = platform_pipeline_operator(
        platform_ops_pipelines.sample_conversation_quality_pipeline, storage_scope
    )
    get_client_quality_operator = pipeline_operator(
        platform_ops_pipelines.get_client_quality_pipeline, storage_scope
    )

    # The public status page, its daily record and the admin's
    # announcements, the help center (no storage) and each person's
    # guidance: platform collections only, read in the caller's unscoped
    # storage (no business, nothing platform-wide).
    record_platform_status_operator = pipeline_operator(
        platform_ops_pipelines.record_platform_status_pipeline, storage_scope
    )
    create_announcement_operator = pipeline_operator(
        platform_ops_pipelines.create_announcement_pipeline, storage_scope
    )
    update_announcement_operator = pipeline_operator(
        platform_ops_pipelines.update_announcement_pipeline, storage_scope
    )
    list_announcements_operator = pipeline_operator(
        platform_ops_pipelines.list_announcements_pipeline, storage_scope
    )
    get_platform_status_operator = pipeline_operator(
        platform_ops_pipelines.get_platform_status_pipeline, storage_scope
    )
    get_help_center_operator = pipeline_operator(
        platform_ops_pipelines.get_help_center_pipeline, storage_scope
    )
    get_help_article_operator = pipeline_operator(
        platform_ops_pipelines.get_help_article_pipeline, storage_scope
    )
    search_help_operator = pipeline_operator(
        platform_ops_pipelines.search_help_pipeline, storage_scope
    )
    get_support_contacts_operator = pipeline_operator(
        platform_ops_pipelines.get_support_contacts_pipeline, storage_scope
    )
    get_help_progress_operator = pipeline_operator(
        platform_ops_pipelines.get_help_progress_pipeline, storage_scope
    )
    mark_coach_mark_seen_operator = pipeline_operator(
        platform_ops_pipelines.mark_coach_mark_seen_pipeline, storage_scope
    )
    reset_coach_marks_operator = pipeline_operator(
        platform_ops_pipelines.reset_coach_marks_pipeline, storage_scope
    )
    read_changelog_operator = pipeline_operator(
        platform_ops_pipelines.read_changelog_pipeline, storage_scope
    )
