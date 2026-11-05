"""
The invoice math of the team's discount and credit: both come off the
price before tax (the discount first, half up; then as much credit as is
left), the ledger records what each invoice used, a voided invoice gives
its credit back, an invoice they cover is paid at once, and a charge the
provider already took is invoiced as charged.
"""

from app.schemas.constants.billing import (
    BillingCreditKind,
    InvoiceKind,
    InvoiceStatus,
    SubscriptionStatus,
)
from app.schemas.constants.invoicing import TaxTreatment
from app.schemas.dto.billing import Money
from app.schemas.dto.billing_ledger import DueInvoicesRequest
from app.schemas.dto.invoicing import TaxDecision
from app.schemas.typings.billing.constrained_integers import (
    ClientDiscountPercent,
    MoneyAmountMinor,
)
from app.schemas.typings.invoicing.constrained_integers import TaxRateBasisPoints
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.billing.billing_credit_ledger import credit_balance
from app.utilities.billing.invoice_adjustments import adjust_price, discount_amount
from app.utilities.billing.tax_math import add_tax
from tests.admin_actions.action_steps import credit, discount, waive
from tests.admin_actions.action_world import ActionWorld
from tests.billing.grace_steps import end_trial, enforce

GEL: CurrencyCode = CurrencyCode("GEL")


def balance(world: ActionWorld) -> int:
    testbed = world.testbed
    return credit_balance(
        testbed.billing_credit_repo.list_by_business(world.business.id),
        testbed.invoice_repo.list_by_business(world.business.id),
        GEL,
    )


def test_the_discount_rounds_half_up_and_the_credit_takes_what_is_left() -> None:
    assert discount_amount(51700, ClientDiscountPercent(30)) == 15510
    assert discount_amount(999, ClientDiscountPercent(15)) == 150

    adjusted = adjust_price(51700, ClientDiscountPercent(30), 10_000)
    assert (adjusted.discount_minor, adjusted.credit_minor) == (15510, 10_000)
    assert adjusted.subtotal_minor == 26190
    covered = adjust_price(51700, ClientDiscountPercent(50), 99_999)
    assert (covered.credit_minor, covered.subtotal_minor) == (25850, 0)
    free = adjust_price(51700, ClientDiscountPercent(100), 5_000)
    assert (free.discount_minor, free.credit_minor, free.subtotal_minor) == (
        51700,
        0,
        0,
    )


def test_vat_goes_on_the_subtotal_after_discount_and_credit() -> None:
    adjusted = adjust_price(51700, ClientDiscountPercent(30), 10_000)
    taxed = add_tax(
        Money(
            amount_minor=MoneyAmountMinor(adjusted.subtotal_minor), currency_code=GEL
        ),
        TaxDecision(
            treatment=TaxTreatment.STANDARD,
            rate_basis_points=TaxRateBasisPoints(1800),
        ),
    )

    assert (int(taxed.tax.amount_minor), int(taxed.total.amount_minor)) == (
        4714,
        30904,
    )


def test_the_first_invoices_after_the_trial_use_the_discount_and_the_credit() -> None:
    world = ActionWorld()
    discount(world, world.founder)
    credit(world, world.accountant)
    world.testbed.clock.advance(days=14, hours=1)

    end_trial(world.testbed)

    period, setup_fee = world.testbed.invoices(world.business.id)
    # The setup fee is invoiced first and uses the 100.00 of credit; the
    # period gets the 30 % discount (setup fees are never discounted).
    assert (setup_fee.kind, int(setup_fee.amount_minor)) == (
        InvoiceKind.SETUP_FEE,
        34300,
    )
    assert (setup_fee.credit_minor, setup_fee.discount_minor) == (10_000, None)
    assert (int(period.amount_minor), period.discount_minor) == (36190, 15510)
    assert (int(period.subtotal_minor or 0), period.discount_percent) == (36190, 30)
    [used] = [
        line
        for line in world.testbed.billing_credit_repo.list_by_business(
            world.business.id
        )
        if line.kind is BillingCreditKind.USED
    ]
    assert (used.invoice_id, int(used.amount_minor)) == (setup_fee.id, 10_000)
    assert balance(world) == 0


def test_a_voided_invoice_gives_its_credit_back() -> None:
    world = ActionWorld()
    credit(world, world.accountant)
    world.testbed.clock.advance(days=14, hours=1)
    end_trial(world.testbed)
    assert balance(world) == 0

    waive(world, world.founder)

    assert balance(world) == 10_000


def test_credit_that_covers_the_period_pays_it_and_the_trial_ends_active() -> None:
    world = ActionWorld()
    waive(world, world.founder)
    for _ in range(6):
        credit(world, world.accountant)
    world.testbed.clock.advance(days=14, hours=1)

    end_trial(world.testbed)

    [period] = world.testbed.invoices(world.business.id)
    assert (period.status, int(period.amount_minor)) == (InvoiceStatus.PAID, 0)
    assert period.credit_minor == 51700
    assert period.paid_at == world.testbed.clock.now()
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.grace_until is None
    assert balance(world) == 60_000 - 51_700
    assert world.testbed.notifier.sent == []
    # The next period uses what is left, and the rest is a bill to pay.
    world.testbed.clock.advance(days=33)
    assert enforce(world.testbed) == 1
    renewal = world.testbed.invoices(world.business.id)[-1]
    assert (renewal.credit_minor, int(renewal.amount_minor)) == (8_300, 43_400)
    assert balance(world) == 0


def test_a_charge_the_provider_took_is_invoiced_as_charged() -> None:
    world = ActionWorld()
    discount(world, world.founder)
    credit(world, world.accountant)
    testbed = world.testbed
    subscription = testbed.subscription(world.business.id)

    [invoice] = testbed.issue_due_invoices.run(
        DueInvoicesRequest(
            business=world.client(),
            subscription=subscription,
            period_start=subscription.period_end,
            status=InvoiceStatus.PAID,
            charged_amount=Money(
                amount_minor=MoneyAmountMinor(51700), currency_code=GEL
            ),
        )
    )

    assert int(invoice.amount_minor) == 51700
    assert (invoice.discount_minor, invoice.credit_minor) == (None, None)
    assert balance(world) == 10_000
