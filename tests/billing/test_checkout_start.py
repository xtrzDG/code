"""Starting a checkout: what is charged, where the payer returns, refusals."""

import pytest

from app.schemas.constants.billing import BillingPeriod, InvoiceKind, InvoiceStatus
from app.schemas.constants.payments import PaymentStatus
from app.schemas.dto.billing_cabinet import StartCheckoutCommand, StartCheckoutRequest
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    ValidationFailedError,
)
from app.utilities.billing.billing_periods import to_local_calendar_day
from tests.billing.billing_settings import (
    APP_BASE_URL,
    CABINET_ORIGIN,
    CHECKOUT_URL,
    ITALY,
)
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.paid_world import (
    build_active_subscription,
    build_trial,
    checkout,
    payment_order,
)


def test_checkout_during_the_trial_prepays_the_first_month_and_setup() -> None:
    world = build_trial()
    trial_end = world.testbed.subscription(world.business.id).period_end

    session = checkout(world)

    invoices = world.testbed.invoices(world.business.id)
    setup_fee, first_period = invoices
    assert setup_fee.kind is InvoiceKind.SETUP_FEE
    assert int(setup_fee.amount_minor) == 44300
    assert setup_fee.period_start == setup_fee.period_end
    assert first_period.kind is InvoiceKind.SERVICE_PERIOD
    assert first_period.period_start == trial_end
    assert int(first_period.amount_minor) == 51700
    assert all(invoice.status is InvoiceStatus.ISSUED for invoice in invoices)
    assert session.amount.text == "960,00\xa0₾"
    assert str(session.checkout_url) == CHECKOUT_URL
    assert set(session.invoice_ids) == {setup_fee.id, first_period.id}
    sent = world.testbed.flitt.checkout_orders[0]
    assert sent["amount"] == 96000
    assert sent["currency"] == "GEL"
    assert sent["lang"] == "ka"
    assert sent["order_desc"] == str(first_period.description)
    assert sent["recurring_data"] == {
        "every": 1,
        "period": "month",
        "amount": 51700,
        "start_time": str(
            to_local_calendar_day(first_period.period_end, world.business.timezone)
        ),
        "state": "y",
        "readonly": "y",
    }
    assert "response_url" not in sent
    order = payment_order(world, session)
    assert order.status is PaymentStatus.CREATED
    assert int(order.recurring_amount_minor) == 51700
    assert str(order.last_payment_reference) == "802345671"


def test_annual_checkout_includes_the_setup_fee_and_charges_yearly() -> None:
    world = build_trial(ITALY, BillingPeriod.ANNUAL)

    session = checkout(world)

    invoices = world.testbed.invoices(world.business.id)
    assert [invoice.kind for invoice in invoices] == [InvoiceKind.SERVICE_PERIOD]
    assert int(invoices[0].amount_minor) == 178500
    assert session.amount.text == "1.785,00\xa0€"
    recurring = world.testbed.flitt.checkout_orders[0]["recurring_data"]
    assert isinstance(recurring, dict)
    assert recurring["every"] == 12
    assert world.testbed.flitt.checkout_orders[0]["lang"] == "it"


@pytest.mark.parametrize(
    "return_url",
    [f"{CABINET_ORIGIN}/billing?paid=1", CABINET_ORIGIN, f"{APP_BASE_URL}/done"],
)
def test_return_page_on_an_allowed_origin_is_passed_on(return_url: str) -> None:
    world = build_trial()

    checkout(world, return_url)

    assert world.testbed.flitt.checkout_orders[0]["response_url"] == return_url


@pytest.mark.parametrize(
    "return_url",
    ["https://evil.example/billing", f"{CABINET_ORIGIN}.evil.example/billing"],
)
def test_return_page_elsewhere_is_refused(return_url: str) -> None:
    world = build_trial()

    with pytest.raises(ValidationFailedError):
        checkout(world, return_url)

    assert world.testbed.flitt.checkout_orders == []


def test_checkout_without_a_subscription_is_not_found() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(email="owner@example.com")
    business = testbed.add_business(owner, ITALY)

    with pytest.raises(NotFoundError):
        testbed.start_checkout.run(
            StartCheckoutCommand(
                user_id=owner.id,
                business_id=business.id,
                request=StartCheckoutRequest(),
            )
        )


def test_a_provider_refusal_saves_no_payment_order() -> None:
    world = build_trial()
    world.testbed.flitt.refusal = {
        "response_status": "failure",
        "error_message": "Merchant is blocked",
    }

    with pytest.raises(ExternalServiceError):
        checkout(world)

    assert world.testbed.payment_order_repo.list_by_business(world.business.id) == []
    assert len(world.testbed.invoices(world.business.id)) == 2


def test_nothing_to_pay_while_automatic_payments_run() -> None:
    world, _ = build_active_subscription()

    with pytest.raises(ConflictError):
        checkout(world)
