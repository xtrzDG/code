from typed_time_provider import Microseconds, WallClock

from app.contracts.calendar_sync import (
    CalendarBusyTimesRepoContract,
    IcalExportFeedRepoContract,
)
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import ResourceRepoContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.calendar_sync import IcalExportFeedDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.calendar_sync.ical_export import IcalExportFile, IcalExportRequest
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.use_cases.calendar_sync.export_events import exported_busy_times
from app.use_cases.calendar_sync.export_rate_limits import (
    refuse_too_frequent_feed_reads,
)
from app.utilities.calendar_sync.calendar_sync_keys import hash_export_token
from app.utilities.calendar_sync.ical_export_feed import (
    BUSY_EVENT_TITLE,
    render_busy_feed,
)
from app.utilities.scheduling.zoned_time import load_time_zone

UNKNOWN_FEED_MESSAGE: str = "This calendar address is not valid (any more)."
MICROSECONDS_PER_SECOND: int = 1_000_000
# A booking that began yesterday may still run.
LOOK_BACK_SECONDS: int = 24 * 60 * 60
# When a calendar last read the feed is written at most this often.
READ_STAMP_SECONDS: int = 10 * 60


class ExportResourceBusyTimesUseCase(
    UseCaseContract[IcalExportRequest, IcalExportFile]
):
    """
    A calendar (Airbnb, Booking.com, Google) fetches a resource's export
    feed: its bookings and outside busy times from now on, with no guest's
    details. The address names only a random token, so its feed is found
    across businesses by the token's hash; everything else is read in its
    business's scope. Fetches are limited per network and for the platform;
    an unknown token is not found.
    """

    def __init__(
        self,
        export_feed_repo: IcalExportFeedRepoContract,
        business_repo: BusinessRepoContract,
        resource_repo: ResourceRepoContract,
        booking_repo: BookingRepoContract,
        busy_times_repo: CalendarBusyTimesRepoContract,
        text_resolver: LocalizedTextResolverContract,
        rate_limits: RequestRateLimitRegistryContract,
        storage_scope: StorageScopeContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._export_feed_repo: IcalExportFeedRepoContract = export_feed_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._busy_times_repo: CalendarBusyTimesRepoContract = busy_times_repo
        self._text_resolver: LocalizedTextResolverContract = text_resolver
        self._rate_limits: RequestRateLimitRegistryContract = rate_limits
        self._storage_scope: StorageScopeContract = storage_scope
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: IcalExportRequest) -> IcalExportFile:
        now: Microseconds = self._wall_clock.now_unix()
        refuse_too_frequent_feed_reads(
            self._rate_limits, input_data.client_ip_address, now
        )
        with self._storage_scope.platform_wide():
            feed: IcalExportFeedDocument | None = self._export_feed_repo.find(
                hash_export_token(input_data.token)
            )
        if feed is None:
            raise NotFoundError(UNKNOWN_FEED_MESSAGE)

        with self._storage_scope.scoped_to_business(feed.business_id):
            return self._render(feed, now)

    def _render(
        self, feed: IcalExportFeedDocument, now: Microseconds
    ) -> IcalExportFile:
        business: BusinessDocument | None = self._business_repo.get(feed.business_id)
        resource: ResourceDocument | None = self._resource_repo.get(
            feed.business_id, feed.resource_id
        )
        if business is None or resource is None:
            raise NotFoundError(UNKNOWN_FEED_MESSAGE)

        now_seconds: int = int(now) // MICROSECONDS_PER_SECOND
        bookings = self._booking_repo.list_ending_after(
            business.id,
            BookingSearchBoundSeconds(max(now_seconds - LOOK_BACK_SECONDS, 0)),
        )
        busy_times = self._busy_times_repo.list_by_business(business.id)
        if feed.last_read_at is None or int(feed.last_read_at) < int(now) - (
            READ_STAMP_SECONDS * MICROSECONDS_PER_SECOND
        ):
            self._export_feed_repo.mark_read(business.id, feed.token_hash, now)

        return IcalExportFile(
            content=render_busy_feed(
                f"{resource.name} · {business.name}",
                str(
                    self._text_resolver.resolve(
                        BUSY_EVENT_TITLE, business.owner_language
                    )
                ),
                exported_busy_times(
                    resource,
                    bookings,
                    busy_times,
                    load_time_zone(business.timezone),
                    now_seconds - LOOK_BACK_SECONDS,
                ),
                now_seconds,
            )
        )
