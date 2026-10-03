"""Changing the plan or the billing period, and cancelling during the trial."""

import pytest

from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    PlanKey,
    SubscriptionStatus,
)
from app.schemas.dto.billing_cabinet import (
    CancelSubscriptionCommand,
    StartCheckoutCommand,
    StartCheckoutRequest,
)
from app.schemas.exceptions.application_errors import NotFoundError
from tests.billing.billing_settings import GEORGIA, ITALY
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.plan_steps import change_plan, start_trial


def test_change_plan_during_the_trial_reprices_at_once() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(phone_number="+995599123456")
    business = testbed.add_business(owner, GEORGIA)
    start_trial(testbed, owner, business)

    overview = change_plan(
        testbed,
        owner,
        business,
        PlanKey.PLUS,
        BillingPeriod.ANNUAL,
    )

    assert overview.subscription is not None
    assert overview.subscription.plan_key is PlanKey.PLUS
    assert overview.subscription.status is SubscriptionStatus.TRIALING
    assert int(overview.subscription.price.money.amount_minor) == 1051620
    assert overview.usage is not None
    assert int(overview.usage.included_voice_minutes) == 1000
    assert testbed.business(business.id).plan_key is PlanKey.PLUS
    assert testbed.flitt.stopped_orders == []


def test_moving_to_a_plan_without_voice_switches_the_voice_agent_off() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(phone_number="+995599123456")
    business = testbed.add_business(owner, GEORGIA)
    start_trial(testbed, owner, business)

    change_plan(testbed, owner, business, PlanKey.PLUS, BillingPeriod.MONTHLY)
    assert testbed.voice_agent_removals.business_ids == []
    change_plan(testbed, owner, business, PlanKey.CHAT, BillingPeriod.MONTHLY)

    assert testbed.voice_agent_removals.business_ids == [business.id]


def test_changing_to_the_same_plan_changes_nothing() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(phone_number="+995599123456")
    business = testbed.add_business(owner, GEORGIA)
    start_trial(testbed, owner, business)
    before = testbed.subscription(business.id)

    change_plan(
        testbed,
        owner,
        business,
        PlanKey.VOICE_AND_CHAT,
        BillingPeriod.MONTHLY,
    )

    assert testbed.subscription(business.id) == before


def test_plan_changes_need_a_subscription_and_a_price() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(email="owner@example.com")
    business = testbed.add_business(owner, ITALY)

    with pytest.raises(NotFoundError):
        change_plan(testbed, owner, business, PlanKey.PLUS, BillingPeriod.MONTHLY)

    with pytest.raises(NotFoundError):
        testbed.cancel_subscription.run(
            CancelSubscriptionCommand(user_id=owner.id, business_id=business.id)
        )


def test_cancel_ends_the_trial_at_its_end_and_is_idempotent() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(email="owner@example.com")
    business = testbed.add_business(owner, ITALY)
    start_trial(testbed, owner, business)
    command = CancelSubscriptionCommand(user_id=owner.id, business_id=business.id)

    first = testbed.cancel_subscription.run(command)
    second = testbed.cancel_subscription.run(command)

    assert first.subscription is not None
    assert first.subscription.status is SubscriptionStatus.CANCELLED
    assert second == first
    assert all(
        invoice.status is InvoiceStatus.VOID
        for invoice in testbed.invoices(business.id)
    )


def test_switching_from_paid_annual_to_monthly_bills_no_setup_fee() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(phone_number="+995599123456", locale="ka")
    business = testbed.add_business(owner, GEORGIA)
    start_trial(testbed, owner, business, billing_period=BillingPeriod.ANNUAL)
    first = testbed.start_checkout.run(
        StartCheckoutCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartCheckoutRequest(),
        )
    )
    order = testbed.payment_order_repo.get(first.payment_order_id)
    assert order is not None
    testbed.deliver_flitt_callback(testbed.callback_parameters(order, "approved"))
    testbed.clock.advance(days=300)

    change_plan(testbed, owner, business, PlanKey.VOICE_AND_CHAT, BillingPeriod.MONTHLY)
    session = testbed.start_checkout.run(
        StartCheckoutCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartCheckoutRequest(),
        )
    )

    assert session.amount.text == "517,00\xa0₾"
    assert all(
        invoice.kind is not InvoiceKind.SETUP_FEE
        for invoice in testbed.invoices(business.id)
    )
