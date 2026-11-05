from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.calendar_sync_collections_container import (
    CalendarSyncCollectionsContainer,
)
from app.repositories.calendar_sync_repositories import (
    CalendarBusyTimesRepository,
    IcalExportFeedRepository,
    ResourceCalendarLinkRepository,
)


class CalendarSyncRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of two-way availability (migration 1160).
    `RepositoriesContainer` extends it, so they are read as
    `repositories.calendar_busy_times_repo` like every other repository.
    """

    calendar_sync_collections: CalendarSyncCollectionsContainer = (
        DependenciesContainer()  # type: ignore[assignment]
    )

    resource_calendar_link_repo: Singleton[ResourceCalendarLinkRepository] = Singleton(
        ResourceCalendarLinkRepository,
        collection=calendar_sync_collections.resource_calendar_link_collection,
    )
    calendar_busy_times_repo: Singleton[CalendarBusyTimesRepository] = Singleton(
        CalendarBusyTimesRepository,
        collection=calendar_sync_collections.calendar_busy_times_collection,
    )
    ical_export_feed_repo: Singleton[IcalExportFeedRepository] = Singleton(
        IcalExportFeedRepository,
        collection=calendar_sync_collections.ical_export_feed_collection,
    )
