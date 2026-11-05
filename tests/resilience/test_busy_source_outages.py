"""
Busy-time reads that Google Calendar or Cal.com answered with a server
error (HTTP 5xx) count against the provider's circuit as unanswered reads
do (REL-04), while the cabinet still explains them as PROVIDER_ERROR; any
other answer (a 400, a refused key, a calendar that is gone) never counts.
"""

from collections.abc import Callable

import httpx
import pytest

from app.adapters.booking_systems.cal_com_booking_system_adapter import (
    CalComBookingSystemAdapter,
)
from app.clients.cal_com.cal_com_client import CalComClient
from app.clients.google.google_calendar_client import GoogleCalendarClient
from app.containers.integration_guards import (
    guard_booking_system,
    guard_google_calendar_client,
)
from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.constants.resilience import CircuitState
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.exceptions.provider_errors import BusyTimeSourceOutageError
from app.utilities.resilience.integration_outages import is_integration_outage
from tests.resilience.test_circuit_breaker import Ticks
from tests.resilience.test_integration_circuits import (
    CAL_COM,
    CALENDAR,
    GOOGLE,
    READ,
    TIMEOUT,
    TOKEN,
    WINDOW,
    breaker,
)

type Answer = Callable[[httpx.Request], httpx.Response]


class CountedAnswers:
    """One fixed HTTP answer, counting the requests that reached it."""

    def __init__(self, status_code: int) -> None:
        self.status_code: int = status_code
        self.requests: int = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        del request
        self.requests += 1
        return httpx.Response(self.status_code, json={"error": {"code": 1}})


def google(answers: CountedAnswers) -> GoogleCalendarClient:
    return GoogleCalendarClient(
        None, None, None, transport=httpx.MockTransport(answers)
    )


def cal_com(answers: CountedAnswers) -> CalComBookingSystemAdapter:
    return CalComBookingSystemAdapter(
        CalComClient(transport=httpx.MockTransport(answers))
    )


@pytest.mark.parametrize(
    ("status_code", "problem", "is_outage"),
    [
        (500, CalendarSyncProblem.PROVIDER_ERROR, True),
        (503, CalendarSyncProblem.PROVIDER_ERROR, True),
        (400, CalendarSyncProblem.PROVIDER_ERROR, False),
        (429, CalendarSyncProblem.PROVIDER_ERROR, False),
        (401, CalendarSyncProblem.NEEDS_RECONNECT, False),
        (404, CalendarSyncProblem.NOT_FOUND, False),
    ],
)
def test_a_google_busy_read_counts_only_a_server_error(
    status_code: int, problem: CalendarSyncProblem, is_outage: bool
) -> None:
    with pytest.raises(BusyTimeSourceError) as raised:
        google(CountedAnswers(status_code)).query_free_busy(
            TOKEN, CALENDAR, WINDOW, TIMEOUT
        )

    assert raised.value.problem is problem
    assert isinstance(raised.value, BusyTimeSourceOutageError) is is_outage
    assert is_integration_outage(raised.value) is is_outage


@pytest.mark.parametrize(
    ("status_code", "problem", "is_outage"),
    [
        (502, CalendarSyncProblem.PROVIDER_ERROR, True),
        (400, CalendarSyncProblem.PROVIDER_ERROR, False),
        (403, CalendarSyncProblem.ACCESS_DENIED, False),
        (410, CalendarSyncProblem.NOT_FOUND, False),
    ],
)
def test_a_cal_com_read_counts_only_a_server_error(
    status_code: int, problem: CalendarSyncProblem, is_outage: bool
) -> None:
    with pytest.raises(BusyTimeSourceError) as raised:
        cal_com(CountedAnswers(status_code)).list_busy(READ)

    assert raised.value.problem is problem
    assert is_integration_outage(raised.value) is is_outage


def test_cal_com_answering_5xx_opens_its_circuit_and_stops_asking() -> None:
    circuits = breaker(Ticks())
    answers = CountedAnswers(503)
    guarded = guard_booking_system(cal_com(answers), circuits)
    for _ in range(5):
        with pytest.raises(BusyTimeSourceOutageError):
            guarded.list_busy(READ)

    with pytest.raises(BusyTimeSourceError) as refused:
        guarded.list_busy(READ)

    assert circuits.state(CAL_COM) is CircuitState.OPEN
    assert refused.value.problem is CalendarSyncProblem.UNREACHABLE
    assert answers.requests == 5


def test_google_answering_400_to_every_business_never_opens_its_circuit() -> None:
    circuits = breaker(Ticks())
    answers = CountedAnswers(400)
    guarded = guard_google_calendar_client(google(answers), circuits)
    for _ in range(10):
        with pytest.raises(BusyTimeSourceError):
            guarded.query_free_busy(TOKEN, CALENDAR, WINDOW, TIMEOUT)

    assert circuits.state(GOOGLE) is CircuitState.CLOSED
    assert answers.requests == 10


def test_google_answering_5xx_to_busy_reads_opens_its_circuit() -> None:
    circuits = breaker(Ticks())
    answers = CountedAnswers(500)
    guarded = guard_google_calendar_client(google(answers), circuits)
    for _ in range(5):
        with pytest.raises(BusyTimeSourceOutageError):
            guarded.query_free_busy(TOKEN, CALENDAR, WINDOW, TIMEOUT)

    with pytest.raises(BusyTimeSourceError) as refused:
        guarded.list_calendars(TOKEN, TIMEOUT)

    assert circuits.state(GOOGLE) is CircuitState.OPEN
    assert refused.value.problem is CalendarSyncProblem.UNREACHABLE
    assert answers.requests == 5
