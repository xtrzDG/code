"""The HTTP calls of the Google client: errors without tokens, time limits."""

import httpx

from app.clients.google.google_api_responses import ensure_success, read_json_object
from app.clients.google.google_calendar_requests import bearer
from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.typings.bookings.strings import CalendarAccessToken
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds

REQUEST_TIMEOUT_SECONDS: float = 10.0


class GoogleHttp:
    """
    One httpx client for Google's OAuth and Calendar endpoints. Network
    errors become ExternalServiceError (BusyTimeSourceError for the
    availability reads, with a timeout of their own); messages name the
    operation and the error type only.
    """

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._client: httpx.Client = httpx.Client(
            timeout=REQUEST_TIMEOUT_SECONDS, transport=transport
        )

    def send(
        self,
        method: str,
        url: str,
        operation: str,
        headers: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
        json: dict[str, object] | None = None,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        try:
            return self._client.request(
                method, url, headers=headers, data=data, json=json, params=params
            )
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                f"{operation} failed: {type(error).__name__}."
            ) from error

    def post_form(
        self, url: str, form: dict[str, str], operation: str
    ) -> dict[str, object]:
        response: httpx.Response = self.send("POST", url, operation, data=form)
        ensure_success(response, operation)
        return read_json_object(response, operation)

    def read_availability(
        self,
        method: str,
        url: str,
        access_token: CalendarAccessToken,
        timeout: BusyTimeFetchSeconds,
        json: dict[str, object] | None = None,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        """A free/busy or calendar list request within `timeout` seconds."""

        try:
            return self._client.request(
                method,
                url,
                headers=bearer(access_token),
                json=json,
                params=params,
                timeout=float(timeout),
            )
        except httpx.TimeoutException as error:
            raise BusyTimeSourceError(
                "Google Calendar took too long to answer.",
                CalendarSyncProblem.TIMEOUT,
            ) from error
        except httpx.HTTPError as error:
            raise BusyTimeSourceError(
                f"Google Calendar cannot be reached: {type(error).__name__}.",
                CalendarSyncProblem.UNREACHABLE,
            ) from error
