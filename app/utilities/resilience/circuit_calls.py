"""
One call to a provider through its circuit breaker: refused at once while
the circuit is open (no network call; the caller tries again later), and
reported to the circuit after it ran.
"""

import logging
from collections.abc import Callable

from app.contracts.resilience import CircuitBreakerContract
from app.schemas.exceptions.application_errors import ProviderCircuitOpenError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.constrained_integers import RetryAfterSeconds
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.utilities.resilience.provider_circuits import is_provider_outage

logger: logging.Logger = logging.getLogger(__name__)


def call_through_circuit[T](
    circuit_breaker: CircuitBreakerContract,
    circuit: CircuitName,
    call: Callable[[], T],
) -> T:
    """
    The call's result. A provider outage (a timeout, a connection error, a
    5xx) counts against the circuit; an answer of the provider (a success,
    a refusal, a rate limit) or a call the business's own setting stopped
    closes a half-open circuit and resets the failures of a closed one.

    Raises:
        ProviderCircuitOpenError: the circuit is open, nothing was sent;
            `retry_after_seconds` says when it lets a trial call through.
        ApplicationError: whatever the call raised.
    """

    if not circuit_breaker.allows_call(circuit):
        retry_after: RetryAfterSeconds | None = circuit_breaker.seconds_until_trial(
            circuit
        )
        raise ProviderCircuitOpenError(
            f"The circuit {circuit} is open after repeated failures; nothing was sent.",
            retry_after_seconds=retry_after,
        )

    try:
        result: T = call()
    except ApplicationError as error:
        if is_provider_outage(error):
            circuit_breaker.record_failure(circuit)
        else:
            circuit_breaker.record_success(circuit)
        raise
    except BaseException:
        # No answer we understood (an unreadable response, a stop): it
        # counts as a failure, so a trial call never stays unreported.
        circuit_breaker.record_failure(circuit)
        raise

    circuit_breaker.record_success(circuit)
    return result
