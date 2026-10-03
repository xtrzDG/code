"""Subscribing after a trial or a cancellation, refusals and the HTTP route."""

import pytest

from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    PlanKey,
    SubscriptionStatus,
)
from app.schemas.dto.billing_cabinet import CancelSubscriptionCommand
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    ValidationFailedError,
)
from tests.billing.billing_testbed import bearer
from tests.billing.subscribe_world import World


def test_subscribing_after_an_unpaid_trial_switches_plan_and_bills_from_now() -> None:
    world = World()
    world.start_trial()
    world.testbed.clock.advance(days=14, hours=1)
    world.testbed.run_job(world.testbed.end_trials, "end_trials")
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.PAST_DUE
    )

    session = world.subscribe(PlanKey.CHAT, BillingPeriod.ANNUAL)

    subscription = world.testbed.subscription(world.business.id)
    assert subscription.plan_key is PlanKey.CHAT
    assert subscription.billing_period is BillingPeriod.ANNUAL
    invoices = world.testbed.invoices(world.business.id)
    open_invoices = [
        invoice for invoice in invoices if invoice.status is InvoiceStatus.ISSUED
    ]
    assert [invoice.kind for invoice in open_invoices] == [InvoiceKind.SERVICE_PERIOD]
    assert open_invoices[0].period_start == world.testbed.clock.now()
    assert int(open_invoices[0].amount_minor) == int(subscription.price_minor)
    assert set(session.invoice_ids) == {open_invoices[0].id}
    world.pay(session)
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.ACTIVE
    )


def test_subscribing_after_the_trial_on_the_same_plan_pays_the_open_bills() -> None:
    world = World()
    world.start_trial()
    world.testbed.clock.advance(days=14, hours=1)
    world.testbed.run_job(world.testbed.end_trials, "end_trials")
    open_before = {
        invoice.id
        for invoice in world.testbed.invoices(world.business.id)
        if invoice.status is InvoiceStatus.ISSUED
    }

    session = world.subscribe()

    assert set(session.invoice_ids) == open_before
    world.pay(session)
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.ACTIVE
    )


def test_subscribing_after_cancelling_resumes_the_service() -> None:
    world = World()
    world.start_trial()
    world.testbed.cancel_subscription.run(
        CancelSubscriptionCommand(user_id=world.owner.id, business_id=world.business.id)
    )
    world.testbed.clock.advance(days=20)

    world.pay(world.subscribe())

    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.ACTIVE
    )


def test_subscribing_while_automatic_payments_run_has_nothing_to_pay() -> None:
    world = World()
    world.pay(world.subscribe())

    with pytest.raises(ConflictError):
        world.subscribe()

    assert world.testbed.flitt.stopped_orders == []


def test_a_foreign_return_page_is_refused_before_anything_changes() -> None:
    world = World()

    with pytest.raises(ValidationFailedError):
        world.subscribe(return_url="https://evil.example/billing")

    assert world.testbed.subscription_repo.list_by_business(world.business.id) == []
    assert world.testbed.flitt.checkout_orders == []


def test_staff_cannot_subscribe() -> None:
    world = World()

    with pytest.raises(AccessDeniedError):
        world.subscribe(user=world.staff)

    assert world.testbed.subscription_repo.list_by_business(world.business.id) == []


def test_subscribe_route_answers_with_the_payment_page() -> None:
    world = World()
    client = world.testbed.build_http_client()
    path = f"/v1/businesses/{world.business.id}/billing/subscribe"

    created = client.post(
        path,
        headers=bearer(world.owner),
        json={"plan_key": "plus", "billing_period": "annual"},
    )
    missing_plan = client.post(path, headers=bearer(world.owner), json={})
    staff = client.post(
        path,
        headers=bearer(world.staff),
        json={"plan_key": "plus"},
    )

    assert created.status_code == 201
    assert created.json()["checkout_url"]
    assert missing_plan.status_code == 422
    assert staff.status_code == 403
