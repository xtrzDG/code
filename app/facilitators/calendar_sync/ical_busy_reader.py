from zoneinfo import ZoneInfo

from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.web_fetching import SafeHttpFetcherContract
from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.constants.web_fetching import (
    REFUSED_FETCH_PROBLEMS,
    UNUSABLE_FETCH_PROBLEMS,
    WebFetchProblem,
)
from app.schemas.domain.calendar_sync import IcalImportFeed
from app.schemas.dto.calendar_sync.busy_reads import BusyPeriod, BusyWindow
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.web_fetching import FetchedWebResource, WebFetchRequest
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.exceptions.web_fetch_errors import WebFetchError
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.schemas.typings.calendar_sync.constrained_strings import CalendarFeedUrl
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.schemas.typings.web_fetching.constrained_floats import WebFetchTimeoutSeconds
from app.utilities.calendar_sync.busy_windows import MAX_BUSY_PERIODS, DayBounds
from app.utilities.calendar_sync.feed_addresses import (
    ICAL_FEED_BYTE_LIMIT,
    ICAL_MEDIA_TYPES,
    fetchable_feed_url,
)
from app.utilities.calendar_sync.ical_busy_times import read_feed_busy_periods

ADDRESS_REFUSED_MESSAGE: str = (
    "This address cannot be imported: use the public https link of the calendar."
)
ACCESS_DENIED_STATUSES: frozenset[str] = frozenset({"401", "403"})
GONE_STATUSES: frozenset[str] = frozenset({"404", "410"})


class IcalBusyReader:
    """
    The busy times of an imported iCal feed, read through the safe fetcher
    (public addresses only, no redirect into the intranet, size and time
    limits). The address is decrypted only for the fetch.
    """

    def __init__(
        self,
        fetcher: SafeHttpFetcherContract,
        secret_cipher: SecretCipherAdapterContract,
    ) -> None:
        self._fetcher: SafeHttpFetcherContract = fetcher
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher

    def read(
        self,
        feed: IcalImportFeed,
        window: BusyWindow,
        zone: ZoneInfo,
        day_bounds: DayBounds,
        timeout: BusyTimeFetchSeconds,
    ) -> list[BusyPeriod]:
        """
        Raises:
            BusyTimeSourceError: why the feed was not read.
        """

        try:
            fetched: FetchedWebResource = self._fetcher.fetch(
                WebFetchRequest(
                    url=fetchable_feed_url(
                        str(self._secret_cipher.decrypt(feed.encrypted_url))
                    ),
                    accepted_media_types=ICAL_MEDIA_TYPES,
                    max_bytes=ICAL_FEED_BYTE_LIMIT,
                    timeout_seconds=WebFetchTimeoutSeconds(float(timeout)),
                )
            )
        except WebFetchError as error:
            raise BusyTimeSourceError(
                f"The feed at {feed.host} was not read: {error.detail}.",
                problem_of(error),
            ) from error

        return read_feed_busy_periods(
            fetched.body, window, zone, day_bounds, MAX_BUSY_PERIODS
        )

    def vet(self, url: CalendarFeedUrl) -> None:
        """
        Raises:
            ValidationFailedError: the address must never be read
                (`address_refused`).
        """

        try:
            self._fetcher.vet(fetchable_feed_url(str(url)))
        except (WebFetchError, ValueError) as error:
            raise ValidationFailedError(
                ADDRESS_REFUSED_MESSAGE,
                reasons=[
                    ErrorReason(
                        code=ErrorReasonCode(CalendarSyncProblem.ADDRESS_REFUSED.value),
                        message=ErrorReasonMessage(ADDRESS_REFUSED_MESSAGE),
                    )
                ],
            ) from error


def problem_of(error: WebFetchError) -> CalendarSyncProblem:
    """The owner-facing reason of a fetch that failed."""

    if error.problem in REFUSED_FETCH_PROBLEMS:
        return CalendarSyncProblem.ADDRESS_REFUSED
    if error.problem in UNUSABLE_FETCH_PROBLEMS:
        return CalendarSyncProblem.NOT_A_CALENDAR
    if error.problem is WebFetchProblem.TIMEOUT:
        return CalendarSyncProblem.TIMEOUT
    if error.problem is WebFetchProblem.HTTP_STATUS:
        status: str = str(error.detail).rpartition(":")[2]
        if status in ACCESS_DENIED_STATUSES:
            return CalendarSyncProblem.ACCESS_DENIED
        if status in GONE_STATUSES:
            return CalendarSyncProblem.NOT_FOUND
        return CalendarSyncProblem.PROVIDER_ERROR
    return CalendarSyncProblem.UNREACHABLE
