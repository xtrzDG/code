"""
Doubles of the integration circuit tests: a Google Calendar client, a
booking system connector and Twilio's phone numbers that each answer with
the error the test sets (or a fixed result), counting their calls.
"""

from app.schemas.constants.calendar_sync import BookingSystemKind
from app.schemas.constants.phone_numbers import PhoneNumberType
from app.schemas.dto.calendar_sync.busy_reads import (
    BookingSystemBookingCreated,
    BookingSystemBookingDraft,
    BookingSystemCredentials,
    BookingSystemRead,
    BookingSystemResource,
    BusyPeriod,
    BusyWindow,
    GoogleCalendarEntry,
)
from app.schemas.dto.operations.calendar_connection import (
    CalendarEventDraft,
    CalendarTokenGrant,
)
from app.schemas.dto.phone_numbers.provisioning import (
    AvailablePhoneNumber,
    PhoneNumberPurchase,
    PhoneNumberSearchQuery,
)
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.bookings.constrained_integers import (
    CalendarTokenLifetimeSeconds,
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
from app.schemas.typings.calendar_sync.strings import BookingSystemBookingId
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.telephony.constrained_strings import VoiceFallbackUrl
from app.schemas.typings.telephony.strings import ProviderPhoneNumberId

GRANT: CalendarTokenGrant = CalendarTokenGrant(
    access_token=CalendarAccessToken("access"),
    refresh_token=None,
    expires_in=CalendarTokenLifetimeSeconds(3600),
)
NUMBER: ProviderPhoneNumberId = ProviderPhoneNumberId("PN0123456789abcdef")
WRITTEN: BookingSystemBookingId = BookingSystemBookingId("booking-1")


class Scripted:
    """Raises `error` when one is set; counts every call."""

    def __init__(self) -> None:
        self.error: BaseException | None = None
        self.calls: int = 0

    def _answer[T](self, result: T) -> T:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return result


class ScriptedGoogle(Scripted):
    """Google OAuth and Calendar, answering as scripted."""

    def is_configured(self) -> bool:
        return True

    def build_authorization_url(
        self, state: CalendarAuthorizationState, code_challenge: CalendarCodeChallenge
    ) -> CalendarAuthorizationUrl:
        del state, code_challenge
        return CalendarAuthorizationUrl("https://accounts.google.com/o/oauth2/auth")

    def exchange_code(
        self, code: CalendarAuthorizationCode, code_verifier: CalendarCodeVerifier
    ) -> CalendarTokenGrant:
        del code, code_verifier
        return self._answer(GRANT)

    def refresh_access_token(
        self, refresh_token: CalendarRefreshToken
    ) -> CalendarTokenGrant:
        del refresh_token
        return self._answer(GRANT)

    def revoke_token(self, refresh_token: CalendarRefreshToken) -> None:
        del refresh_token
        self._answer(None)

    def get_calendar_name(
        self, access_token: CalendarAccessToken, calendar_id: ExternalCalendarId
    ) -> CalendarDisplayName | None:
        del access_token, calendar_id
        return self._answer(CalendarDisplayName("Bookings"))

    def insert_event(
        self,
        access_token: CalendarAccessToken,
        calendar_id: ExternalCalendarId,
        event: CalendarEventDraft,
    ) -> CalendarEventId:
        del access_token, calendar_id, event
        return self._answer(CalendarEventId("event-1"))

    def patch_event(
        self,
        access_token: CalendarAccessToken,
        calendar_id: ExternalCalendarId,
        event_id: CalendarEventId,
        event: CalendarEventDraft,
    ) -> None:
        del access_token, calendar_id, event_id, event
        self._answer(None)

    def delete_event(
        self,
        access_token: CalendarAccessToken,
        calendar_id: ExternalCalendarId,
        event_id: CalendarEventId,
    ) -> None:
        del access_token, calendar_id, event_id
        self._answer(None)

    def query_free_busy(
        self,
        access_token: CalendarAccessToken,
        calendar_id: ExternalCalendarId,
        window: BusyWindow,
        timeout: BusyTimeFetchSeconds,
    ) -> list[BusyPeriod]:
        del access_token, calendar_id, window, timeout
        return self._answer([])

    def list_calendars(
        self, access_token: CalendarAccessToken, timeout: BusyTimeFetchSeconds
    ) -> list[GoogleCalendarEntry]:
        del access_token, timeout
        return self._answer([])


class ScriptedBookingSystem(Scripted):
    """A booking system connector (Cal.com), answering as scripted."""

    kind: BookingSystemKind = BookingSystemKind.CAL_COM

    def describe(
        self, credentials: BookingSystemCredentials, timeout: BusyTimeFetchSeconds
    ) -> BookingSystemResource:
        del timeout
        return self._answer(
            BookingSystemResource(external_resource_id=credentials.external_resource_id)
        )

    def list_busy(self, read: BookingSystemRead) -> list[BusyPeriod]:
        del read
        return self._answer([])

    def create_booking(
        self,
        credentials: BookingSystemCredentials,
        draft: BookingSystemBookingDraft,
        timeout: BusyTimeFetchSeconds,
    ) -> BookingSystemBookingCreated:
        del credentials, draft, timeout
        return self._answer(BookingSystemBookingCreated(booking_id=WRITTEN))

    def find_booking(
        self,
        credentials: BookingSystemCredentials,
        draft: BookingSystemBookingDraft,
        timeout: BusyTimeFetchSeconds,
    ) -> BookingSystemBookingId | None:
        del credentials, draft, timeout
        return self._answer(WRITTEN)

    def cancel_booking(
        self,
        credentials: BookingSystemCredentials,
        booking_id: BookingSystemBookingId,
        timeout: BusyTimeFetchSeconds,
    ) -> None:
        del credentials, booking_id, timeout
        self._answer(None)


class ScriptedTwilioNumbers(Scripted):
    """Twilio's phone numbers, answering as scripted."""

    def list_available_numbers(
        self, query: PhoneNumberSearchQuery
    ) -> list[AvailablePhoneNumber]:
        del query
        return self._answer([])

    def get_monthly_price(
        self, country_code: CountryCode, number_type: PhoneNumberType
    ) -> CostMicroUsd | None:
        del country_code, number_type
        return self._answer(CostMicroUsd(1_150_000))

    def buy_number(self, purchase: PhoneNumberPurchase) -> ProviderPhoneNumberId:
        del purchase
        return self._answer(NUMBER)

    def release_number(self, provider_number_id: ProviderPhoneNumberId) -> None:
        del provider_number_id
        self._answer(None)

    def set_voice_fallback(
        self, provider_number_id: ProviderPhoneNumberId, url: VoiceFallbackUrl
    ) -> None:
        del provider_number_id, url
        self._answer(None)
