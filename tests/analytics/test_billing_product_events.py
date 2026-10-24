"""The billing steps report their product events with the monthly amount."""

from app.schemas.constants.analytics import ProductEventName
from app.schemas.constants.billing import BillingPeriod, PlanKey, SubscriptionStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_cabinet import (
    CancelSubscriptionCommand,
    StartCheckoutCommand,
    StartCheckoutRequest,
)
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.grace_steps import end_trial, pay_open_invoices, start_trial
from tests.billing.paid_world import build_active_subscription
from tests.billing.plan_steps import change_plan


def test_starting_the_trial_reports_it_with_its_end_and_price() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed)

    [trial] = testbed.product_events.named(ProductEventName.TRIAL_STARTED)
    subscription = testbed.subscription(business.id)
    assert trial.user_id == owner.id
    assert trial.business_id == business.id
    assert trial.properties.trial_ends_at == subscription.trial_ends_at
    assert trial.properties.monthly_amount == int(subscription.price_minor)
    assert trial.properties.currency_code == subscription.currency_code
    assert trial.properties.plan_key is subscription.plan_key


def test_a_trial_paid_ahead_subscribes_when_it_ends_not_when_paid() -> None:
    world, _ = build_active_subscription()
    events = world.testbed.product_events

    [subscribed] = events.named(ProductEventName.SUBSCRIBED)
    assert subscribed.business_id == world.business.id
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.ACTIVE
    )
    assert events.names().index(ProductEventName.TRIAL_STARTED) < events.names().index(
        ProductEventName.SUBSCRIBED
    )


def test_paying_after_an_unpaid_trial_subscribes_through_the_webhook() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed)
    testbed.clock.advance(days=14, hours=1)
    end_trial(testbed)
    assert testbed.product_events.named(ProductEventName.SUBSCRIBED) == []

    pay_open_invoices(testbed, owner, business)

    [subscribed] = testbed.product_events.named(ProductEventName.SUBSCRIBED)
    assert subscribed.business_id == business.id
    assert subscribed.user_id is None


def test_a_renewal_of_an_active_subscription_is_not_a_new_subscription() -> None:
    world, order = build_active_subscription()
    period_end = world.testbed.subscription(world.business.id).period_end
    world.testbed.clock.move_to(period_end)
    world.testbed.clock.advance(hours=2)

    world.testbed.deliver_flitt_callback(
        {
            **world.testbed.callback_parameters(
                order, "approved", payment_id=2, amount=51700
            ),
            "order_id": f"{order.id}_2",
            "parent_order_id": str(order.id),
        }
    )

    assert len(world.testbed.product_events.named(ProductEventName.SUBSCRIBED)) == 1


def test_a_declined_checkout_is_a_failed_payment() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed)
    testbed.clock.advance(days=14, hours=1)
    end_trial(testbed)
    session = checkout_for(testbed, owner, business)
    order = testbed.payment_order_repo.get(session)
    assert order is not None

    testbed.deliver_flitt_callback(testbed.callback_parameters(order, "declined"))

    [failed] = testbed.product_events.named(ProductEventName.PAYMENT_FAILED)
    assert failed.business_id == business.id


def test_a_plan_change_names_the_plan_before_and_spreads_an_annual_price() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed)
    before = testbed.subscription(business.id).plan_key

    change_plan(testbed, owner, business, PlanKey.PLUS, BillingPeriod.ANNUAL)

    [changed] = testbed.product_events.named(ProductEventName.PLAN_CHANGED)
    subscription = testbed.subscription(business.id)
    assert changed.user_id == owner.id
    assert changed.properties.previous_plan_key is before
    assert changed.properties.plan_key is PlanKey.PLUS
    assert changed.properties.billing_period is BillingPeriod.ANNUAL
    assert changed.properties.monthly_amount == round(
        int(subscription.price_minor) / 12
    )


def test_cancelling_twice_reports_one_cancellation() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed)
    command = CancelSubscriptionCommand(user_id=owner.id, business_id=business.id)

    testbed.cancel_subscription.run(command)
    testbed.cancel_subscription.run(command)

    [cancelled] = testbed.product_events.named(ProductEventName.CANCELLED)
    assert cancelled.user_id == owner.id
    assert cancelled.business_id == business.id


def checkout_for(
    testbed: BillingTestbed, owner: UserDocument, business: BusinessDocument
) -> PaymentOrderId:
    session = testbed.start_checkout.run(
        StartCheckoutCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartCheckoutRequest(),
        )
    )
    return session.payment_order_id
