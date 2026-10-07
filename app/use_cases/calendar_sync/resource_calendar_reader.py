"""Loading a resource and its calendars as the cabinet shows them."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.calendar_sync import (
    BookingSystemConnectorRegistryContract,
    CalendarBusyTimesRepoContract,
    IcalExportFeedRepoContract,
    ResourceCalendarLinkRepoContract,
)
from app.contracts.operations import (
    CalendarConnectionRepoContract,
    GoogleCalendarClientContract,
)
from app.contracts.repositories.knowledge_repositories import ResourceRepoContract
from app.schemas.domain.calendar_sync import (
    IcalExportFeedDocument,
    ResourceCalendarLinkDocument,
)
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.calendar_sync.resource_calendar import ResourceCalendarView
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.calendar_sync.calendar_views import (
    CalendarViewParts,
    build_calendar_view,
)


class ResourceCalendarReader:
    """The resource of a request (or NotFoundError) and its calendars' view."""

    def __init__(
        self,
        resource_repo: ResourceRepoContract,
        link_repo: ResourceCalendarLinkRepoContract,
        busy_times_repo: CalendarBusyTimesRepoContract,
        export_feed_repo: IcalExportFeedRepoContract,
        connection_repo: CalendarConnectionRepoContract,
        calendar_client: GoogleCalendarClientContract,
        connectors: BookingSystemConnectorRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self.resource_repo: ResourceRepoContract = resource_repo
        self.link_repo: ResourceCalendarLinkRepoContract = link_repo
        self.busy_times_repo: CalendarBusyTimesRepoContract = busy_times_repo
        self.export_feed_repo: IcalExportFeedRepoContract = export_feed_repo
        self._connection_repo: CalendarConnectionRepoContract = connection_repo
        self._calendar_client: GoogleCalendarClientContract = calendar_client
        self._connectors: BookingSystemConnectorRegistryContract = connectors
        self.wall_clock: WallClock[Microseconds] = wall_clock

    def resource(
        self, business_id: BusinessId, resource_id: ResourceId
    ) -> ResourceDocument:
        resource: ResourceDocument | None = self.resource_repo.get(
            business_id, resource_id
        )
        if resource is None:
            raise NotFoundError(f"Resource {resource_id} was not found.")

        return resource

    def view(
        self, business_id: BusinessId, resource_id: ResourceId
    ) -> ResourceCalendarView:
        return self.view_of(self.resource(business_id, resource_id))

    def view_of(self, resource: ResourceDocument) -> ResourceCalendarView:
        link: ResourceCalendarLinkDocument | None = self.link_repo.get(
            resource.business_id, resource.id
        )
        export_feed: IcalExportFeedDocument | None = (
            None
            if link is None or link.ical_export_token_hash is None
            else self.export_feed_repo.find(link.ical_export_token_hash)
        )
        return build_calendar_view(
            resource,
            link,
            CalendarViewParts(
                is_google_available=self._calendar_client.is_configured(),
                is_google_connected=self._connection_repo.get_by_business(
                    resource.business_id
                )
                is not None,
                booking_system_kinds=self._connectors.kinds(),
                busy_times=self.busy_times_repo.list_by_business(resource.business_id),
                export_feed=export_feed,
                now=self.wall_clock.now_unix(),
            ),
        )
