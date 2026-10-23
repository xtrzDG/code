"""
Failures that say nothing about a provider's health never open its circuit:
Flitt refusing a call (an HTTP 4xx, an answer with the status "failure"),
online payments not set up, and a typing signal that returned without a
call. Only a real outage counts, and a best-effort typing signal never
takes the trial call of a half-open circuit nor closes it.
"""

from collections.abc import Callable

import httpx
import pytest

from app.adapters.payments.circuit_breaking_payment_gateway_adapter import (
    CircuitBreakingPaymentGatewayAdapter,
)
from app.adapters.payments.flitt_payment_gateway_adapter import (
    FlittPaymentGatewayAdapter,
)
from app.clients.flitt.flitt_client import FlittClient
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.constants.resilience import CircuitState, OutboundProvider
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ProviderCircuitOpenError,
    ProviderRateLimitedError,
)
from app.schemas.exceptions.payment_errors import (
    PaymentProviderRefusedError,
    PaymentsNotConfiguredError,
)
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from app.utilities.resilience.provider_circuits import provider_circuit
from tests.billing.test_flitt_payment_gateway import build_checkout_request
from tests.resilience.test_circuit_breaker import Ticks

FLITT = provider_circuit(OutboundProvider.FLITT)
META = provider_circuit(OutboundProvider.META)
ORDER = PaymentProviderReference("802345671")
CALLS_TO_OPEN: int = 5


def flitt_answering(
    status_code: int, body: dict[str, object], calls: list[str]
) -> FlittClient:
    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(status_code, json={"response": body})

    return FlittClient(
        PlatformIdentifier("1549901"),
        PlatformSecret("test-secret-0000"),
        transport=httpx.MockTransport(handle),
    )


def guarded(
    client: FlittClient | None, breaker: CircuitBreakerFacilitator
) -> CircuitBreakingPaymentGatewayAdapter:
    return CircuitBreakingPaymentGatewayAdapter(
        FlittPaymentGatewayAdapter(client, PublicBaseUrl("https://api.example.com")),
        breaker,
        FLITT,
    )


def call_repeatedly(
    call: Callable[[], object], error: type[Exception], times: int
) -> None:
    for _ in range(times):
        with pytest.raises(error):
            call()


@pytest.mark.parametrize(
    ("status_code", "body", "error"),
    [
        (400, {"response_status": "failure"}, PaymentProviderRefusedError),
        (404, {}, PaymentProviderRefusedError),
        (
            200,
            {"response_status": "failure", "error_message": "Order is stopped"},
            PaymentProviderRefusedError,
        ),
        (429, {}, ProviderRateLimitedError),
    ],
)
def test_flitt_refusals_leave_the_circuit_closed(
    status_code: int, body: dict[str, object], error: type[Exception]
) -> None:
    calls: list[str] = []
    breaker = CircuitBreakerFacilitator(Ticks().clock())
    gateway = guarded(flitt_answering(status_code, body, calls), breaker)

    call_repeatedly(lambda: gateway.stop_recurring(ORDER), error, CALLS_TO_OPEN + 1)
    call_repeatedly(lambda: gateway.create_checkout(build_checkout_request()), error, 1)

    # Every call reached Flitt: it answers, so it is up.
    assert len(calls) == CALLS_TO_OPEN + 2
    assert breaker.state(FLITT) is CircuitState.CLOSED


def test_payments_not_set_up_leave_the_circuit_closed() -> None:
    breaker = CircuitBreakerFacilitator(Ticks().clock())
    unconfigured = guarded(None, breaker)
    no_base_url = CircuitBreakingPaymentGatewayAdapter(
        FlittPaymentGatewayAdapter(flitt_answering(200, {}, []), None), breaker, FLITT
    )

    call_repeatedly(
        lambda: unconfigured.stop_recurring(ORDER),
        PaymentsNotConfiguredError,
        CALLS_TO_OPEN,
    )
    call_repeatedly(
        lambda: no_base_url.create_checkout(build_checkout_request()),
        PaymentsNotConfiguredError,
        CALLS_TO_OPEN,
    )

    assert breaker.state(FLITT) is CircuitState.CLOSED


def test_flitt_5xx_still_opens_the_circuit() -> None:
    calls: list[str] = []
    breaker = CircuitBreakerFacilitator(Ticks().clock())
    gateway = guarded(flitt_answering(503, {}, calls), breaker)

    call_repeatedly(
        lambda: gateway.stop_recurring(ORDER), ExternalServiceError, CALLS_TO_OPEN
    )
    with pytest.raises(ProviderCircuitOpenError):
        gateway.stop_recurring(ORDER)

    assert len(calls) == CALLS_TO_OPEN
    assert breaker.state(FLITT) is CircuitState.OPEN
