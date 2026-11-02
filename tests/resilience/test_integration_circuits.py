"""
The businesses' integrations behind their circuits (REL-04): Google
Calendar, Cal.com and Twilio's phone numbers open after repeated calls
the provider did not answer (or answered with a 5xx), refuse at once while
open, let one trial through after the wait (half-open), and never open on
one business's own refusal.
"""

from collections.abc import Callable

import pytest

from app.adapters.booking_systems.circuit_breaking_booking_system_adapter import (
    CircuitBreakingBookingSystemAdapter,
)
from app.containers.integration_guards import (
    guard_booking_system,
    guard_google_calendar_client,
    guard_twilio_phone_numbers,
)
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.constants.calendar_sync import BookingSystemKind, CalendarSyncProblem
from app.schemas.constants.resilience import CircuitState, OutboundProvider
from app.schemas.dto.calendar_sync.busy_reads import (
    BookingSystemCredentials,
    BookingSystemRead,
    BusyWindow,
)
from app.schemas.dto.operations.calendar_connection import CalendarEventDraft
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ProviderCircuitOpenError,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.exceptions.phone_number_errors import PhoneNumberUnavailableError
from app.schemas.exceptions.provider_errors import ProviderOutageError
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.bookings.strings import (
    CalendarAccessToken,
    CalendarEventDescription,
    CalendarEventId,
    CalendarEventTitle,
    CalendarRefreshToken,
    ExternalCalendarId,
)
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.schemas.typings.calendar_sync.constrained_integers import (
    BusyEndsAtUnixSeconds,
    BusyStartsAtUnixSeconds,
)
from app.schemas.typings.calendar_sync.constrained_strings import (
    BookingSystemResourceId,
)
from app.schemas.typings.calendar_sync.strings import (
    BookingSystemApiKey,
    BookingSystemBookingId,
)
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.schemas.typings.telephony.constrained_strings import VoiceFallbackUrl
from app.utilities.resilience.provider_circuits import (
    guarded_circuits,
    provider_circuit,
)
from tests.resilience.integration_doubles import (
    NUMBER,
    ScriptedBookingSystem,
    ScriptedGoogle,
    ScriptedTwilioNumbers,
)
from tests.resilience.test_circuit_breaker import Ticks

GOOGLE = provider_circuit(OutboundProvider.GOOGLE_CALENDAR)
CAL_COM = provider_circuit(OutboundProvider.CAL_COM)
TWILIO_NUMBERS = provider_circuit(OutboundProvider.TWILIO_NUMBERS)
TOKEN = CalendarAccessToken("access")
CALENDAR = ExternalCalendarId("primary")
TIMEOUT = BusyTimeFetchSeconds(5.0)
WINDOW = BusyWindow(
    starts_at=BusyStartsAtUnixSeconds(1_791_000_000),
    ends_at=BusyEndsAtUnixSeconds(1_791_086_400),
)
READ = BookingSystemRead(
    credentials=BookingSystemCredentials(
        api_key=BookingSystemApiKey("cal_live_key"),
        external_resource_id=BookingSystemResourceId("1234"),
    ),
    window=WINDOW,
    timeout=TIMEOUT,
)
EVENT = CalendarEventDraft(
    title=CalendarEventTitle("Booking: Giulia, guests: 2"),
    description=CalendarEventDescription("Table 4"),
    starts_at=BookingStartsAtUnixSeconds(1_791_050_400),
    ends_at=BookingEndsAtUnixSeconds(1_791_057_600),
    timezone=TimezoneName("Europe/Rome"),
)
WRITTEN = BookingSystemBookingId("booking-1")
FALLBACK = VoiceFallbackUrl("https://api.workshop.example/v1/telephony/twilio/x")


def breaker(ticks: Ticks) -> CircuitBreakerFacilitator:
    return CircuitBreakerFacilitator(ticks.clock(), known_circuits=guarded_circuits())


def fail_times(call: Callable[[], object], times: int) -> None:
    for _ in range(times):
        with pytest.raises(ApplicationError):
            call()


def test_each_integration_has_its_own_circuit() -> None:
    circuits = guarded_circuits()

    assert {GOOGLE, CAL_COM, TWILIO_NUMBERS} <= set(circuits)
    assert len(set(circuits)) == len(circuits)


def test_google_opens_after_five_unanswered_calls_and_refuses_at_once() -> None:
    ticks = Ticks()
    circuits = breaker(ticks)
    google = ScriptedGoogle()
    guarded = guard_google_calendar_client(google, circuits)
    google.error = ProviderOutageError("Google Calendar event insert failed.")

    fail_times(lambda: guarded.insert_event(TOKEN, CALENDAR, EVENT), 5)
    with pytest.raises(ProviderCircuitOpenError) as refused:
        guarded.delete_event(TOKEN, CALENDAR, CalendarEventId("event-1"))
    with pytest.raises(BusyTimeSourceError) as unreachable:
        guarded.query_free_busy(TOKEN, CALENDAR, WINDOW, TIMEOUT)

    assert google.calls == 5
    assert circuits.state(GOOGLE) is CircuitState.OPEN
    assert refused.value.retry_after_seconds is not None
    assert unreachable.value.problem is CalendarSyncProblem.UNREACHABLE
    assert circuits.state(CAL_COM) is CircuitState.CLOSED


def test_a_trial_after_the_wait_closes_the_circuit_again() -> None:
    ticks = Ticks()
    circuits = breaker(ticks)
    google = ScriptedGoogle()
    guarded = guard_google_calendar_client(google, circuits)
    google.error = BusyTimeSourceError("Timed out.", CalendarSyncProblem.TIMEOUT)
    fail_times(lambda: guarded.list_calendars(TOKEN, TIMEOUT), 5)

    ticks.advance(31)
    google.error = None
    assert guarded.list_calendars(TOKEN, TIMEOUT) == []

    assert circuits.state(GOOGLE) is CircuitState.CLOSED


def test_a_businesss_own_refusal_never_opens_the_circuit() -> None:
    circuits = breaker(Ticks())
    google = ScriptedGoogle()
    guarded = guard_google_calendar_client(google, circuits)
    google.error = ExternalServiceError(
        "Google token refresh returned HTTP 400 (invalid_grant)."
    )

    fail_times(lambda: guarded.refresh_access_token(CalendarRefreshToken("r")), 20)
    google.error = BusyTimeSourceError("Gone.", CalendarSyncProblem.NOT_FOUND)
    fail_times(lambda: guarded.query_free_busy(TOKEN, CALENDAR, WINDOW, TIMEOUT), 20)

    assert google.calls == 40
    assert circuits.state(GOOGLE) is CircuitState.CLOSED


def test_the_consent_url_needs_no_call() -> None:
    circuits = breaker(Ticks())
    google = ScriptedGoogle()
    for _ in range(5):
        circuits.record_failure(GOOGLE)

    guarded = guard_google_calendar_client(google, circuits)

    assert guarded.is_configured() is True
    assert google.calls == 0


def test_a_booking_system_counts_its_timeouts_not_a_refused_key() -> None:
    circuits = breaker(Ticks())
    cal_com = ScriptedBookingSystem()
    guarded = guard_booking_system(cal_com, circuits)
    cal_com.error = BusyTimeSourceError("Refused.", CalendarSyncProblem.ACCESS_DENIED)
    fail_times(lambda: guarded.list_busy(READ), 10)
    assert circuits.state(CAL_COM) is CircuitState.CLOSED

    cal_com.error = BusyTimeSourceError("Unreachable.", CalendarSyncProblem.UNREACHABLE)
    fail_times(lambda: guarded.list_busy(READ), 5)
    with pytest.raises(BusyTimeSourceError) as refused:
        guarded.cancel_booking(READ.credentials, WRITTEN, TIMEOUT)

    assert isinstance(guarded, CircuitBreakingBookingSystemAdapter)
    assert guarded.kind is BookingSystemKind.CAL_COM
    assert circuits.state(CAL_COM) is CircuitState.OPEN
    assert refused.value.problem is CalendarSyncProblem.UNREACHABLE
    assert cal_com.calls == 15


def test_twilio_numbers_open_on_server_errors_not_on_a_number_that_is_gone() -> None:
    circuits = breaker(Ticks())
    twilio = ScriptedTwilioNumbers()
    guarded = guard_twilio_phone_numbers(twilio, circuits)
    twilio.error = PhoneNumberUnavailableError("The number was taken.")
    fail_times(lambda: guarded.release_number(NUMBER), 10)
    assert circuits.state(TWILIO_NUMBERS) is CircuitState.CLOSED

    twilio.error = ProviderOutageError("Twilio answered HTTP 503.")
    fail_times(lambda: guarded.set_voice_fallback(NUMBER, FALLBACK), 5)
    with pytest.raises(ProviderCircuitOpenError):
        guarded.release_number(NUMBER)

    assert twilio.calls == 15
    assert circuits.state(TWILIO_NUMBERS) is CircuitState.OPEN
    assert circuits.state(provider_circuit(OutboundProvider.TWILIO_SMS)) is (
        CircuitState.CLOSED
    )
