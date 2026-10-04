from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.document_collections_container import (
    DocumentCollectionsContainer,
)
from app.containers.adapters.operations_collections_container import (
    OperationsCollectionsContainer,
)
from app.repositories.help_progress_repository import HelpProgressRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.maintenance_run_repository import MaintenanceRunRepository
from app.repositories.platform_activity_repository import PlatformActivityRepository
from app.repositories.platform_alert_state_repository import (
    PlatformAlertStateRepository,
)
from app.repositories.platform_announcement_repository import (
    PlatformAnnouncementRepository,
)
from app.repositories.platform_status_day_repository import (
    PlatformStatusDayRepository,
)
from app.repositories.system_health_repository import SystemHealthRepository


class OperationsRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of the platform's own operations (migration 1093): the
    system page's platform-wide counts over the existing collections
    (`health_collections`), the activity the alerts measure, the alerts'
    episodes, the recorded backups and drills, and the incident log.
    `RepositoriesContainer` extends it.
    """

    health_collections: DocumentCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]
    operations_collections: OperationsCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    system_health_repo: Singleton[SystemHealthRepository] = Singleton(
        SystemHealthRepository,
        job_collection=health_collections.queued_job_collection,
        heartbeat_collection=health_collections.worker_heartbeat_collection,
        channel_collection=health_collections.channel_collection,
        business_collection=health_collections.business_collection,
    )
    platform_activity_repo: Singleton[PlatformActivityRepository] = Singleton(
        PlatformActivityRepository,
        handoff_collection=health_collections.handoff_collection,
        outbound_collection=health_collections.outbound_message_collection,
        message_collection=health_collections.message_collection,
    )
    platform_alert_state_repo: Singleton[PlatformAlertStateRepository] = Singleton(
        PlatformAlertStateRepository,
        collection=operations_collections.platform_alert_state_collection,
    )
    maintenance_run_repo: Singleton[MaintenanceRunRepository] = Singleton(
        MaintenanceRunRepository,
        collection=operations_collections.maintenance_run_collection,
    )
    incident_repo: Singleton[IncidentRepository] = Singleton(
        IncidentRepository,
        collection=operations_collections.incident_collection,
    )
    # The status page, the banner and the cabinet's guidance (1111).
    platform_announcement_repo: Singleton[PlatformAnnouncementRepository] = Singleton(
        PlatformAnnouncementRepository,
        collection=operations_collections.platform_announcement_collection,
    )
    platform_status_day_repo: Singleton[PlatformStatusDayRepository] = Singleton(
        PlatformStatusDayRepository,
        collection=operations_collections.platform_status_day_collection,
    )
    help_progress_repo: Singleton[HelpProgressRepository] = Singleton(
        HelpProgressRepository,
        collection=operations_collections.help_progress_collection,
    )
