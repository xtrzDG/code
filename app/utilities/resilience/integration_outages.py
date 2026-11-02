"""
Which failures of a business's integration (Google Calendar, a booking
system such as Cal.com, Twilio's phone numbers) mean the provider itself
is in trouble, and so count against its circuit breaker (REL-04).

These providers answer one business's own problem with an error too: a
revoked consent, a calendar or event type that is gone, a refused key.
Such an answer says nothing about the provider, so only a call that got
no answer (a timeout, a connection error) or a server error counts; with
many businesses on one circuit, one business's broken setting never opens
it for the others.
"""

from collections.abc import Callable

from app.contracts.resilience import CircuitBreakerContract
from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.exceptions.application_errors import ProviderCircuitOpenError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.exceptions.provider_errors import ProviderOutageError
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.utilities.resilience.circuit_calls import call_through_circuit

UNANSWERED_PROBLEMS: frozenset[CalendarSyncProblem] = frozenset(
    {CalendarSyncProblem.TIMEOUT, CalendarSyncProblem.UNREACHABLE}
)


def is_integration_outage(error: ApplicationError) -> bool:
    """
    A busy-time read that timed out or could not reach the provider, or a
    call the provider did not answer or answered with a 5xx.
    """

    if isinstance(error, BusyTimeSourceError):
        return error.problem in UNANSWERED_PROBLEMS

    return isinstance(error, ProviderOutageError)


def call_integration[T](
    circuit_breaker: CircuitBreakerContract,
    circuit: CircuitName,
    call: Callable[[], T],
) -> T:
    """
    The call through the integration's circuit, counting only its outages.

    Raises:
        ProviderCircuitOpenError: the circuit is open, nothing was sent.
        ApplicationError: whatever the call raised.
    """

    return call_through_circuit(circuit_breaker, circuit, call, is_integration_outage)


def read_busy_source[T](
    circuit_breaker: CircuitBreakerContract,
    circuit: CircuitName,
    call: Callable[[], T],
) -> T:
    """
    A busy-time source's call through its circuit: while the circuit is
    open the source counts as unreachable, as its readers expect.

    Raises:
        BusyTimeSourceError: why the source was not read (UNREACHABLE while
            the circuit is open).
    """

    try:
        return call_integration(circuit_breaker, circuit, call)
    except ProviderCircuitOpenError as error:
        raise BusyTimeSourceError(
            "The provider failed again and again just now; it is tried again "
            "in a moment.",
            CalendarSyncProblem.UNREACHABLE,
        ) from error
