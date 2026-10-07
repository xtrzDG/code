from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.document_collections_container import (
    DocumentCollectionsContainer,
)
from app.containers.adapters.operations_collections_container import (
    OperationsCollectionsContainer,
)
from app.repositories.client_standing_repository import ClientStandingRepository
from app.repositories.data_task_state_repository import DataTaskStateRepository
from app.repositories.help_progress_repository import HelpProgressRepository
from app.repositories.idempotency_key_repository import IdempotencyKeyRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.maintenance_run_repository import MaintenanceRunRepository
from app.repositories.platform_activity_repository import PlatformActivityRepository
from app.repositories.platform_alert_state_repository import (
    PlatformAlertStateRepository,
)
from app.repositories.platform_announcement_repository import (
    PlatformAnnouncementRepository,
)
from app.repositories.platform_monitor_repository import PlatformMonitorRepository
from app.repositories.platform_status_day_repository import (
    PlatformStatusDayRepository,
)
from app.repositories.service_level_repositories import (
    ServiceLevelHourRepository,
    ServiceLevelSlotRepository,
    ServiceLevelSourceRepository,
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
    # When each watcher of the platform last looked (1173).
    platform_monitor_repo: Singleton[PlatformMonitorRepository] = Singleton(
        PlatformMonitorRepository,
        collection=operations_collections.platform_monitor_collection,
    )
    maintenance_run_repo: Singleton[MaintenanceRunRepository] = Singleton(
        MaintenanceRunRepository,
        collection=operations_collections.maintenance_run_collection,
    )
    incident_repo: Singleton[IncidentRepository] = Singleton(
        IncidentRepository,
        collection=operations_collections.incident_collection,
    )
    # The platform admin's client list, refreshed by a periodic job (1122).
    client_standing_repo: Singleton[ClientStandingRepository] = Singleton(
        ClientStandingRepository,
        collection=operations_collections.client_standing_collection,
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
    # The post-deploy data tasks' progress (1164).
    data_task_state_repo: Singleton[DataTaskStateRepository] = Singleton(
        DataTaskStateRepository,
        collection=operations_collections.data_task_state_collection,
    )
    # The service level indicators and their platform-wide sources (1163).
    service_level_slot_repo: Singleton[ServiceLevelSlotRepository] = Singleton(
        ServiceLevelSlotRepository,
        collection=operations_collections.service_level_slot_collection,
    )
    service_level_hour_repo: Singleton[ServiceLevelHourRepository] = Singleton(
        ServiceLevelHourRepository,
        collection=operations_collections.service_level_hour_collection,
    )
    service_level_source_repo: Singleton[ServiceLevelSourceRepository] = Singleton(
        ServiceLevelSourceRepository,
        inbound_event_collection=health_collections.inbound_event_collection,
        message_collection=health_collections.message_collection,
    )
    idempotency_key_repo: Singleton[IdempotencyKeyRepository] = Singleton(
        IdempotencyKeyRepository,
        collection=operations_collections.idempotency_key_collection,
    )
