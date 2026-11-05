"""
The integration guards behave like the clients they wrap while their
circuits are closed, and the clients name what counts against a circuit:
a call Google or Twilio did not answer, or answered with a 5xx, is a
ProviderOutageError; their refusals (4xx) stay plain ExternalServiceError.
"""

from collections.abc import Callable

import httpx
import pytest

from app.clients.google.google_calendar_client import GoogleCalendarClient
from app.clients.twilio.twilio_phone_numbers_client import TwilioPhoneNumbersClient
from app.containers.integration_guards import (
    guard_booking_system,
    guard_google_calendar_client,
    guard_twilio_phone_numbers,
)
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.constants.phone_numbers import PhoneNumberType
from app.schemas.dto.calendar_sync.busy_reads import BookingSystemBookingDraft
from app.schemas.dto.phone_numbers.provisioning import (
    PhoneNumberPurchase,
    PhoneNumberSearchQuery,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.exceptions.provider_errors import ProviderOutageError
from app.schemas.typings.bookings.strings import (
    CalendarAuthorizationCode,
    CalendarAuthorizationState,
    CalendarCodeChallenge,
    CalendarCodeVerifier,
    CalendarEventId,
    CalendarRefreshToken,
)
from app.schemas.typings.calendar_sync.constrained_integers import (
    BusyEndsAtUnixSeconds,
    BusyStartsAtUnixSeconds,
)
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.messaging.constrained_strings import TwilioAccountSid
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.telephony.constrained_strings import PhoneNumberLabel
from app.utilities.resilience.integration_outages import is_integration_outage
from app.utilities.resilience.provider_circuits import guarded_circuits
from tests.resilience.integration_doubles import (
    GRANT,
    NUMBER,
    WRITTEN,
    ScriptedBookingSystem,
    ScriptedGoogle,
    ScriptedTwilioNumbers,
)
from tests.resilience.test_circuit_breaker import Ticks
from tests.resilience.test_integration_circuits import (
    CALENDAR,
    EVENT,
    FALLBACK,
    READ,
    TIMEOUT,
    TOKEN,
    WINDOW,
)

DRAFT = BookingSystemBookingDraft(
    starts_at=BusyStartsAtUnixSeconds(1_791_050_400),
    ends_at=BusyEndsAtUnixSeconds(1_791_057_600),
    guest_name=ContactName("Giulia"),
    time_zone=TimezoneName("Europe/Rome"),
    language=LanguageTag("it"),
)
TWILIO_ACCOUNT = TwilioAccountSid("AC" + "0" * 32)


def breaker() -> CircuitBreakerFacilitator:
    return CircuitBreakerFacilitator(Ticks().clock(), known_circuits=guarded_circuits())


def test_every_google_call_passes_through_while_closed() -> None:
    google = ScriptedGoogle()
    guarded = guard_google_calendar_client(google, breaker())

    url = guarded.build_authorization_url(
        CalendarAuthorizationState("state"), CalendarCodeChallenge("challenge")
    )
    grants = [
        guarded.exchange_code(
            CalendarAuthorizationCode("code"), CalendarCodeVerifier("verifier")
        ),
        guarded.refresh_access_token(CalendarRefreshToken("refresh")),
    ]
    guarded.revoke_token(CalendarRefreshToken("refresh"))
    name = guarded.get_calendar_name(TOKEN, CALENDAR)
    event_id = guarded.insert_event(TOKEN, CALENDAR, EVENT)
    guarded.patch_event(TOKEN, CALENDAR, event_id, EVENT)
    guarded.delete_event(TOKEN, CALENDAR, CalendarEventId("event-1"))
    busy = guarded.query_free_busy(TOKEN, CALENDAR, WINDOW, TIMEOUT)

    assert str(url).startswith("https://accounts.google.com/")
    assert grants == [GRANT, GRANT]
    assert str(name) == "Bookings"
    assert busy == []
    assert google.calls == 8


def test_every_booking_system_call_passes_through_while_closed() -> None:
    cal_com = ScriptedBookingSystem()
    guarded = guard_booking_system(cal_com, breaker())

    resource = guarded.describe(READ.credentials, TIMEOUT)
    created = guarded.create_booking(READ.credentials, DRAFT, TIMEOUT)
    found = guarded.find_booking(READ.credentials, DRAFT, TIMEOUT)

    assert resource.external_resource_id == READ.credentials.external_resource_id
    assert created.booking_id == WRITTEN
    assert found == WRITTEN
    assert cal_com.calls == 3


def test_every_twilio_numbers_call_passes_through_while_closed() -> None:
    twilio = ScriptedTwilioNumbers()
    guarded = guard_twilio_phone_numbers(twilio, breaker())

    offers = guarded.list_available_numbers(
        PhoneNumberSearchQuery(
            country_code=CountryCode("IT"), number_type=PhoneNumberType.LOCAL
        )
    )
    price = guarded.get_monthly_price(CountryCode("IT"), PhoneNumberType.LOCAL)
    bought = guarded.buy_number(
        PhoneNumberPurchase(
            phone_number=E164PhoneNumber("+390212345678"),
            label=PhoneNumberLabel("Trattoria"),
        )
    )

    assert offers == []
    assert price is not None
    assert bought == NUMBER
    assert twilio.calls == 3


def google_answering(
    answer: Callable[[httpx.Request], httpx.Response],
) -> GoogleCalendarClient:
    return GoogleCalendarClient(None, None, None, transport=httpx.MockTransport(answer))


type Answer = Callable[[httpx.Request], httpx.Response]


def unreachable(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("connection refused", request=request)


def status(code: int, body: dict[str, object]) -> Answer:
    def answer(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(code, json=body)

    return answer


@pytest.mark.parametrize(
    ("answer", "is_outage"),
    [
        (status(503, {"error": "backendError"}), True),
        (unreachable, True),
        (status(401, {"error": "invalid_grant"}), False),
        (status(404, {}), False),
    ],
)
def test_google_names_its_outages(
    answer: Callable[[httpx.Request], httpx.Response], is_outage: bool
) -> None:
    with pytest.raises(ExternalServiceError) as raised:
        google_answering(answer).insert_event(TOKEN, CALENDAR, EVENT)

    assert isinstance(raised.value, ProviderOutageError) is is_outage
    assert is_integration_outage(raised.value) is is_outage


@pytest.mark.parametrize(
    ("answer", "is_outage"),
    [
        (status(500, {"code": 20500}), True),
        (unreachable, True),
        (status(401, {"code": 20003}), False),
        (status(400, {"code": 21422}), False),
    ],
)
def test_twilio_numbers_name_their_outages(
    answer: Callable[[httpx.Request], httpx.Response], is_outage: bool
) -> None:
    twilio = TwilioPhoneNumbersClient(
        TWILIO_ACCOUNT, PlatformSecret("token"), transport=httpx.MockTransport(answer)
    )

    with pytest.raises(ExternalServiceError) as raised:
        twilio.set_voice_fallback(NUMBER, FALLBACK)

    assert isinstance(raised.value, ProviderOutageError) is is_outage


@pytest.mark.parametrize(
    ("problem", "is_outage"),
    [
        (CalendarSyncProblem.TIMEOUT, True),
        (CalendarSyncProblem.UNREACHABLE, True),
        (CalendarSyncProblem.NEEDS_RECONNECT, False),
        (CalendarSyncProblem.ACCESS_DENIED, False),
        (CalendarSyncProblem.NOT_FOUND, False),
        (CalendarSyncProblem.PROVIDER_ERROR, False),
    ],
)
def test_only_unanswered_busy_reads_are_outages(
    problem: CalendarSyncProblem, is_outage: bool
) -> None:
    assert is_integration_outage(BusyTimeSourceError("x", problem)) is is_outage
