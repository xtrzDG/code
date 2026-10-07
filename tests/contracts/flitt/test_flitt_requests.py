"""
What the platform sends to Flitt (a subscription checkout, stopping the
automatic charges) matches the documented protocol 2.0 request with every
object closed, its signature is the documented one, and Flitt's documented
answers are read as the billing flow expects.
"""

from typing import Any

import pytest

from app.adapters.payments.flitt_payment_gateway_adapter import (
    FlittPaymentGatewayAdapter,
)
from app.clients.flitt.flitt_client import FlittClient
from app.schemas.dto.billing import Money
from app.schemas.dto.payments import PaymentCheckoutRequest, RecurringCharge
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.billing.constrained_integers import (
    BillingIntervalMonths,
    MoneyAmountMinor,
)
from app.schemas.typings.billing.constrained_strings import (
    AutoDebitStartDate,
    PaymentReturnUrl,
)
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.billing.strings import (
    InvoiceDescription,
    PaymentProviderReference,
)
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from tests.billing.billing_settings import APP_BASE_URL, FLITT_MERCHANT_ID
from tests.channels.recording_transport import RecordingTransport
from tests.contracts.contract_files import load_json_fixture
from tests.contracts.flitt.flitt_signing import TEST_SECRET, opened
from tests.contracts.vendor_schemas import assert_inbound, assert_outbound

SPEC: str = "flitt_api.json"


def gateway(transport: RecordingTransport) -> FlittPaymentGatewayAdapter:
    client = FlittClient(
        merchant_id=PlatformIdentifier(FLITT_MERCHANT_ID),
        secret_key=PlatformSecret(TEST_SECRET),
        transport=transport.build(),
    )
    return FlittPaymentGatewayAdapter(
        flitt_client=client, app_base_url=PublicBaseUrl(APP_BASE_URL)
    )


def checkout_request() -> PaymentCheckoutRequest:
    gel = CurrencyCode("GEL")
    return PaymentCheckoutRequest(
        payment_order_id=PaymentOrderId(),
        amount=Money(amount_minor=MoneyAmountMinor(96000), currency_code=gel),
        description=InvoiceDescription("Call and message handling service"),
        recurring_charge=RecurringCharge(
            amount=Money(amount_minor=MoneyAmountMinor(51700), currency_code=gel),
            interval_months=BillingIntervalMonths(1),
            start_date=AutoDebitStartDate("2026-11-15"),
        ),
        language=LanguageTag("ka"),
        return_url=PaymentReturnUrl("https://app.assistant.example/billing"),
    )


@pytest.mark.parametrize(
    "fixture",
    [
        "checkout_url_response.json",
        "checkout_url_envelope_response.json",
        "checkout_failure_response.json",
        "subscription_stop_response.json",
    ],
)
def test_documented_answers_match_the_protocol(fixture: str) -> None:
    assert_inbound(load_json_fixture("flitt", fixture), SPEC, "response:api")


def test_checkout_request_matches_the_protocol() -> None:
    transport = RecordingTransport()
    transport.respond(
        "POST",
        r"/api/checkout/url/$",
        load_json_fixture("flitt", "checkout_url_response.json"),
    )

    session = gateway(transport).create_checkout(checkout_request())

    [request] = transport.requests
    assert_outbound(request.json(), SPEC, "request:api")
    assert_outbound(opened(request.json()), SPEC, "CheckoutOrder")
    assert str(session.checkout_url).startswith("https://pay.flitt.com/")
    assert session.payment_reference == "802345671"


def test_a_signed_checkout_answer_without_a_status_is_read() -> None:
    # Flitt's live test merchant answers the checkout with a signed 2.0
    # envelope holding only checkout_url and payment_id (no
    # response_status); field names seen in the nightly run of 2026-10-07.
    transport = RecordingTransport()
    transport.respond(
        "POST",
        r"/api/checkout/url/$",
        load_json_fixture("flitt", "checkout_url_envelope_response.json"),
    )

    session = gateway(transport).create_checkout(checkout_request())

    assert str(session.checkout_url).startswith("https://pay.flitt.com/")
    assert session.payment_reference == "802345671"


def test_stopping_the_charges_matches_the_protocol() -> None:
    transport = RecordingTransport()
    transport.respond(
        "POST",
        r"/api/subscription/$",
        load_json_fixture("flitt", "subscription_stop_response.json"),
    )

    gateway(transport).stop_recurring(PaymentProviderReference("payment_order_1"))

    [request] = transport.requests
    assert_outbound(request.json(), SPEC, "request:api")
    order: dict[str, Any] = opened(request.json())
    assert_outbound(order, SPEC, "SubscriptionOrder")
    assert order["action"] == "stop"


def test_a_documented_refusal_names_flitt_s_code() -> None:
    transport = RecordingTransport()
    transport.respond(
        "POST",
        r"/api/checkout/url/$",
        load_json_fixture("flitt", "checkout_failure_response.json"),
    )

    with pytest.raises(ExternalServiceError) as raised:
        gateway(transport).create_checkout(checkout_request())

    assert "code 1013" in str(raised.value)
