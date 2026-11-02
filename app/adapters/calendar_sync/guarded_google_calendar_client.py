"""
The Google Calendar client behind the Google Calendar circuit (REL-04).
"""

from app.contracts.operations import GoogleCalendarClientContract
from app.contracts.resilience import CircuitBreakerContract
from app.schemas.dto.calendar_sync.busy_reads import (
    BusyPeriod,
    BusyWindow,
    GoogleCalendarEntry,
)
from app.schemas.dto.operations.calendar_connection import (
    CalendarEventDraft,
    CalendarTokenGrant,
)
from app.schemas.typings.bookings.constrained_strings import CalendarAuthorizationUrl
from app.schemas.typings.bookings.strings import (
    CalendarAccessToken,
    CalendarAuthorizationCode,
    CalendarAuthorizationState,
    CalendarCodeChallenge,
    CalendarCodeVerifier,
    CalendarDisplayName,
    CalendarEventId,
    CalendarRefreshToken,
    ExternalCalendarId,
)
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.utilities.resilience.integration_outages import (
    call_integration,
    read_busy_source,
)


class GuardedGoogleCalendarClient(GoogleCalendarClientContract):
    """
    Decorator of the Google OAuth and Calendar client: every network call
    goes through the Google Calendar circuit (`provider:google_calendar`,
    shared by every business). After repeated calls Google did not answer
    or answered with a 5xx the circuit opens: a mirror, an erasure or a
    consent call fails at once with ProviderCircuitOpenError (their
    callers already retry or report an ExternalServiceError), a busy-time
    read with BusyTimeSourceError UNREACHABLE (the busy times read before
    stay in force); after the circuit's wait one trial call goes through
    (half-open). A business's own refusal (a revoked consent, a calendar
    that is gone) never counts. Building the consent URL makes no call.
    """

    def __init__(
        self,
        inner_client: GoogleCalendarClientContract,
        circuit_breaker: CircuitBreakerContract,
        circuit: CircuitName,
    ) -> None:
        self._inner: GoogleCalendarClientContract = inner_client
        self._circuit_breaker: CircuitBreakerContract = circuit_breaker
        self._circuit: CircuitName = circuit

    def is_configured(self) -> bool:
        return self._inner.is_configured()

    def build_authorization_url(
        self,
        state: CalendarAuthorizationState,
        code_challenge: CalendarCodeChallenge,
    ) -> CalendarAuthorizationUrl:
        return self._inner.build_authorization_url(state, code_challenge)

    def exchange_code(
        self,
        code: CalendarAuthorizationCode,
        code_verifier: CalendarCodeVerifier,
    ) -> CalendarTokenGrant:
        return call_integration(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.exchange_code(code, code_verifier),
        )

    def refresh_access_token(
        self,
        refresh_token: CalendarRefreshToken,
    ) -> CalendarTokenGrant:
        return call_integration(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.refresh_access_token(refresh_token),
        )

    def revoke_token(self, refresh_token: CalendarRefreshToken) -> None:
        call_integration(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.revoke_token(refresh_token),
        )

    def get_calendar_name(
        self,
        access_token: CalendarAccessToken,
        calendar_id: ExternalCalendarId,
    ) -> CalendarDisplayName | None:
        return call_integration(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.get_calendar_name(access_token, calendar_id),
        )

    def insert_event(
        self,
        access_token: CalendarAccessToken,
        calendar_id: ExternalCalendarId,
        event: CalendarEventDraft,
    ) -> CalendarEventId:
        return call_integration(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.insert_event(access_token, calendar_id, event),
        )

    def patch_event(
        self,
        access_token: CalendarAccessToken,
        calendar_id: ExternalCalendarId,
        event_id: CalendarEventId,
        event: CalendarEventDraft,
    ) -> None:
        call_integration(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.patch_event(access_token, calendar_id, event_id, event),
        )

    def delete_event(
        self,
        access_token: CalendarAccessToken,
        calendar_id: ExternalCalendarId,
        event_id: CalendarEventId,
    ) -> None:
        call_integration(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.delete_event(access_token, calendar_id, event_id),
        )

    def query_free_busy(
        self,
        access_token: CalendarAccessToken,
        calendar_id: ExternalCalendarId,
        window: BusyWindow,
        timeout: BusyTimeFetchSeconds,
    ) -> list[BusyPeriod]:
        return read_busy_source(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.query_free_busy(
                access_token, calendar_id, window, timeout
            ),
        )

    def list_calendars(
        self,
        access_token: CalendarAccessToken,
        timeout: BusyTimeFetchSeconds,
    ) -> list[GoogleCalendarEntry]:
        return read_busy_source(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.list_calendars(access_token, timeout),
        )
