"""
Seams of two-way availability: the calendar settings of resources, their
cached busy times and export feeds, the booking-system connectors, and the
facilitator that reads every source.
"""

from collections.abc import Callable, Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.adapter_contract import AdapterContract
from app.contracts.facilitator_contract import FacilitatorContract
from app.contracts.registry_contract import RegistryContract
from app.contracts.repo_contract import RepoContract
from app.schemas.constants.calendar_sync import BookingSystemKind
from app.schemas.domain.calendar_sync import (
    CalendarBusyTimesDocument,
    IcalExportFeedDocument,
    ResourceCalendarLinkDocument,
)
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.calendar_sync.busy_reads import (
    BookingSystemBookingCreated,
    BookingSystemBookingDraft,
    BookingSystemCredentials,
    BookingSystemRead,
    BookingSystemResource,
    BusyPeriod,
    GoogleCalendarList,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.schemas.typings.calendar_sync.constrained_strings import (
    CalendarFeedUrl,
    IcalExportTokenHash,
)
from app.schemas.typings.calendar_sync.strings import BookingSystemBookingId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit

type CalendarLinkChange = Callable[
    [ResourceCalendarLinkDocument], ResourceCalendarLinkDocument | None
]


class ResourceCalendarLinkRepoContract(RepoContract, Protocol):
    """One calendar settings document per resource."""

    def get(
        self, business_id: BusinessId, resource_id: ResourceId
    ) -> ResourceCalendarLinkDocument | None:
        raise NotImplementedError

    def add(self, link: ResourceCalendarLinkDocument) -> None:
        """Store a new document; one already stored for the resource stays."""
        raise NotImplementedError

    def update(
        self,
        business_id: BusinessId,
        resource_id: ResourceId,
        change: CalendarLinkChange,
    ) -> ResourceCalendarLinkDocument | None:
        """What `change` makes of the stored document, written in one step."""
        raise NotImplementedError

    def list_by_business(
        self, business_id: BusinessId
    ) -> list[ResourceCalendarLinkDocument]:
        """Every resource of the business that has calendar settings."""
        raise NotImplementedError

    def list_due(
        self, now: Microseconds, limit: DocumentQueryLimit
    ) -> list[ResourceCalendarLinkDocument]:
        """Across businesses: the ones whose sources are due to sync, oldest first."""
        raise NotImplementedError


class CalendarBusyTimesRepoContract(RepoContract, Protocol):
    """The cached busy times of each source of each resource."""

    def list_by_business(
        self, business_id: BusinessId
    ) -> list[CalendarBusyTimesDocument]:
        raise NotImplementedError

    def store_if_newer(self, busy_times: CalendarBusyTimesDocument) -> bool:
        """
        Store the read unless a newer read of the same source is stored
        already (concurrent syncs: the latest read wins). True when stored.
        """
        raise NotImplementedError

    def delete(self, business_id: BusinessId, busy_times_ids: Sequence[str]) -> None:
        """Forget the busy times of sources that were unlinked."""
        raise NotImplementedError


class IcalExportFeedRepoContract(RepoContract, Protocol):
    """Export addresses, stored by the hash of their token."""

    def add(self, feed: IcalExportFeedDocument) -> None:
        raise NotImplementedError

    def find(self, token_hash: IcalExportTokenHash) -> IcalExportFeedDocument | None:
        """Across businesses: the feed of an address (platform-wide read)."""
        raise NotImplementedError

    def remove(self, business_id: BusinessId, token_hash: IcalExportTokenHash) -> None:
        raise NotImplementedError

    def mark_read(
        self, business_id: BusinessId, token_hash: IcalExportTokenHash, at: Microseconds
    ) -> None:
        """Remember when a calendar last fetched the feed."""
        raise NotImplementedError


class BookingSystemConnectorContract(AdapterContract, Protocol):
    """
    One outside booking system (Cal.com, and the market-specific ones that
    follow). Every call takes the business's key and a time limit; it
    raises BusyTimeSourceError with the reason (ACCESS_DENIED for a
    refused key, NOT_FOUND, TIMEOUT, UNREACHABLE, PROVIDER_ERROR).
    """

    kind: BookingSystemKind

    def describe(
        self, credentials: BookingSystemCredentials, timeout: BusyTimeFetchSeconds
    ) -> BookingSystemResource:
        """Check the key and the resource; its title as the system shows it."""
        raise NotImplementedError

    def list_busy(self, read: BookingSystemRead) -> list[BusyPeriod]:
        """
        The resource's active bookings in the window, as busy periods; the
        bookings the platform wrote there are left out (the platform's own
        booking already takes its place).
        """
        raise NotImplementedError

    def create_booking(
        self,
        credentials: BookingSystemCredentials,
        draft: BookingSystemBookingDraft,
        timeout: BusyTimeFetchSeconds,
    ) -> BookingSystemBookingCreated:
        """Write a booking the platform took, so the time is taken there too."""
        raise NotImplementedError

    def find_booking(
        self,
        credentials: BookingSystemCredentials,
        draft: BookingSystemBookingDraft,
        timeout: BusyTimeFetchSeconds,
    ) -> BookingSystemBookingId | None:
        """
        The active booking the platform wrote there for the draft's platform
        booking at the draft's time, if there is one (a write repeated after
        it succeeded but before its id was kept finds it instead of writing
        a second one).
        """
        raise NotImplementedError

    def cancel_booking(
        self,
        credentials: BookingSystemCredentials,
        booking_id: BookingSystemBookingId,
        timeout: BusyTimeFetchSeconds,
    ) -> None:
        """Cancel a booking the platform wrote; one already gone is no error."""
        raise NotImplementedError


class BookingSystemConnectorRegistryContract(RegistryContract, Protocol):
    """The connector of each booking system the platform speaks to."""

    def connector_for(self, kind: BookingSystemKind) -> BookingSystemConnectorContract:
        raise NotImplementedError

    def kinds(self) -> list[BookingSystemKind]:
        raise NotImplementedError


class BusyTimeSyncFacilitatorContract(FacilitatorContract, Protocol):
    """Reads a resource's outside calendars into its cached busy times."""

    def sync_resource(
        self, resource: ResourceDocument, timeout: BusyTimeFetchSeconds
    ) -> ResourceCalendarLinkDocument | None:
        """
        Read every source linked to the resource (each within `timeout`),
        store what each made busy, record how each went and when the
        resource is due next. Never raises for a source's failure (its
        status says why; the busy times read before stay). None when the
        resource has no calendar settings.
        """
        raise NotImplementedError

    def refresh_stale(
        self, business_id: BusinessId, timeout: BusyTimeFetchSeconds
    ) -> None:
        """
        Before availability is shown: read again, within `timeout` in all,
        the business's resources whose busy times are older than two sync
        periods (the sync job fell behind). Never raises.
        """
        raise NotImplementedError

    def list_google_calendars(
        self, business_id: BusinessId, timeout: BusyTimeFetchSeconds
    ) -> GoogleCalendarList:
        """
        The connected Google account's calendars a resource can be linked
        to; unreadable (with the reason) when Google Calendar is not
        connected or its consent lacks the read permission.
        """
        raise NotImplementedError

    def describe_booking_system(
        self,
        kind: BookingSystemKind,
        credentials: BookingSystemCredentials,
        timeout: BusyTimeFetchSeconds,
    ) -> BookingSystemResource:
        """
        Check a key and a resource with the booking system before they are
        saved.

        Raises:
            BusyTimeSourceError: the key was refused, the resource is not
                there, or the system did not answer.
        """
        raise NotImplementedError

    def vet_feed_address(self, url: CalendarFeedUrl) -> None:
        """
        Refuse an iCal feed address the platform must never read (not public
        http(s) on ports 80 and 443, credentials in it, an intranet host).

        Raises:
            ValidationFailedError: with the reason `address_refused`.
        """
        raise NotImplementedError
