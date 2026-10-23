"""
Stripe sits behind its own circuit (`provider:stripe`), apart from Flitt's:
a refusal (a declined card, a 4xx, a request to slow down) says Stripe is up
and leaves the circuit closed, Stripe not set up makes no call at all, and
only a timeout or a 5xx counts against it; once open, a checkout, a stop of
automatic charges and a retried charge fail at once without a request.
"""

import httpx
import pytest

from app.adapters.payments.circuit_breaking_payment_gateway_adapter import (
    CircuitBreakingPaymentGatewayAdapter,
)
from app.adapters.payments.stripe_billing_adapter import StripeBillingAdapter
from app.clients.stripe.stripe_client import StripeClient
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.constants.payments import PaymentProvider
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
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.utilities.resilience.provider_circuits import (
    guarded_circuits,
    provider_circuit,
)
from tests.billing.billing_fakes import AdjustableClock
from tests.payments.stripe_requests import build_stripe_client, checkout_request
from tests.resilience.test_answered_failures import CALLS_TO_OPEN, call_repeatedly
from tests.resilience.test_circuit_breaker import Ticks

STRIPE = provider_circuit(OutboundProvider.STRIPE)
FLITT = provider_circuit(OutboundProvider.FLITT)
SUBSCRIPTION = PaymentProviderReference("sub_1Q2w3E4r5T6y7U8i")


def stripe_answering(
    status_code: int, body: dict[str, object], calls: list[str]
) -> StripeClient:
    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(status_code, json=body)

    return build_stripe_client(httpx.MockTransport(handle))


def guarded(
    client: StripeClient | None, breaker: CircuitBreakerFacilitator
) -> CircuitBreakingPaymentGatewayAdapter:
    return CircuitBreakingPaymentGatewayAdapter(
        StripeBillingAdapter(
            stripe_client=client,
            cabinet_base_url=CabinetBaseUrl("https://app.example.com"),
            wall_clock=AdjustableClock().wall_clock,
        ),
        breaker,
        STRIPE,
    )


def test_stripe_has_a_circuit_of_its_own() -> None:
    assert STRIPE in guarded_circuits()
    assert FLITT in guarded_circuits()
    assert STRIPE != FLITT


@pytest.mark.parametrize(
    ("status_code", "body", "error"),
    [
        (
            402,
            {"error": {"type": "card_error", "code": "card_declined"}},
            PaymentProviderRefusedError,
        ),
        (
            400,
            {"error": {"type": "invalid_request_error", "code": "parameter_missing"}},
            PaymentProviderRefusedError,
        ),
        (429, {"error": {"type": "rate_limit_error"}}, ProviderRateLimitedError),
    ],
)
def test_stripe_refusals_leave_the_circuit_closed(
    status_code: int, body: dict[str, object], error: type[Exception]
) -> None:
    calls: list[str] = []
    breaker = CircuitBreakerFacilitator(Ticks().clock())
    gateway = guarded(stripe_answering(status_code, body, calls), breaker)

    call_repeatedly(
        lambda: gateway.create_checkout(checkout_request(86_400)),
        error,
        CALLS_TO_OPEN + 1,
    )

    # Every call reached Stripe: it answers, so it is up.
    assert len(calls) == CALLS_TO_OPEN + 1
    assert breaker.state(STRIPE) is CircuitState.CLOSED


def test_stripe_not_set_up_leaves_the_circuit_closed() -> None:
    breaker = CircuitBreakerFacilitator(Ticks().clock())
    unconfigured = guarded(None, breaker)

    call_repeatedly(
        lambda: unconfigured.stop_recurring(PaymentProvider.STRIPE, SUBSCRIPTION),
        PaymentsNotConfiguredError,
        CALLS_TO_OPEN,
    )

    assert breaker.state(STRIPE) is CircuitState.CLOSED


def test_stripe_5xx_opens_its_circuit_and_leaves_flitt_alone() -> None:
    calls: list[str] = []
    breaker = CircuitBreakerFacilitator(Ticks().clock())
    gateway = guarded(stripe_answering(503, {}, calls), breaker)

    call_repeatedly(
        lambda: gateway.stop_recurring(PaymentProvider.STRIPE, SUBSCRIPTION),
        ExternalServiceError,
        CALLS_TO_OPEN,
    )
    with pytest.raises(ProviderCircuitOpenError):
        gateway.create_checkout(checkout_request(86_400))

    assert len(calls) == CALLS_TO_OPEN
    assert breaker.state(STRIPE) is CircuitState.OPEN
    assert breaker.state(FLITT) is CircuitState.CLOSED
