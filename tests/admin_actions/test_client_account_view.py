"""
What the admin's client page shows of the team's grants (credit left,
discount, trial end, waived fee), the invoices paid by hand, the setup
option as the owner reads it, and the invoice PDF naming discount, credit
and a bank transfer.
"""

from app.schemas.constants.billing import (
    InvoiceKind,
    ManualPaymentMethod,
    SetupOption,
)
from app.schemas.constants.invoicing import BillingDocumentKind
from app.schemas.dto.admin import AdminClientQuery, ClientHealthView
from app.schemas.dto.invoicing import BillingDocumentPrintout
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.invoicing.billing_document_layout_transformer import (
    BillingDocumentLayoutTransformer,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.admin_actions.action_steps import credit, discount, mark_paid, waive
from tests.admin_actions.action_world import ActionWorld
from tests.billing.grace_steps import end_trial, start_trial


def detail(world: ActionWorld) -> ClientHealthView:
    testbed = world.testbed
    flagged = testbed.add_user(email="flagged@platform.example", is_platform_admin=True)
    return testbed.get_client_health.run(
        AdminClientQuery(user_id=flagged.id, business_id=world.business.id)
    )


def test_the_client_page_shows_credit_discount_trial_and_waived_fee() -> None:
    world = ActionWorld()
    credit(world, world.accountant)
    discount(world, world.founder)
    waive(world, world.founder)

    account = detail(world).account

    assert account is not None
    assert account.credit_balance is not None
    assert (
        int(account.credit_balance.amount_minor),
        str(account.credit_balance.currency_code),
    ) == (10_000, "GEL")
    assert account.discount is not None and account.discount.is_active
    assert int(account.discount.percent) == 30
    assert account.trial_ends_at is not None
    assert account.is_setup_fee_waived


def test_an_invoice_paid_by_hand_names_its_method() -> None:
    world = ActionWorld()
    world.testbed.clock.advance(days=14, hours=1)
    end_trial(world.testbed)
    period = next(
        invoice
        for invoice in world.testbed.invoices(world.business.id)
        if invoice.kind is InvoiceKind.SERVICE_PERIOD
    )
    mark_paid(world, world.accountant, period.id)

    [view] = [item for item in detail(world).invoices if item.id == period.id]

    assert view.manual_payment_method is ManualPaymentMethod.BANK_TRANSFER
    assert view.number is not None


def test_a_trial_without_a_setup_choice_reads_self_serve() -> None:
    world = ActionWorld()
    testbed = world.testbed
    _, business = start_trial(testbed)
    subscription = testbed.subscription(business.id)
    subscription.setup_option = None
    testbed.subscription_repo.save(subscription)
    flagged = testbed.add_user(email="flagged@platform.example", is_platform_admin=True)

    view = testbed.get_client_health.run(
        AdminClientQuery(user_id=flagged.id, business_id=business.id)
    )

    assert view.summary.setup_option is SetupOption.SELF_SERVE


def test_the_invoice_pdf_names_the_discount_the_credit_and_the_transfer() -> None:
    world = ActionWorld()
    waive(world, world.founder)
    discount(world, world.founder)
    credit(world, world.accountant)
    world.testbed.clock.advance(days=14, hours=1)
    end_trial(world.testbed)
    [period] = world.testbed.invoices(world.business.id)
    mark_paid(world, world.accountant, period.id)
    paid = world.testbed.invoice_repo.get(world.business.id, period.id)
    assert paid is not None

    html = str(
        BillingDocumentLayoutTransformer(LocalizedTextResolver()).transform(
            BillingDocumentPrintout(
                invoice=paid,
                kind=BillingDocumentKind.RECEIPT,
                language=LanguageTag("en"),
                timezone=world.client().timezone,
            )
        )
    )

    assert "Discount 30%" in html
    assert "−GEL155.10" in html
    assert "Credit applied" in html
    assert "−GEL100.00" in html
    assert "517.00" in html
    assert "Bank transfer, reference TBC #1" in html
