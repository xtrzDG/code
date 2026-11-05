"""
Every invoice the billing issues is the accountant's invoice: numbered in
the seller's series, with the seller and the buyer as they were, the VAT
the tax policy decides, and once paid, when and with which card.
"""

from typing import cast

from app.schemas.constants.billing import InvoiceKind, InvoiceStatus
from app.schemas.constants.invoicing import TaxTreatment
from app.schemas.constants.payments import PaymentWebhookOutcome
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from tests.billing.billing_settings import ITALY
from tests.billing.paid_world import PaidWorld, checkout, payment_order
from tests.invoicing.invoicing_world import (
    SELLER_TAX_ID,
    build_seller_trial,
    renew,
    save_billing_profile,
)


def period_invoice(world: PaidWorld) -> InvoiceDocument:
    return next(
        invoice
        for invoice in world.testbed.invoices(world.business.id)
        if invoice.kind is InvoiceKind.SERVICE_PERIOD
    )


def test_an_invoice_without_vat_registration_is_numbered_and_names_both_parties() -> (
    None
):
    world = build_seller_trial(is_vat_registered=False)

    checkout(world)

    invoice = period_invoice(world)
    assert str(invoice.number) == "AW-2026-000001"
    assert invoice.seller is not None and invoice.buyer is not None
    assert str(invoice.seller.legal_name) == "Assistant Workshop LLC"
    assert str(invoice.seller.tax_id) == SELLER_TAX_ID
    assert str(invoice.buyer.legal_name) == "Mtsvane Ezo"
    assert str(invoice.buyer.country_code) == "GE"
    assert invoice.buyer.tax_id is None
    assert invoice.tax_treatment is TaxTreatment.NOT_REGISTERED
    assert (int(invoice.subtotal_minor or 0), int(invoice.tax_minor or 0)) == (
        51_700,
        0,
    )
    assert int(invoice.amount_minor) == 51_700


def test_a_registered_seller_adds_georgian_vat_to_the_bill_and_the_autopay() -> None:
    world = build_seller_trial(is_vat_registered=True)
    save_billing_profile(world, "GE", tax_id="405123456")

    session = checkout(world)

    invoice = period_invoice(world)
    assert invoice.tax_treatment is TaxTreatment.STANDARD
    assert int(invoice.tax_rate_basis_points or 0) == 1800
    assert int(invoice.subtotal_minor or 0) == 51_700
    assert int(invoice.tax_minor or 0) == 9_306
    assert int(invoice.amount_minor) == 61_006
    assert str(invoice.buyer.tax_id if invoice.buyer else "") == "405123456"
    assert int(session.amount.money.amount_minor) == 61_006
    order = payment_order(world, session)
    assert int(order.recurring_amount_minor) == 61_006
    sent = world.testbed.flitt.checkout_orders[-1]
    recurring = cast(dict[str, object], sent["recurring_data"])
    assert (sent["amount"], recurring["amount"]) == (61_006, 61_006)


def test_a_setup_fee_gets_its_own_number_and_vat() -> None:
    world = build_seller_trial(is_vat_registered=True)
    world.testbed.set_up_for_you(world.business.id)

    checkout(world)

    invoices = world.testbed.invoices(world.business.id)
    numbers = sorted(str(invoice.number) for invoice in invoices)
    assert numbers == ["AW-2026-000001", "AW-2026-000002"]
    setup_fee = next(i for i in invoices if i.kind is InvoiceKind.SETUP_FEE)
    assert int(setup_fee.subtotal_minor or 0) == 44_300
    assert int(setup_fee.tax_minor or 0) == 7_974
    assert int(setup_fee.amount_minor) == 52_274


def test_buyers_abroad_pay_no_georgian_vat() -> None:
    business_abroad = build_seller_trial(is_vat_registered=True, country=ITALY)
    save_billing_profile(business_abroad, "IT", tax_id="IT12345678901")
    consumer_abroad = build_seller_trial(is_vat_registered=True, country=ITALY)

    checkout(business_abroad)
    checkout(consumer_abroad)

    reverse = period_invoice(business_abroad)
    outside = period_invoice(consumer_abroad)
    assert reverse.tax_treatment is TaxTreatment.REVERSE_CHARGE
    assert outside.tax_treatment is TaxTreatment.OUTSIDE_SCOPE
    for invoice in (reverse, outside):
        assert int(invoice.tax_minor or 0) == 0
        assert invoice.amount_minor == invoice.subtotal_minor
        assert str(invoice.currency_code) == "EUR"


def test_the_billing_details_of_an_issued_invoice_never_change() -> None:
    world = build_seller_trial(is_vat_registered=False)
    checkout(world)
    issued = period_invoice(world)

    save_billing_profile(world, "GE", tax_id="405123456")

    assert period_invoice(world).buyer == issued.buyer
    assert period_invoice(world).number == issued.number


def test_a_payment_records_when_and_the_masked_card() -> None:
    world = build_seller_trial(is_vat_registered=False)
    session = checkout(world)
    order = payment_order(world, session)
    world.testbed.clock.advance(hours=3)

    receipt = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(
            order,
            "approved",
            masked_card="444455XXXXXX1111",
            card_type="VISA",
        )
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED
    invoice = period_invoice(world)
    assert invoice.status is InvoiceStatus.PAID
    assert invoice.paid_at == world.testbed.clock.now()
    assert invoice.payment_card is not None
    assert str(invoice.payment_card.brand) == "VISA"
    assert str(invoice.payment_card.last_digits) == "1111"


def test_an_automatic_charge_is_invoiced_for_what_it_took() -> None:
    world = build_seller_trial(is_vat_registered=True)
    session = checkout(world)
    order = payment_order(world, session)
    world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "approved", payment_id=1)
    )
    world.testbed.clock.advance(days=14, hours=1)
    world.testbed.run_job(world.testbed.end_trials, "end_trials")
    world.testbed.clock.move_to(
        world.testbed.subscription(world.business.id).period_end
    )
    world.testbed.clock.advance(hours=2)

    receipt = renew(world, order, 2, masked_card="537541XXXXXX0003")

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED
    renewal = world.testbed.invoices(world.business.id)[-1]
    assert str(renewal.number) == "AW-2026-000002"
    assert int(renewal.amount_minor) == 61_006
    assert (int(renewal.subtotal_minor or 0), int(renewal.tax_minor or 0)) == (
        51_700,
        9_306,
    )
    assert renewal.paid_at == world.testbed.clock.now()
    assert renewal.payment_card is not None
    assert renewal.payment_card.brand is None
    assert str(renewal.payment_card.last_digits) == "0003"


def test_a_schedule_from_before_vat_keeps_its_amount_with_vat_inside() -> None:
    world = build_seller_trial(is_vat_registered=True)
    session = checkout(world)
    order = payment_order(world, session)
    world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "approved", payment_id=1)
    )
    # The schedule was started before VAT registration: 517.00 a month.
    order = payment_order(world, session)
    order.recurring_amount_minor = MoneyAmountMinor(51_700)
    world.testbed.payment_order_repo.save(order)
    world.testbed.clock.advance(days=14, hours=1)
    world.testbed.run_job(world.testbed.end_trials, "end_trials")
    world.testbed.clock.move_to(
        world.testbed.subscription(world.business.id).period_end
    )
    world.testbed.clock.advance(hours=2)

    renew(world, order, 2)

    renewal = world.testbed.invoices(world.business.id)[-1]
    assert int(renewal.amount_minor) == 51_700
    assert int(renewal.subtotal_minor or 0) + int(renewal.tax_minor or 0) == 51_700
    assert int(renewal.tax_minor or 0) == 7_886
