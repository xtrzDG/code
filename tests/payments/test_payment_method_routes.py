"""The card on file routes and the Stripe webhook route over HTTP."""

import pytest

from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from tests.billing.billing_settings import CABINET_ORIGIN, CHECKOUT_URL
from tests.billing.billing_testbed import bearer
from tests.billing.route_world import RouteWorld
from tests.billing.stripe_sandbox import sign_stripe_event, stripe_event
from tests.payments.payment_world import stripe_session

STRIPE_WEBHOOK_PATH: str = "/v1/payments/stripe/webhook"


def card_path(world: RouteWorld) -> str:
    return world.billing_path("/payment-method")


def test_the_owner_reads_and_saves_the_card_on_file() -> None:
    world = RouteWorld()
    world.start_trial()

    read = world.client.get(card_path(world), headers=bearer(world.owner))
    saved = world.client.post(
        card_path(world),
        headers=bearer(world.owner),
        json={"return_url": f"{CABINET_ORIGIN}/billing"},
        params={"language": "ru"},
    )

    assert read.status_code == 200
    assert read.json() == {
        "provider": "flitt",
        "card": None,
        "has_auto_debit": False,
        "can_save_card": True,
        "trial_ends_at": read.json()["trial_ends_at"],
        "is_trial_card_prompt_due": False,
        "retry": None,
        "setup_fee_due": {"amount_minor": 44300, "currency_code": "GEL"},
    }
    assert isinstance(read.json()["trial_ends_at"], int)
    assert saved.status_code == 201
    assert saved.json()["provider"] == "flitt"
    assert saved.json()["url"] == CHECKOUT_URL
    order = world.testbed.payment_order_repo.get(
        PaymentOrderId(saved.json()["payment_order_id"])
    )
    assert order is not None
    assert world.testbed.flitt.checkout_orders[-1]["lang"] == "ru"
    assert world.testbed.flitt.checkout_orders[-1]["response_url"] == (
        f"{CABINET_ORIGIN}/billing"
    )


def test_the_card_routes_check_tokens_roles_and_state() -> None:
    world = RouteWorld()

    assert world.client.get(card_path(world)).status_code == 401
    assert (
        world.client.get(card_path(world), headers=bearer(world.staff)).status_code
        == 403
    )
    assert (
        world.client.post(card_path(world), headers=bearer(world.staff)).status_code
        == 403
    )
    assert (
        world.client.post(card_path(world), headers=bearer(world.owner)).status_code
        == 404
    )
    world.start_trial()
    assert (
        world.client.post(
            card_path(world),
            headers=bearer(world.owner),
            json={"return_url": "https://evil.example/billing"},
        ).status_code
        == 422
    )
    world.testbed.clock.advance(days=14, hours=1)
    world.testbed.run_job(world.testbed.end_trials, "end_trials")
    assert (
        world.client.post(card_path(world), headers=bearer(world.owner)).status_code
        == 409
    )
    assert world.testbed.flitt.checkout_orders == []


@pytest.mark.usefixtures("stripe_gate_open")
def test_a_signed_stripe_event_is_applied_over_http() -> None:
    world = RouteWorld()
    world.start_trial()
    order = world.checkout()
    now = int(world.testbed.clock.now()) // 1_000_000
    payload = stripe_event(
        "checkout.session.completed", "evt_test_0100", stripe_session(order), now
    )

    unsigned = world.client.post(
        STRIPE_WEBHOOK_PATH,
        content=payload,
        headers={"Content-Type": "application/json"},
    )
    forged = world.client.post(
        STRIPE_WEBHOOK_PATH,
        content=payload,
        headers={"Stripe-Signature": f"t={now},v1=0000"},
    )
    applied = world.client.post(
        STRIPE_WEBHOOK_PATH,
        content=payload,
        headers={"Stripe-Signature": sign_stripe_event(payload, now)},
    )
    repeated = world.client.post(
        STRIPE_WEBHOOK_PATH,
        content=payload,
        headers={"Stripe-Signature": sign_stripe_event(payload, now)},
    )
    malformed = world.client.post(
        STRIPE_WEBHOOK_PATH,
        content="not json",
        headers={"Stripe-Signature": sign_stripe_event("not json", now)},
    )

    assert unsigned.status_code == 403
    assert forged.status_code == 403
    assert applied.status_code == 200
    assert applied.json() == {
        "outcome": "applied",
        "payment_order_id": str(order.id),
    }
    assert repeated.json()["outcome"] == "duplicate"
    assert malformed.status_code == 422


def test_a_stripe_event_for_an_unknown_order_is_not_found() -> None:
    world = RouteWorld()
    now = int(world.testbed.clock.now()) // 1_000_000
    payload = stripe_event(
        "checkout.session.completed",
        "evt_test_0101",
        {
            "id": "cs_test_0000",
            "metadata": {
                "payment_order_id": "payment_order_00000000-0000-4000-8000-000000000000"
            },
            "payment_status": "paid",
            "amount_total": 100,
            "currency": "eur",
        },
        now,
    )

    response = world.client.post(
        STRIPE_WEBHOOK_PATH,
        content=payload,
        headers={"Stripe-Signature": sign_stripe_event(payload, now)},
    )

    assert response.status_code == 404
