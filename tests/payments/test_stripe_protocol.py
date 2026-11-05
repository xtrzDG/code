"""Stripe's wire protocol, its client and the hosted-page parameters."""

import httpx
import pytest

from app.adapters.payments.stripe_cards import read_stripe_card
from app.adapters.payments.stripe_checkout_parameters import (
    build_checkout_parameters,
    recurring_interval,
    schedule_start,
    select_checkout_language,
)
from app.clients.stripe.stripe_client import (
    StripeCardDeclinedError,
    StripeClient,
    StripeNotFoundError,
)
from app.clients.stripe.stripe_protocol import encode_form, parse_event, read_error
from app.schemas.constants.payments import (
    PaymentOrderPurpose,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ExternalServiceError,
    ValidationFailedError,
)
from tests.billing.billing_settings import (
    CABINET_ORIGIN,
)
from tests.billing.stripe_sandbox import sign_stripe_event, stripe_event
from tests.payments.stripe_requests import (
    DAY_SECONDS,
    NOW_SECONDS,
    build_stripe_client,
    checkout_request,
)


def test_nested_parameters_are_form_encoded_like_stripe_expects() -> None:
    assert encode_form(
        {
            "mode": "subscription",
            "line_items": [{"quantity": 1, "price_data": {"unit_amount": 500}}],
            "expand": ["default_payment_method"],
            "flag": True,
        }
    ) == [
        ("mode", "subscription"),
        ("line_items[0][quantity]", "1"),
        ("line_items[0][price_data][unit_amount]", "500"),
        ("expand[0]", "default_payment_method"),
        ("flag", "true"),
    ]


def test_a_card_setup_charges_nothing_now() -> None:
    form = build_checkout_parameters(
        checkout_request(30 * DAY_SECONDS, PaymentOrderPurpose.CARD_SETUP),
        f"{CABINET_ORIGIN}/",
        NOW_SECONDS,
    )

    line_items = form["line_items"]
    assert isinstance(line_items, list)
    assert len(line_items) == 1
    assert form["locale"] == "de"
    assert form["subscription_data"] == {
        "metadata": {"payment_order_id": form["client_reference_id"]},
        "trial_end": NOW_SECONDS + 30 * DAY_SECONDS,
    }


def test_a_near_start_anchors_the_cycle_instead_of_a_trial() -> None:
    assert schedule_start(NOW_SECONDS + DAY_SECONDS, NOW_SECONDS) == {
        "billing_cycle_anchor": NOW_SECONDS + DAY_SECONDS,
        "proration_behavior": "none",
    }
    assert schedule_start(NOW_SECONDS - 10, NOW_SECONDS) == {
        "billing_cycle_anchor": NOW_SECONDS + 60,
        "proration_behavior": "none",
    }
    assert schedule_start(NOW_SECONDS + 2 * DAY_SECONDS, NOW_SECONDS) == {
        "trial_end": NOW_SECONDS + 2 * DAY_SECONDS
    }


def test_intervals_and_languages() -> None:
    assert recurring_interval(12) == {"interval": "year", "interval_count": 1}
    assert recurring_interval(3) == {"interval": "month", "interval_count": 3}
    assert select_checkout_language("ka-GE") == "auto"
    assert select_checkout_language("he") == "auto"
    assert select_checkout_language("ru") == "ru"


def test_a_card_payment_method_is_summarised() -> None:
    summary = read_stripe_card(
        {"card": {"brand": "amex", "last4": "0005", "exp_month": 13, "exp_year": 2031}},
        NOW_SECONDS,
    )

    assert summary is not None
    assert str(summary.brand) == "AMEX"
    assert summary.expiry_month is None
    assert summary.expiry_year is not None
    assert int(summary.saved_at) == NOW_SECONDS * 1_000_000
    assert read_stripe_card("pm_test_0001", NOW_SECONDS) is None
    assert read_stripe_card({"type": "sepa_debit"}, NOW_SECONDS) is None


def test_the_client_reports_declines_missing_objects_and_failures() -> None:
    def answer(status: int, body: object) -> StripeClient:
        return build_stripe_client(
            httpx.MockTransport(lambda _: httpx.Response(status, json=body))
        )

    with pytest.raises(StripeCardDeclinedError) as declined:
        answer(
            402, {"error": {"type": "card_error", "code": "expired_card"}}
        ).pay_invoice("in_test_0001", "retry:1")
    assert declined.value.decline_code == "expired_card"

    with pytest.raises(StripeNotFoundError):
        answer(
            404, {"error": {"type": "invalid_request_error"}}
        ).retrieve_payment_method("pm_test_0009")

    answer(404, {"error": {"type": "invalid_request_error"}}).cancel_subscription(
        "sub_gone"
    )

    with pytest.raises(ExternalServiceError):
        answer(500, None).retrieve_subscription("sub_test_0001")

    with pytest.raises(ExternalServiceError):
        answer(200, ["not", "an", "object"]).retrieve_subscription("sub_test_0001")

    def unreachable(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route")

    with pytest.raises(ExternalServiceError):
        build_stripe_client(httpx.MockTransport(unreachable)).cancel_subscription(
            "sub_test_0001"
        )

    assert read_error({"error": "text"}) == ("unknown", "unknown")
    assert read_error(None) == ("unknown", "unknown")


def test_webhook_payloads_must_be_events() -> None:
    with pytest.raises(ValidationFailedError):
        parse_event("[]")

    with pytest.raises(ValidationFailedError):
        parse_event('{"type": "invoice.paid", "data": {}}')

    with pytest.raises(ValidationFailedError):
        parse_event("{")

    client = build_stripe_client()
    payload = stripe_event("invoice.paid", "evt_1", {"id": "in_1"}, NOW_SECONDS)

    with pytest.raises(AccessDeniedError):
        client.verify_webhook(payload, "v1=abc", NOW_SECONDS)

    with pytest.raises(AccessDeniedError):
        client.verify_webhook(
            payload, sign_stripe_event(payload, NOW_SECONDS + 301), NOW_SECONDS
        )

    assert client.verify_webhook(
        payload, sign_stripe_event(payload, NOW_SECONDS), NOW_SECONDS
    )["id"] == ("evt_1")
