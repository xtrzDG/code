"""Cal.com API v2 over httpx: event types and bookings of one account."""

from datetime import UTC, datetime
from urllib.parse import quote

import httpx

from app.clients.cal_com.cal_com_responses import read_data, read_list, read_object
from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.dto.calendar_sync.busy_reads import BusyWindow
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.schemas.typings.calendar_sync.constrained_strings import (
    BookingSystemResourceId,
    CalComApiBaseUrl,
)
from app.schemas.typings.calendar_sync.strings import (
    BookingSystemApiKey,
    BookingSystemBookingId,
)

# Cal.com versions each endpoint family by a header.
BOOKINGS_API_VERSION: str = "2024-08-13"
EVENT_TYPES_API_VERSION: str = "2024-06-14"
PAGE_SIZE: int = 100
# At most this many pages of bookings per read (10,000 bookings).
MAX_PAGES: int = 100


class CalComClient:
    """
    The few calls the Cal.com connector needs: an event type, the bookings
    of an event type in a window (paged), a new booking and its
    cancellation. Every call has its own time limit; failures raise
    BusyTimeSourceError (the key never appears in a message).
    """

    def __init__(
        self,
        base_url: CalComApiBaseUrl,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url: str = str(base_url)
        self._http_client: httpx.Client = httpx.Client(transport=transport)

    def get_event_type(
        self,
        api_key: BookingSystemApiKey,
        event_type_id: BookingSystemResourceId,
        timeout: BusyTimeFetchSeconds,
    ) -> dict[str, object]:
        response: httpx.Response = self._send(
            "GET",
            f"/event-types/{quote(str(event_type_id), safe='')}",
            api_key,
            EVENT_TYPES_API_VERSION,
            timeout,
        )
        return read_object(read_data(response, "event type"))

    def list_bookings(
        self,
        api_key: BookingSystemApiKey,
        event_type_id: BookingSystemResourceId,
        window: BusyWindow,
        timeout: BusyTimeFetchSeconds,
    ) -> list[dict[str, object]]:
        """Every booking of the event type that overlaps the window."""

        bookings: list[dict[str, object]] = []
        for page in range(MAX_PAGES):
            response: httpx.Response = self._send(
                "GET",
                "/bookings",
                api_key,
                BOOKINGS_API_VERSION,
                timeout,
                params={
                    "eventTypeId": str(event_type_id),
                    "afterStart": iso_instant(int(window.starts_at)),
                    "beforeEnd": iso_instant(int(window.ends_at)),
                    "take": str(PAGE_SIZE),
                    "skip": str(page * PAGE_SIZE),
                },
            )
            items: list[object] = read_list(read_data(response, "bookings"))
            bookings.extend(read_object(item) for item in items)
            if len(items) < PAGE_SIZE:
                break

        return bookings

    def create_booking(
        self,
        api_key: BookingSystemApiKey,
        body: dict[str, object],
        timeout: BusyTimeFetchSeconds,
    ) -> dict[str, object]:
        response: httpx.Response = self._send(
            "POST", "/bookings", api_key, BOOKINGS_API_VERSION, timeout, json=body
        )
        return read_object(read_data(response, "booking"))

    def cancel_booking(
        self,
        api_key: BookingSystemApiKey,
        booking_id: BookingSystemBookingId,
        timeout: BusyTimeFetchSeconds,
    ) -> None:
        response: httpx.Response = self._send(
            "POST",
            f"/bookings/{quote(str(booking_id), safe='')}/cancel",
            api_key,
            BOOKINGS_API_VERSION,
            timeout,
            json={"cancellationReason": "Cancelled in Assistant Workshop"},
        )
        read_data(response, "booking cancellation")

    def _send(
        self,
        method: str,
        path: str,
        api_key: BookingSystemApiKey,
        api_version: str,
        timeout: BusyTimeFetchSeconds,
        params: dict[str, str] | None = None,
        json: dict[str, object] | None = None,
    ) -> httpx.Response:
        try:
            return self._http_client.request(
                method,
                f"{self._base_url}{path}",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "cal-api-version": api_version,
                },
                params=params,
                json=json,
                timeout=float(timeout),
            )
        except httpx.TimeoutException as error:
            raise BusyTimeSourceError(
                "Cal.com took too long to answer.", CalendarSyncProblem.TIMEOUT
            ) from error
        except httpx.HTTPError as error:
            raise BusyTimeSourceError(
                f"Cal.com cannot be reached: {type(error).__name__}.",
                CalendarSyncProblem.UNREACHABLE,
            ) from error


def iso_instant(unix_seconds: int) -> str:
    return (
        datetime.fromtimestamp(unix_seconds, tz=UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
