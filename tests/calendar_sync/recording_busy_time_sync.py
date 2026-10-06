"""A busy-time sync facilitator that only records what availability asked."""

from app.contracts.calendar_sync import BusyTimeSyncFacilitatorContract
from app.schemas.constants.calendar_sync import BookingSystemKind
from app.schemas.domain.calendar_sync import ResourceCalendarLinkDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.calendar_sync.busy_reads import (
    BookingSystemCredentials,
    BookingSystemResource,
    GoogleCalendarList,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.schemas.typings.calendar_sync.constrained_strings import CalendarFeedUrl


class RecordingBusyTimeSync(BusyTimeSyncFacilitatorContract):
    """Records stale refreshes (business, time limit); reads nothing."""

    def __init__(self) -> None:
        self.stale_refreshes: list[tuple[BusinessId, float]] = []
        self.synced: list[ResourceDocument] = []

    def sync_resource(
        self, resource: ResourceDocument, timeout: BusyTimeFetchSeconds
    ) -> ResourceCalendarLinkDocument | None:
        self.synced.append(resource)
        return None

    def refresh_stale(
        self, business_id: BusinessId, timeout: BusyTimeFetchSeconds
    ) -> None:
        self.stale_refreshes.append((business_id, float(timeout)))

    def list_google_calendars(
        self, business_id: BusinessId, timeout: BusyTimeFetchSeconds
    ) -> GoogleCalendarList:
        return GoogleCalendarList(is_readable=True, items=[])

    def describe_booking_system(
        self,
        kind: BookingSystemKind,
        credentials: BookingSystemCredentials,
        timeout: BusyTimeFetchSeconds,
    ) -> BookingSystemResource:
        return BookingSystemResource(
            external_resource_id=credentials.external_resource_id
        )

    def vet_feed_address(self, url: CalendarFeedUrl) -> None:
        del url
