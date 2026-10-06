from typed_time_provider import Microseconds, WallClock

from app.contracts.operations import (
    CalendarConnectionRepoContract,
    GoogleCalendarClientContract,
)
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.facilitators.calendar.google_access_tokens import fresh_access_token
from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.domain.calendar import CalendarConnectionDocument
from app.schemas.dto.calendar_sync.busy_reads import (
    BusyPeriod,
    BusyWindow,
    GoogleCalendarEntry,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.bookings.strings import (
    CalendarAccessToken,
    ExternalCalendarId,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.utilities.calendar_sync.busy_periods import subtract_periods
from app.utilities.scheduling.availability import BLOCKING_BOOKING_STATUSES

NOT_CONNECTED_MESSAGE: str = "Google Calendar is not connected for this business."
REVOKED_GRANT_CODE: str = "invalid_grant"


class GoogleBusyReader:
    """
    The busy times of the Google calendar linked to a resource, read with
    the business's connection (free/busy needs the calendar read
    permission). When the linked calendar is the one bookings are mirrored
    into, the assistant's own bookings are taken out of its busy times: they
    block their places already, and a booking must not block itself when it
    moves.
    """

    def __init__(
        self,
        connection_repo: CalendarConnectionRepoContract,
        calendar_client: GoogleCalendarClientContract,
        secret_cipher: SecretCipherAdapterContract,
        booking_repo: BookingRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._connection_repo: CalendarConnectionRepoContract = connection_repo
        self._calendar_client: GoogleCalendarClientContract = calendar_client
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._booking_repo: BookingRepoContract = booking_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def read(
        self,
        business_id: BusinessId,
        calendar_id: ExternalCalendarId,
        window: BusyWindow,
        timeout: BusyTimeFetchSeconds,
    ) -> list[BusyPeriod]:
        """
        Raises:
            BusyTimeSourceError: NOT_CONNECTED, NEEDS_RECONNECT and the
                free/busy query's reasons.
        """

        connection: CalendarConnectionDocument = self._connection(business_id)
        periods: list[BusyPeriod] = self._calendar_client.query_free_busy(
            self.access_token(connection), calendar_id, window, timeout
        )
        if calendar_id != connection.calendar_id:
            return periods

        return subtract_periods(periods, self._own_bookings(business_id, window))

    def access_token(
        self, connection: CalendarConnectionDocument
    ) -> CalendarAccessToken:
        """The connection's access token; a refused refresh means reconnecting."""

        try:
            return fresh_access_token(
                connection,
                self._connection_repo,
                self._calendar_client,
                self._secret_cipher,
                self._wall_clock.now_unix(),
            )
        except BusyTimeSourceError:
            raise
        except ExternalServiceError as error:
            raise BusyTimeSourceError(
                "Google refused to renew the calendar access.",
                CalendarSyncProblem.NEEDS_RECONNECT
                if REVOKED_GRANT_CODE in str(error)
                else CalendarSyncProblem.UNREACHABLE,
            ) from error

    def list_calendars(
        self, business_id: BusinessId, timeout: BusyTimeFetchSeconds
    ) -> list[GoogleCalendarEntry]:
        """The connected account's calendars (raises as `read`)."""

        connection: CalendarConnectionDocument = self._connection(business_id)
        return self._calendar_client.list_calendars(
            self.access_token(connection), timeout
        )

    def _connection(self, business_id: BusinessId) -> CalendarConnectionDocument:
        connection: CalendarConnectionDocument | None = (
            self._connection_repo.get_by_business(business_id)
            if self._calendar_client.is_configured()
            else None
        )
        if connection is None:
            raise BusyTimeSourceError(
                NOT_CONNECTED_MESSAGE, CalendarSyncProblem.NOT_CONNECTED
            )

        return connection

    def _own_bookings(
        self, business_id: BusinessId, window: BusyWindow
    ) -> list[tuple[int, int]]:
        return [
            (int(booking.starts_at), int(booking.ends_at))
            for booking in self._booking_repo.list_ending_after(
                business_id, BookingSearchBoundSeconds(int(window.starts_at))
            )
            if booking.status in BLOCKING_BOOKING_STATUSES and not booking.is_sandbox
        ]
