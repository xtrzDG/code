"""
Stripe's events (API version 2024-06-20, the version every webhook
endpoint and request is pinned to), shaped as Stripe documents them, go
through the real client and adapter: the signature is checked as Stripe
signs, each event says what the billing flow needs, an event the platform
does not use is ignored, and Stripe's answers and errors read as expected.
"""

import json
from typing import Any

import httpx
import pytest
from typed_time_provider import Microseconds

from app.adapters.payments.stripe_billing_adapter import (
    StripeBillingAdapter,
    read_page_url,
)
from app.clients.stripe.stripe_client import (
    StripeCardDeclinedError,
    StripeClient,
    read_response,
)
from app.clients.stripe.stripe_protocol import verify_signature
from app.schemas.constants.payments import PaymentProvider, PaymentStatus
from app.schemas.dto.payments import PaymentWebhookDelivery, VerifiedPaymentEvent
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.billing.strings import (
    PaymentWebhookBody,
    PaymentWebhookSignature,
)
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.schemas.typings.platform.strings import PlatformSecret
from tests.billing.billing_fakes import AdjustableClock
from tests.billing.billing_settings import (
    CABINET_ORIGIN,
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
)
from tests.billing.stripe_sandbox import StripeSandbox, sign_stripe_event
from tests.contracts.contract_files import load_json_fixture

ORDER_ID: str = "payment_order_7d3c1f9e-2b4a-4c8e-9f10-000000000001"


def read_event(name: str) -> VerifiedPaymentEvent:
    """The fixture event, signed now, through the adapter."""

    sandbox = StripeSandbox(
        payment_method=load_json_fixture("stripe", "payment_method_card.json")
    )
    clock = AdjustableClock()
    adapter = StripeBillingAdapter(
        stripe_client=StripeClient(
            secret_key=PlatformSecret(STRIPE_SECRET_KEY),
            webhook_secret=PlatformSecret(STRIPE_WEBHOOK_SECRET),
            transport=httpx.MockTransport(sandbox.handle),
        ),
        cabinet_base_url=CabinetBaseUrl(CABINET_ORIGIN),
        wall_clock=clock.wall_clock,
    )
    payload: str = json.dumps(load_json_fixture("stripe", name))
    now: int = int(clock.now()) // 1_000_000
    return adapter.read_notification(
        PaymentWebhookDelivery(
            body=PaymentWebhookBody(payload),
            provider=PaymentProvider.STRIPE,
            signature=PaymentWebhookSignature(sign_stripe_event(payload, now)),
        )
    )


def test_the_signature_follows_stripes_scheme() -> None:
    example: dict[str, Any] = load_json_fixture("stripe", "signature_example.json")

    verify_signature(
        example["payload"], example["header"], example["secret"], example["timestamp"]
    )

    with pytest.raises(AccessDeniedError):
        verify_signature(
            example["payload"] + " ",
            example["header"],
            example["secret"],
            example["timestamp"],
        )


def test_a_completed_session_pays_and_saves_the_card() -> None:
    event = read_event("event_checkout_session_completed.json")

    assert event.payment is not None
    assert str(event.payment.order_reference) == ORDER_ID
    assert event.payment.status is PaymentStatus.APPROVED
    assert str(event.payment.payment_reference) == "in_test_0001"
    assert event.payment.amount is not None
    assert int(event.payment.amount.amount_minor) == 31900
    assert str(event.payment.amount.currency_code) == "EUR"
    card = event.payment_method
    assert card is not None
    assert str(card.schedule_reference) == "sub_test_0001"
    assert str(card.customer_reference) == "cus_test_0001"
    assert card.summary is not None
    assert str(card.summary.last_digits) == "4444"
    assert card.summary.saved_at == Microseconds(1_792_479_600_000_000)


@pytest.mark.parametrize(
    ("name", "status", "is_retry"),
    [
        ("event_invoice_paid.json", PaymentStatus.APPROVED, False),
        ("event_invoice_payment_failed.json", PaymentStatus.DECLINED, True),
    ],
)
def test_invoices_of_later_periods_are_automatic_charges(
    name: str, status: PaymentStatus, is_retry: bool
) -> None:
    event = read_event(name)

    assert event.payment_method is None
    assert event.payment is not None
    assert str(event.payment.parent_order_reference) == ORDER_ID
    assert event.payment.status is status
    assert event.payment.is_retry is is_retry
    assert event.payment.amount is not None
    assert int(event.payment.amount.amount_minor) == 17500


def test_a_new_default_card_replaces_the_card_on_file() -> None:
    event = read_event("event_customer_subscription_updated.json")

    assert event.payment is None
    assert event.payment_method is not None
    summary = event.payment_method.summary
    assert summary is not None
    assert (str(summary.brand), str(summary.last_digits)) == ("MASTERCARD", "4444")
    assert (int(summary.expiry_month or 0), int(summary.expiry_year or 0)) == (
        4,
        2031,
    )


def test_an_event_the_platform_does_not_use_is_ignored() -> None:
    event = read_event("event_unknown_type.json")

    assert event.payment is None
    assert event.payment_method is None


def test_stripes_answers_and_errors_read_as_documented() -> None:
    session: dict[str, object] = read_response(
        httpx.Response(
            200, json=load_json_fixture("stripe", "checkout_session_response.json")
        )
    )

    assert str(read_page_url(session)) == (
        "https://checkout.stripe.com/c/pay/cs_test_0001"
    )
    with pytest.raises(StripeCardDeclinedError) as declined:
        read_response(
            httpx.Response(
                402, json=load_json_fixture("stripe", "error_card_declined.json")
            )
        )
    assert declined.value.decline_code == "insufficient_funds"
    assert "Your card" not in str(declined.value)
