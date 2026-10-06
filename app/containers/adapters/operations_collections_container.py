from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.client_standings import ClientStandingDocument
from app.schemas.domain.data_tasks import DataTaskStateDocument
from app.schemas.domain.help_progress import HelpProgressDocument
from app.schemas.domain.incidents import IncidentDocument
from app.schemas.domain.maintenance_runs import MaintenanceRunDocument
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
from app.schemas.domain.platform_status import (
    PlatformAnnouncementDocument,
    PlatformStatusDayDocument,
)
from app.schemas.domain.service_levels import (
    ServiceLevelHourDocument,
    ServiceLevelSlotDocument,
)


class OperationsCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of the platform's own operations (migration
    1093): the platform alerts' episodes, the recorded backups and restore
    drills, and the incident log. A sibling of DocumentCollectionsContainer
    with the same storage factory.
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    platform_alert_state_collection = document_collection(
        PlatformAlertStateDocument,
        "platform_alert_states",
        config,
        clients,
        utilities,
        time_provider,
    )
    maintenance_run_collection = document_collection(
        MaintenanceRunDocument,
        "maintenance_runs",
        config,
        clients,
        utilities,
        time_provider,
    )
    incident_collection = document_collection(
        IncidentDocument,
        "incidents",
        config,
        clients,
        utilities,
        time_provider,
    )
    client_standing_collection = document_collection(
        ClientStandingDocument,
        "client_standings",
        config,
        clients,
        utilities,
        time_provider,
    )
    # The status page and the cabinet's guidance (1111): the platform
    # team's announcements, the status history by day, and what each
    # person has seen of the coach marks and the changelog.
    platform_announcement_collection = document_collection(
        PlatformAnnouncementDocument,
        "platform_announcements",
        config,
        clients,
        utilities,
        time_provider,
    )
    platform_status_day_collection = document_collection(
        PlatformStatusDayDocument,
        "platform_status_days",
        config,
        clients,
        utilities,
        time_provider,
    )
    help_progress_collection = document_collection(
        HelpProgressDocument,
        "help_progress",
        config,
        clients,
        utilities,
        time_provider,
    )
    # The post-deploy data tasks' progress, one row per task (1164).
    data_task_state_collection = document_collection(
        DataTaskStateDocument,
        "data_task_states",
        config,
        clients,
        utilities,
        time_provider,
    )
    # The service level indicators (1163): five-minute slots per series and
    # one row per hour.
    service_level_slot_collection = document_collection(
        ServiceLevelSlotDocument,
        "service_level_slots",
        config,
        clients,
        utilities,
        time_provider,
    )
    service_level_hour_collection = document_collection(
        ServiceLevelHourDocument,
        "service_level_hours",
        config,
        clients,
        utilities,
        time_provider,
    )
