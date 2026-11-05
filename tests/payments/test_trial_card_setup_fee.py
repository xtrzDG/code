"""
A card saved in a done-for-you trial pays the one-time setup fee on its
page: the trial is billed what a trial without a card is billed at its end.
"""

from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    SetupOption,
    SubscriptionStatus,
)
from app.schemas.constants.payments import (
    PaymentOrderPurpose,
    PaymentWebhookOutcome,
)
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.billing_ledger import InvoiceDescriptionInput
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.billing.billing_periods import (
    add_billing_period,
    to_local_calendar_day,
)
from tests.billing.paid_world import PaidWorld, build_trial
from tests.payments.payment_world import (
    card_callback,
    payment_method,
    reload,
    save_card,
    setup_order,
)

DAYS_OF_TRIAL: int = 14


def kinds_and_statuses(world: PaidWorld) -> list[tuple[InvoiceKind, InvoiceStatus]]:
    return [
        (invoice.kind, invoice.status)
        for invoice in world.testbed.invoices(world.business.id)
    ]


def setup_fee_of(world: PaidWorld) -> InvoiceDocument:
    [fee] = [
        invoice
        for invoice in world.testbed.invoices(world.business.id)
        if invoice.kind is InvoiceKind.SETUP_FEE
    ]
    return fee


def first_automatic_charge(
    world: PaidWorld, order: PaymentOrderDocument, status: str = "approved"
) -> PaymentWebhookOutcome:
    return world.testbed.deliver_flitt_callback(
        {
            **world.testbed.callback_parameters(
                order,
                status,
                payment_id=8,
                amount=int(order.recurring_amount_minor),
            ),
            "order_id": f"{order.id}_1",
            "parent_order_id": str(order.id),
        }
    ).outcome


def test_the_card_page_of_a_done_for_you_trial_charges_the_setup_fee() -> None:
    world = build_trial(setup_option=SetupOption.DONE_FOR_YOU)
    trial_ends_at = world.testbed.subscription(world.business.id).trial_ends_at
    assert trial_ends_at is not None
    quoted = payment_method(world).setup_fee_due

    order = setup_order(world)

    fee = setup_fee_of(world)
    assert fee.status is InvoiceStatus.ISSUED
    assert quoted is not None
    assert (quoted.amount_minor, quoted.currency_code) == (
        fee.amount_minor,
        fee.currency_code,
    )
    assert order.purpose is PaymentOrderPurpose.CHECKOUT
    assert order.invoice_ids == [fee.id]
    assert order.amount_minor == fee.amount_minor
    sent = world.testbed.flitt.checkout_orders[-1]
    assert sent["amount"] == int(fee.amount_minor)
    assert "verification" not in sent
    assert sent["order_desc"] == str(fee.description)
    recurring = sent["recurring_data"]
    assert isinstance(recurring, dict)
    assert recurring["amount"] == int(order.recurring_amount_minor)
    assert recurring["start_time"] == str(
        to_local_calendar_day(trial_ends_at, world.business.timezone)
    )


def test_a_trial_with_a_saved_card_is_billed_the_setup_fee_and_then_the_month() -> None:
    world = build_trial(setup_option=SetupOption.DONE_FOR_YOU)
    order = setup_order(world)

    paid = world.testbed.deliver_flitt_callback(
        card_callback(world, order, "approved", 7)
    )

    assert paid.outcome is PaymentWebhookOutcome.APPLIED
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.TRIALING
    assert subscription.provider_reference == PaymentProviderReference(str(order.id))
    assert subscription.payment_method_summary is not None
    assert kinds_and_statuses(world) == [(InvoiceKind.SETUP_FEE, InvoiceStatus.PAID)]
    view = payment_method(world)
    assert view.setup_fee_due is None
    assert not view.is_trial_card_prompt_due

    world.testbed.clock.advance(days=DAYS_OF_TRIAL, hours=1)
    assert world.testbed.run_job(world.testbed.end_trials, "end_trials") == 0
    assert first_automatic_charge(world, reload(world, order)) is (
        PaymentWebhookOutcome.APPLIED
    )

    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.ACTIVE
    )
    assert sorted(kinds_and_statuses(world)) == sorted(
        [
            (InvoiceKind.SETUP_FEE, InvoiceStatus.PAID),
            (InvoiceKind.SERVICE_PERIOD, InvoiceStatus.PAID),
        ]
    )


def test_a_declined_setup_fee_stays_to_pay_and_the_next_card_page_pays_it() -> None:
    world = build_trial(setup_option=SetupOption.DONE_FOR_YOU)
    first = setup_order(world)
    world.testbed.deliver_flitt_callback(card_callback(world, first, "declined", 7))

    fee = setup_fee_of(world)
    assert fee.status is InvoiceStatus.FAILED
    view = payment_method(world)
    assert view.can_save_card
    assert view.setup_fee_due is not None
    assert view.setup_fee_due.amount_minor == fee.amount_minor

    second = setup_order(world)

    assert second.id != first.id
    assert second.invoice_ids == [fee.id]
    assert [invoice.kind for invoice in world.testbed.invoices(world.business.id)] == [
        InvoiceKind.SETUP_FEE
    ]


def test_an_abandoned_card_page_bills_the_setup_fee_once_when_the_trial_ends() -> None:
    world = build_trial(setup_option=SetupOption.DONE_FOR_YOU)
    save_card(world)
    world.testbed.clock.advance(days=DAYS_OF_TRIAL, hours=1)

    assert world.testbed.run_job(world.testbed.end_trials, "end_trials") == 1

    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.PAST_DUE
    )
    assert sorted(kinds_and_statuses(world)) == sorted(
        [
            (InvoiceKind.SETUP_FEE, InvoiceStatus.ISSUED),
            (InvoiceKind.SERVICE_PERIOD, InvoiceStatus.ISSUED),
        ]
    )


def test_a_self_serve_trial_owes_no_setup_fee_and_saves_the_card_for_nothing() -> None:
    world = build_trial(setup_option=SetupOption.SELF_SERVE)

    assert payment_method(world).setup_fee_due is None
    order = setup_order(world)

    assert order.purpose is PaymentOrderPurpose.CARD_SETUP
    assert int(order.amount_minor) == 0
    assert world.testbed.invoices(world.business.id) == []
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.trial_ends_at is not None
    # Flitt's page names the charges in the owner's language (Georgian).
    assert world.testbed.flitt.checkout_orders[-1]["order_desc"] == str(
        world.testbed.invoice_description_transformer.transform(
            InvoiceDescriptionInput(
                kind=InvoiceKind.SERVICE_PERIOD,
                language=LanguageTag("ka"),
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
    )


def test_a_waived_setup_fee_is_not_charged_on_the_card_page() -> None:
    world = build_trial(setup_option=SetupOption.DONE_FOR_YOU)
    subscription = world.testbed.subscription(world.business.id)
    subscription.is_setup_fee_waived = True
    world.testbed.subscription_repo.save(subscription)

    assert payment_method(world).setup_fee_due is None
    assert setup_order(world).purpose is PaymentOrderPurpose.CARD_SETUP
    assert world.testbed.invoices(world.business.id) == []
