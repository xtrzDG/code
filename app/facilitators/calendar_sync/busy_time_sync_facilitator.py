import logging
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.calendar_sync import (
    BusyTimeSyncFacilitatorContract,
    CalendarBusyTimesRepoContract,
    ResourceCalendarLinkRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.knowledge_repositories import ResourceRepoContract
from app.facilitators.calendar_sync.booking_system_busy_reader import (
    BookingSystemBusyReader,
)
from app.facilitators.calendar_sync.busy_time_reads import (
    BusyRead,
    BusyTimeReads,
    busy_times_document,
)
from app.facilitators.calendar_sync.google_busy_reader import GoogleBusyReader
from app.facilitators.calendar_sync.ical_busy_reader import IcalBusyReader
from app.facilitators.calendar_sync.sync_outcomes import (
    SourceOutcome,
    failed,
    is_still_linked,
    previous_status,
    record_outcomes,
    succeeded,
)
from app.schemas.constants.calendar_sync import (
    BookingSystemKind,
    BusyTimeSource,
    CalendarSyncProblem,
)
from app.schemas.domain.calendar_sync import ResourceCalendarLinkDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.calendar_sync.busy_reads import (
    BookingSystemCredentials,
    BookingSystemResource,
    BusyPeriod,
    BusyWindow,
    GoogleCalendarList,
)
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.schemas.typings.calendar_sync.constrained_strings import CalendarFeedUrl
from app.schemas.typings.calendar_sync.prefixed_id import IcalImportFeedId
from app.utilities.calendar_sync.busy_windows import (
    STALE_AFTER_SECONDS,
    busy_window,
)
from app.utilities.calendar_sync.calendar_sync_keys import busy_times_id_of

LOGGER: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_SECOND: int = 1_000_000
UNEXPECTED_MESSAGE: str = "Unexpected error while reading busy times."
# A source is not read with less time than this left of the budget.
MIN_READ_SECONDS: float = 0.2


class BusyTimeSyncFacilitator(BusyTimeSyncFacilitatorContract):
    """
    Reads every source linked to a resource (its Google calendar, each
    imported iCal feed, its booking system), each within the time given,
    and keeps what each made busy (`calendar_busy_times`, the latest read
    wins). A source that fails keeps the busy times read before and records
    the reason; one unlinked during the read is forgotten again. The next
    read is due one sync period later.
    """

    def __init__(
        self,
        link_repo: ResourceCalendarLinkRepoContract,
        busy_times_repo: CalendarBusyTimesRepoContract,
        resource_repo: ResourceRepoContract,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        google: GoogleBusyReader,
        ical: IcalBusyReader,
        booking_systems: BookingSystemBusyReader,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._link_repo: ResourceCalendarLinkRepoContract = link_repo
        self._busy_times_repo: CalendarBusyTimesRepoContract = busy_times_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._reads: BusyTimeReads = BusyTimeReads(
            business_repo, business_profile_repo, google, ical, booking_systems
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def sync_resource(
        self, resource: ResourceDocument, timeout: BusyTimeFetchSeconds
    ) -> ResourceCalendarLinkDocument | None:
        link: ResourceCalendarLinkDocument | None = self._link_repo.get(
            resource.business_id, resource.id
        )
        if link is None:
            return None

        now: Microseconds = self._wall_clock.now_unix()
        zone: ZoneInfo = self._reads.zone_of(resource.business_id)
        outcomes: list[SourceOutcome] = [
            self._read(resource, link, source, feed_id, read, now)
            for source, feed_id, read in self._reads.reads_of(
                resource, link, zone, timeout
            )
        ]
        updated: ResourceCalendarLinkDocument | None = self._link_repo.update(
            resource.business_id,
            resource.id,
            lambda stored: record_outcomes(stored, outcomes, now),
        )
        if updated is not None:
            self._forget_unlinked(updated, outcomes)

        return updated

    def refresh_stale(
        self, business_id: BusinessId, timeout: BusyTimeFetchSeconds
    ) -> None:
        try:
            self._refresh_stale(business_id, float(timeout))
        except Exception:  # noqa: BLE001 - availability is shown with what is cached
            LOGGER.exception("Refreshing stale busy times of %s failed.", business_id)

    def list_google_calendars(
        self, business_id: BusinessId, timeout: BusyTimeFetchSeconds
    ) -> GoogleCalendarList:
        try:
            return GoogleCalendarList(
                is_readable=True,
                items=self._reads.google.list_calendars(business_id, timeout),
            )
        except BusyTimeSourceError as error:
            return GoogleCalendarList(
                is_readable=False, problem=error.problem, items=[]
            )

    def describe_booking_system(
        self,
        kind: BookingSystemKind,
        credentials: BookingSystemCredentials,
        timeout: BusyTimeFetchSeconds,
    ) -> BookingSystemResource:
        return self._reads.booking_systems.describe(kind, credentials, timeout)

    def vet_feed_address(self, url: CalendarFeedUrl) -> None:
        self._reads.ical.vet(url)

    def _read(
        self,
        resource: ResourceDocument,
        link: ResourceCalendarLinkDocument,
        source: BusyTimeSource,
        feed_id: IcalImportFeedId | None,
        read: BusyRead,
        now: Microseconds,
    ) -> SourceOutcome:
        window: BusyWindow = busy_window(int(now) // MICROSECONDS_PER_SECOND, source)
        previous = previous_status(link, source, feed_id)
        try:
            periods: list[BusyPeriod] = read(window)
        except BusyTimeSourceError as error:
            LOGGER.info(
                "Busy times of %s (%s) not read: %s", resource.id, source, error
            )
            return SourceOutcome(
                source, feed_id, failed(previous, now, error.problem, str(error))
            )
        except Exception:  # noqa: BLE001 - one source never stops the others
            LOGGER.exception("Busy times of %s (%s) raised.", resource.id, source)
            return SourceOutcome(
                source,
                feed_id,
                failed(
                    previous,
                    now,
                    CalendarSyncProblem.PROVIDER_ERROR,
                    UNEXPECTED_MESSAGE,
                ),
            )

        self._busy_times_repo.store_if_newer(
            busy_times_document(resource, source, feed_id, periods, window, now)
        )
        return SourceOutcome(source, feed_id, succeeded(now, len(periods)))

    def _forget_unlinked(
        self, link: ResourceCalendarLinkDocument, outcomes: list[SourceOutcome]
    ) -> None:
        """Busy times written for a source that was unlinked during the read."""

        stale_ids: list[str] = [
            str(busy_times_id_of(link.resource_id, outcome.source, outcome.feed_id))
            for outcome in outcomes
            if not is_still_linked(link, outcome)
        ]
        if stale_ids:
            self._busy_times_repo.delete(link.business_id, stale_ids)

    def _refresh_stale(self, business_id: BusinessId, budget: float) -> None:
        started: int = int(self._wall_clock.now_unix())
        stale_before: int = started - STALE_AFTER_SECONDS * MICROSECONDS_PER_SECOND
        for link in self._link_repo.list_by_business(business_id):
            if link.next_sync_at is None or int(link.next_sync_at) > stale_before:
                continue

            spent: float = (
                int(self._wall_clock.now_unix()) - started
            ) / MICROSECONDS_PER_SECOND
            remaining: float = budget - spent
            resource: ResourceDocument | None = self._resource_repo.get(
                business_id, link.resource_id
            )
            if remaining < MIN_READ_SECONDS:
                return
            if resource is not None:
                self.sync_resource(resource, BusyTimeFetchSeconds(remaining))
