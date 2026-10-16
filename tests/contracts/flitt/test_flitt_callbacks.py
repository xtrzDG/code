"""
Flitt payment callbacks, signed as Flitt documents it: every documented
callback matches the callback shape and verifies as recorded, the adapter
reads the payment the billing flow needs, and the webhook route applies a
callback in every encoding Flitt uses. A status Flitt may add later is
refused with 422 and changes nothing, never a 500.
"""

import json
from typing import Any
from urllib.parse import urlencode

import pytest

from app.adapters.payments.flitt_payment_gateway_adapter import (
    FlittPaymentGatewayAdapter,
)
from app.clients.flitt.flitt_protocol import build_parameter_signature
from app.schemas.dto.payments import PaymentWebhookDelivery
from app.schemas.typings.billing.strings import (
    PaymentWebhookBody,
    PaymentWebhookContentType,
)
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from tests.billing.billing_settings import APP_BASE_URL
from tests.billing.billing_testbed import bearer
from tests.billing.flitt_test_clients import build_client
from tests.billing.route_world import RouteWorld
from tests.contracts.contract_files import load_json_fixture, read_fixture_bytes
from tests.contracts.flitt.flitt_signing import envelope, signed
from tests.contracts.vendor_schemas import assert_inbound

SPEC: str = "flitt_api.json"
WEBHOOK_PATH: str = "/v1/payments/flitt/webhook"
DOCUMENTED_CALLBACKS: list[str] = [
    "callback_approved.json",
    "callback_declined.json",
    "callback_subscription_charge.json",
]


def adapter() -> FlittPaymentGatewayAdapter:
    return FlittPaymentGatewayAdapter(
        flitt_client=build_client(), app_base_url=PublicBaseUrl(APP_BASE_URL)
    )


def test_signatures_follow_the_documented_example() -> None:
    example: dict[str, Any] = load_json_fixture("flitt", "signature_example.json")

    assert (
        build_parameter_signature(example["secret_key"], example["parameters"])
        == example["signature"]
    )


@pytest.mark.parametrize("fixture", DOCUMENTED_CALLBACKS)
def test_callbacks_match_the_documented_shape(fixture: str) -> None:
    assert_inbound(load_json_fixture("flitt", fixture), SPEC, "Callback")


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        (
            "callback_approved.json",
            {"status": "approved", "parent": None, "amount": 96000, "reason": None},
        ),
        (
            "callback_declined.json",
            {
                "status": "declined",
                "parent": None,
                "amount": 96000,
                "reason": "Declined by issuer",
            },
        ),
        (
            "callback_subscription_charge.json",
            {
                "status": "approved",
                "parent": "payment_order_contract_0001",
                "amount": 51700,
                "reason": None,
            },
        ),
    ],
)
def test_recorded_callbacks_verify_and_are_read(
    fixture: str, expected: dict[str, Any]
) -> None:
    notification = adapter().read_notification(
        PaymentWebhookDelivery(
            body=PaymentWebhookBody(read_fixture_bytes("flitt", fixture).decode()),
            content_type=PaymentWebhookContentType("application/json"),
        )
    )

    read: dict[str, Any] = notification.model_dump(mode="json")
    assert {
        "status": read["status"],
        "parent": read["parent_order_reference"],
        "amount": read["amount"]["amount_minor"],
        "reason": read["failure_reason"],
    } == expected
    assert read["amount"]["currency_code"] == "GEL"
    assert read["card"] == {"brand": "VISA", "last_digits": "1111"}


def world_callback(world: RouteWorld, fixture: str) -> dict[str, Any]:
    """The fixture as Flitt would send it for the world's payment order."""

    order = world.checkout()
    return signed(
        {
            **load_json_fixture("flitt", fixture),
            "order_id": str(order.id),
            "merchant_data": str(order.id),
            "amount": str(int(order.amount_minor)),
            "actual_amount": str(int(order.amount_minor)),
            "currency": str(order.currency_code),
        }
    )


def post_json(world: RouteWorld, body: dict[str, Any]) -> Any:
    return world.client.post(
        WEBHOOK_PATH,
        content=json.dumps(body),
        headers={"Content-Type": "application/json"},
    )


@pytest.mark.parametrize("encoding", ["json", "form", "envelope"])
def test_approved_callback_pays_the_invoices_in_every_encoding(encoding: str) -> None:
    world = RouteWorld()
    world.start_trial()
    callback: dict[str, Any] = world_callback(world, "callback_approved.json")

    if encoding == "form":
        response = world.client.post(
            WEBHOOK_PATH,
            content=urlencode({name: str(value) for name, value in callback.items()}),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    else:
        response = post_json(
            world, envelope(callback) if encoding == "envelope" else callback
        )

    assert response.status_code == 200, response.text
    assert response.json()["outcome"] == "applied"
    page = world.client.get(world.billing_path(), headers=bearer(world.owner))
    assert {invoice["status"] for invoice in page.json()["invoices"]} == {"paid"}


def test_declined_callback_leaves_the_invoices_open() -> None:
    world = RouteWorld()
    world.start_trial()

    response = post_json(world, world_callback(world, "callback_declined.json"))

    assert response.status_code == 200, response.text
    assert response.json()["outcome"] == "applied"
    page = world.client.get(world.billing_path(), headers=bearer(world.owner))
    assert "paid" not in {invoice["status"] for invoice in page.json()["invoices"]}


def test_a_status_flitt_may_add_is_refused_without_a_server_error() -> None:
    world = RouteWorld()
    world.start_trial()

    response = post_json(world, world_callback(world, "callback_unknown_status.json"))

    assert response.status_code == 422
    page = world.client.get(world.billing_path(), headers=bearer(world.owner))
    assert "paid" not in {invoice["status"] for invoice in page.json()["invoices"]}
