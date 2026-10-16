"""A business in its trial, and helpers to check out and pay through Flitt."""

from dataclasses import dataclass

from app.schemas.constants.billing import BillingPeriod, SetupOption
from app.schemas.constants.payments import PaymentWebhookOutcome
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_cabinet import (
    CheckoutSessionView,
    StartCheckoutCommand,
    StartCheckoutRequest,
    StartTrialCommand,
    StartTrialRequest,
)
from app.schemas.typings.billing.constrained_strings import PaymentReturnUrl
from tests.billing.billing_settings import GEORGIA, CountryPreset
from tests.billing.billing_testbed import BillingTestbed


@dataclass(frozen=True)
class PaidWorld:
    testbed: BillingTestbed
    owner: UserDocument
    business: BusinessDocument


def build_trial(
    country: CountryPreset = GEORGIA,
    billing_period: BillingPeriod = BillingPeriod.MONTHLY,
    setup_option: SetupOption = SetupOption.DONE_FOR_YOU,
) -> PaidWorld:
    """
    A business in its trial; set up by the platform team (the setup fee
    path) unless `setup_option` says the owner set it up alone.
    """

    testbed = BillingTestbed()
    owner = (
        testbed.add_user(phone_number="+995599123456", locale="ka")
        if country is GEORGIA
        else testbed.add_user(email="owner@example.com")
    )
    business = testbed.add_business(owner, country)
    testbed.start_trial.run(
        StartTrialCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartTrialRequest(billing_period=billing_period),
        )
    )
    subscription = testbed.subscription(business.id)
    subscription.setup_option = setup_option
    testbed.subscription_repo.save(subscription)
    return PaidWorld(testbed=testbed, owner=owner, business=business)


def checkout(world: PaidWorld, return_url: str | None = None) -> CheckoutSessionView:
    return world.testbed.start_checkout.run(
        StartCheckoutCommand(
            user_id=world.owner.id,
            business_id=world.business.id,
            request=StartCheckoutRequest(
                return_url=None if return_url is None else PaymentReturnUrl(return_url)
            ),
        )
    )


def payment_order(
    world: PaidWorld, session: CheckoutSessionView
) -> PaymentOrderDocument:
    order = world.testbed.payment_order_repo.get(session.payment_order_id)
    assert order is not None
    return order


def pay(world: PaidWorld, session: CheckoutSessionView, payment_id: int = 1) -> None:
    order = payment_order(world, session)
    receipt = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "approved", payment_id=payment_id)
    )
    assert receipt.outcome is PaymentWebhookOutcome.APPLIED


def build_active_subscription() -> tuple[PaidWorld, PaymentOrderDocument]:
    world = build_trial()
    session = checkout(world)
    pay(world, session)
    world.testbed.clock.advance(days=14, hours=1)
    world.testbed.run_job(world.testbed.end_trials, "end_trials")
    return world, payment_order(world, session)
