"""The owner's billing routes and the Flitt webhook route over HTTP."""

import json
from typing import Any
from urllib.parse import urlencode

from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from tests.billing.billing_settings import CHECKOUT_URL, sign_flitt_callback
from tests.billing.billing_testbed import bearer
from tests.billing.route_world import RouteWorld

WEBHOOK_PATH: str = "/v1/payments/flitt/webhook"


def test_owner_starts_the_trial_and_reads_the_billing_page() -> None:
    world = RouteWorld()

    created = world.client.post(
        world.billing_path("/trial"), headers=bearer(world.owner)
    )
    page = world.client.get(
        world.billing_path(),
        headers=bearer(world.owner),
        params={"language": "RU"},
    )

    assert created.status_code == 201
    assert created.json()["subscription"]["status"] == "trialing"
    assert page.status_code == 200
    body: dict[str, Any] = page.json()
    assert body["display_language"] == "ru"
    assert body["currency_code"] == "GEL"
    assert body["subscription"]["plan_name"] == "Голос + чат"
    assert body["subscription"]["price"]["text"] == "517,00\xa0GEL"
    assert body["usage"]["included_voice_minutes"] == 400
    assert body["is_trial_available"] is False


def test_billing_routes_check_tokens_roles_ids_and_bodies() -> None:
    world = RouteWorld()
    world.start_trial()

    assert world.client.get(world.billing_path()).status_code == 401
    assert (
        world.client.get(world.billing_path(), headers=bearer(world.staff)).status_code
        == 403
    )
    assert (
        world.client.get(
            "/v1/businesses/not-an-id/billing",
            headers=bearer(world.owner),
        ).status_code
        == 404
    )
    assert (
        world.client.get(
            world.billing_path(),
            headers=bearer(world.owner),
            params={"language": "not a language"},
        ).status_code
        == 422
    )
    assert (
        world.client.post(
            world.billing_path("/plan"),
            headers=bearer(world.owner),
            json={"plan_key": "gold", "billing_period": "monthly"},
        ).status_code
        == 422
    )
    assert (
        world.client.post(
            world.billing_path("/plan"),
            headers=bearer(world.owner),
        ).status_code
        == 422
    )
    assert (
        world.client.post(
            world.billing_path("/trial"), headers=bearer(world.owner)
        ).status_code
        == 409
    )


def test_owner_changes_the_plan_and_cancels() -> None:
    world = RouteWorld()
    world.start_trial()

    changed = world.client.post(
        world.billing_path("/plan"),
        headers=bearer(world.owner),
        json={"plan_key": "plus", "billing_period": "annual"},
    )
    cancelled = world.client.post(
        world.billing_path("/cancel"),
        headers=bearer(world.owner),
        params={"language": "en"},
    )

    assert changed.status_code == 200
    assert changed.json()["subscription"]["price"]["money"] == {
        "amount_minor": 1051620,
        "currency_code": "GEL",
    }
    assert cancelled.status_code == 200
    assert cancelled.json()["subscription"]["status"] == "cancelled"
    assert cancelled.json()["subscription"]["plan_name"] == "Plus"


def test_checkout_returns_the_payment_page() -> None:
    world = RouteWorld()
    world.start_trial()

    response = world.client.post(
        world.billing_path("/checkout"),
        headers=bearer(world.owner),
    )
    refused = world.client.post(
        world.billing_path("/checkout"),
        headers=bearer(world.owner),
        json={"return_url": "https://evil.example/billing"},
    )

    assert response.status_code == 201
    assert response.json()["checkout_url"] == CHECKOUT_URL
    assert response.json()["amount"]["text"] == "960,00\xa0₾"
    assert refused.status_code == 422


def test_flitt_webhook_applies_payments_once() -> None:
    world = RouteWorld()
    world.start_trial()
    order = world.checkout()
    body: str = json.dumps(
        sign_flitt_callback(world.testbed.callback_parameters(order, "approved"))
    )

    first = world.client.post(
        WEBHOOK_PATH,
        content=body,
        headers={"Content-Type": "application/json"},
    )
    second = world.client.post(
        WEBHOOK_PATH,
        content=body,
        headers={"Content-Type": "application/json"},
    )

    assert first.status_code == 200
    assert first.json() == {"outcome": "applied", "payment_order_id": str(order.id)}
    assert second.status_code == 200
    assert second.json()["outcome"] == "duplicate"
    page = world.client.get(world.billing_path(), headers=bearer(world.owner))
    assert page.json()["subscription"]["has_auto_debit"] is True
    assert {invoice["status"] for invoice in page.json()["invoices"]} == {"paid"}


def test_flitt_webhook_accepts_form_posts() -> None:
    world = RouteWorld()
    world.start_trial()
    order = world.checkout()
    parameters = sign_flitt_callback(
        world.testbed.callback_parameters(order, "declined")
    )

    response = world.client.post(
        WEBHOOK_PATH,
        content=urlencode({key: str(value) for key, value in parameters.items()}),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "applied"


def test_flitt_webhook_rejects_bad_notifications() -> None:
    world = RouteWorld()
    world.start_trial()
    order = world.checkout()
    parameters = world.testbed.callback_parameters(order, "approved")
    unknown = sign_flitt_callback(
        {**parameters, "order_id": str(PaymentOrderId()), "merchant_data": ""}
    )

    forged = world.client.post(
        WEBHOOK_PATH,
        json={**parameters, "signature": "0" * 40},
    )
    missing = world.client.post(WEBHOOK_PATH, json=unknown)
    not_utf8 = world.client.post(
        WEBHOOK_PATH,
        content=b"\xff\xfe",
        headers={"Content-Type": "application/json"},
    )
    empty = world.client.post(WEBHOOK_PATH)

    assert forged.status_code == 403
    assert missing.status_code == 404
    assert not_utf8.status_code == 422
    assert empty.status_code == 422
