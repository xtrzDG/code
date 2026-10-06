"""Cal.com as a booking-system connector: event types as resources."""

from app.clients.cal_com.cal_com_client import CalComClient, iso_instant
from app.clients.cal_com.cal_com_responses import (
    is_busy_booking,
    read_instant,
    read_text,
)
from app.contracts.calendar_sync import BookingSystemConnectorContract
from app.schemas.constants.calendar_sync import BookingSystemKind, CalendarSyncProblem
from app.schemas.dto.calendar_sync.busy_reads import (
    BookingSystemBookingCreated,
    BookingSystemBookingDraft,
    BookingSystemCredentials,
    BookingSystemRead,
    BookingSystemResource,
    BusyPeriod,
)
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.schemas.typings.calendar_sync.strings import (
    BookingSystemBookingId,
    BookingSystemResourceTitle,
)
from app.utilities.calendar_sync.busy_periods import (
    clip_to_window,
    merge_busy_periods,
    new_period,
)

MAX_TITLE_LENGTH: int = 120
SECONDS_PER_MINUTE: int = 60


class CalComBookingSystemAdapter(BookingSystemConnectorContract):
    """
    Cal.com (API v2): a resource is an event type (its id); its accepted
    and pending bookings make the resource busy; a booking the platform
    takes is written there with the guest's name, e-mail when known, zone
    and language, so the time is taken on the business's Cal.com page too.
    """

    kind: BookingSystemKind = BookingSystemKind.CAL_COM

    def __init__(self, client: CalComClient) -> None:
        self._client: CalComClient = client

    def describe(
        self, credentials: BookingSystemCredentials, timeout: BusyTimeFetchSeconds
    ) -> BookingSystemResource:
        fields: dict[str, object] = self._client.get_event_type(
            credentials.api_key, credentials.external_resource_id, timeout
        )
        title: str | None = read_text(fields, "title")
        return BookingSystemResource(
            external_resource_id=credentials.external_resource_id,
            title=(
                None
                if title is None
                else BookingSystemResourceTitle(title[:MAX_TITLE_LENGTH])
            ),
        )

    def list_busy(self, read: BookingSystemRead) -> list[BusyPeriod]:
        periods: list[BusyPeriod] = []
        for fields in self._client.list_bookings(
            read.credentials.api_key,
            read.credentials.external_resource_id,
            read.window,
            read.timeout,
        ):
            start: int | None = read_instant(fields, "start")
            end: int | None = read_instant(fields, "end")
            if not is_busy_booking(fields) or start is None or end is None:
                continue

            period: BusyPeriod | None = new_period(start, end)
            clipped: BusyPeriod | None = (
                None if period is None else clip_to_window(period, read.window)
            )
            if clipped is not None:
                periods.append(clipped)

        return merge_busy_periods(periods)

    def create_booking(
        self,
        credentials: BookingSystemCredentials,
        draft: BookingSystemBookingDraft,
        timeout: BusyTimeFetchSeconds,
    ) -> BookingSystemBookingCreated:
        attendee: dict[str, object] = {
            "name": str(draft.guest_name),
            "timeZone": str(draft.time_zone),
            "language": str(draft.language).split("-")[0],
        }
        if draft.guest_email is not None:
            attendee["email"] = str(draft.guest_email)
        fields: dict[str, object] = self._client.create_booking(
            credentials.api_key,
            {
                "start": iso_instant(int(draft.starts_at)),
                "eventTypeId": event_type_number(credentials),
                "lengthInMinutes": (int(draft.ends_at) - int(draft.starts_at))
                // SECONDS_PER_MINUTE,
                "attendee": attendee,
                "metadata": {"source": "assistant-workshop"},
            },
            timeout,
        )
        uid: str | None = read_text(fields, "uid")
        if uid is None:
            raise BusyTimeSourceError(
                "Cal.com created a booking without its uid.",
                CalendarSyncProblem.PROVIDER_ERROR,
            )

        return BookingSystemBookingCreated(booking_id=BookingSystemBookingId(uid))

    def cancel_booking(
        self,
        credentials: BookingSystemCredentials,
        booking_id: BookingSystemBookingId,
        timeout: BusyTimeFetchSeconds,
    ) -> None:
        try:
            self._client.cancel_booking(credentials.api_key, booking_id, timeout)
        except BusyTimeSourceError as error:
            if error.problem is not CalendarSyncProblem.NOT_FOUND:
                raise


def event_type_number(credentials: BookingSystemCredentials) -> int | str:
    """Cal.com wants the event type id as a number when it is one."""

    text: str = str(credentials.external_resource_id)
    return int(text) if text.isdigit() else text
