"""
A card saved in the trial through Stripe Checkout (subscription mode, no
Stripe customer yet): the first invoice at the trial's end activates the
subscription, a done-for-you trial pays its setup fee on the page, and the
page names the charges in the owner's language.
"""

import pytest

from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    SetupOption,
    SubscriptionStatus,
)
from app.schemas.constants.payments import (
    PaymentOrderPurpose,
    PaymentProvider,
    PaymentWebhookOutcome,
)
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.billing_ledger import InvoiceDescriptionInput
from app.schemas.dto.payment_methods import StartCardSetupCommand, StartCardSetupRequest
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.billing.billing_periods import add_billing_period
from tests.billing.billing_settings import ITALY
from tests.billing.paid_world import PaidWorld, build_trial
from tests.billing.stripe_sandbox import STRIPE_PORTAL_URL
from tests.payments.payment_world import (
    MICROSECONDS_PER_SECOND,
    deliver_stripe,
    payment_method,
    reload,
    save_card,
    setup_order,
    stripe_invoice,
    stripe_session,
)
from tests.payments.test_stripe_renewals import (
    build_stripe_subscription,
    decline_renewal,
)

pytestmark = pytest.mark.usefixtures("stripe_gate_open")
RECURRING_NAME: str = "line_items[0][price_data][product_data][name]"
ONE_TIME_AMOUNT: str = "line_items[1][price_data][unit_amount]"


def complete_checkout(
    world: PaidWorld, order: PaymentOrderDocument, payment_status: str
) -> PaymentWebhookOutcome:
    return deliver_stripe(
        world,
        "checkout.session.completed",
        "evt_test_0100",
        {**stripe_session(order, payment_status), "invoice": None},
    ).outcome


def first_invoice_paid(world: PaidWorld, order: PaymentOrderDocument) -> None:
    trial_ends_at = world.testbed.subscription(world.business.id).trial_ends_at
    assert trial_ends_at is not None
    world.testbed.clock.move_to(trial_ends_at)
    world.testbed.clock.advance(hours=1)
    assert world.testbed.run_job(world.testbed.end_trials, "end_trials") == 0
    receipt = deliver_stripe(
        world, "invoice.paid", "evt_test_0101", stripe_invoice(order, "in_test_0101")
    )
    assert receipt.outcome is PaymentWebhookOutcome.APPLIED


def test_a_self_serve_trial_saves_its_card_in_checkout_and_the_trial_end_pays() -> None:
    world = build_trial(ITALY, setup_option=SetupOption.SELF_SERVE)
    order = setup_order(world)

    params = world.testbed.stripe.checkout_sessions[-1]
    assert params["mode"] == "subscription"
    assert ONE_TIME_AMOUNT not in params
    trial_ends_at = world.testbed.subscription(world.business.id).trial_ends_at
    assert trial_ends_at is not None
    assert params["subscription_data[trial_end]"] == str(
        int(trial_ends_at) // MICROSECONDS_PER_SECOND
    )
    assert order.purpose is PaymentOrderPurpose.CARD_SETUP
    assert complete_checkout(world, order, "no_payment_required") is (
        PaymentWebhookOutcome.APPLIED
    )
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.payment_provider is PaymentProvider.STRIPE
    assert subscription.provider_reference == PaymentProviderReference("sub_test_0001")
    assert subscription.payment_method_summary is not None
    assert not payment_method(world).is_trial_card_prompt_due

    first_invoice_paid(world, reload(world, order))

    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.ACTIVE
    )
    assert [
        (invoice.kind, invoice.status)
        for invoice in world.testbed.invoices(world.business.id)
    ] == [(InvoiceKind.SERVICE_PERIOD, InvoiceStatus.PAID)]


def test_a_done_for_you_trial_pays_its_setup_fee_on_the_checkout_page() -> None:
    world = build_trial(ITALY, setup_option=SetupOption.DONE_FOR_YOU)
    order = setup_order(world)

    [fee] = world.testbed.invoices(world.business.id)
    assert fee.kind is InvoiceKind.SETUP_FEE
    assert order.purpose is PaymentOrderPurpose.CHECKOUT
    params = world.testbed.stripe.checkout_sessions[-1]
    assert params[ONE_TIME_AMOUNT] == str(int(fee.amount_minor))
    assert complete_checkout(world, order, "paid") is PaymentWebhookOutcome.APPLIED

    first_invoice_paid(world, reload(world, order))

    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.ACTIVE
    )
    assert sorted(
        (invoice.kind, invoice.status)
        for invoice in world.testbed.invoices(world.business.id)
    ) == sorted(
        [
            (InvoiceKind.SETUP_FEE, InvoiceStatus.PAID),
            (InvoiceKind.SERVICE_PERIOD, InvoiceStatus.PAID),
        ]
    )


def test_the_checkout_page_names_the_charges_in_the_owners_language() -> None:
    world = build_trial(ITALY, setup_option=SetupOption.SELF_SERVE)
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.trial_ends_at is not None

    world.testbed.payments.start_card_setup.run(
        StartCardSetupCommand(
            user_id=world.owner.id,
            business_id=world.business.id,
            request=StartCardSetupRequest(),
            display_language=LanguageTag("ru"),
        )
    )

    expected = world.testbed.invoice_description_transformer.transform(
        InvoiceDescriptionInput(
            kind=InvoiceKind.SERVICE_PERIOD,
            language=LanguageTag("ru"),
            timezone=world.business.timezone,
            plan_names=world.testbed.plan_registry.get(subscription.plan_key).names,
            billing_period=subscription.billing_period,
            period_start=subscription.trial_ends_at,
            period_end=add_billing_period(
                subscription.trial_ends_at,
                subscription.billing_period,
                world.business.timezone,
            ),
        )
    )
    params = world.testbed.stripe.checkout_sessions[-1]
    assert params[RECURRING_NAME] == str(expected)
    assert params["locale"] == "ru"
    assert "Card for automatic payments" not in params.values()


def test_a_stripe_card_is_replaced_in_the_portal_while_a_charge_is_retried() -> None:
    world, order = build_stripe_subscription()
    decline_renewal(world, order)
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.PAST_DUE
    )

    session = save_card(world)

    assert str(session.url) == STRIPE_PORTAL_URL
    assert world.testbed.stripe.portal_sessions[-1]["customer"] == "cus_test_0001"
    assert session.payment_order_id is not None
    setup = world.testbed.payment_order_repo.get(
        PaymentOrderId(session.payment_order_id)
    )
    assert setup is not None
    assert setup.purpose is PaymentOrderPurpose.CARD_SETUP
