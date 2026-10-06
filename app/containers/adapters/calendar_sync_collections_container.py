from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.calendar_sync import (
    CalendarBusyTimesDocument,
    IcalExportFeedDocument,
    ResourceCalendarLinkDocument,
)


class CalendarSyncCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of two-way availability (migration 1160): the
    calendar settings of resources, their cached busy times and their iCal
    export feeds. A sibling of DocumentCollectionsContainer with the same
    storage factory (Postgres with DATABASE_URL, else in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    resource_calendar_link_collection = document_collection(
        ResourceCalendarLinkDocument,
        "resource_calendar_links",
        config,
        clients,
        utilities,
        time_provider,
    )
    calendar_busy_times_collection = document_collection(
        CalendarBusyTimesDocument,
        "calendar_busy_times",
        config,
        clients,
        utilities,
        time_provider,
    )
    ical_export_feed_collection = document_collection(
        IcalExportFeedDocument,
        "ical_export_feeds",
        config,
        clients,
        utilities,
        time_provider,
    )
