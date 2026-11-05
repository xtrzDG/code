"""
A longer trial (running, or ended unpaid), a discount until a day, and the
setup fee waived: what each changes on the client's account.
"""

import pytest

from app.schemas.constants.billing import InvoiceKind, InvoiceStatus, SubscriptionStatus
from app.schemas.constants.businesses import ServiceMode
from app.schemas.dto.admin_actions import (
    GiveDiscountBody,
    GiveDiscountCommand,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import ClientDiscountPercent
from app.schemas.typings.billing.constrained_strings import DiscountEndDate
from tests.admin_actions.action_steps import discount, extend, waive
from tests.admin_actions.action_world import REASON, ActionWorld
from tests.billing.billing_settings import MICROSECONDS_PER_DAY
from tests.billing.grace_steps import end_trial, enforce, pay_open_invoices


def test_a_running_trial_ends_a_week_later() -> None:
    world = ActionWorld()
    ends_at = world.testbed.subscription(world.business.id).trial_ends_at
    assert ends_at is not None

    extend(world, world.founder)

    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.TRIALING
    assert int(subscription.trial_ends_at or 0) - int(ends_at) == (
        7 * MICROSECONDS_PER_DAY
    )
    assert subscription.period_end == subscription.trial_ends_at
    world.testbed.clock.advance(days=15)
    assert end_trial(world.testbed) == 0


def test_a_trial_that_ended_unpaid_runs_again_with_full_service() -> None:
    world = ActionWorld()
    world.testbed.clock.advance(days=14, hours=1)
    end_trial(world.testbed)
    world.testbed.clock.advance(days=7, hours=1)
    enforce(world.testbed)
    assert world.client().service_mode is ServiceMode.LEADS_ONLY

    extend(world, world.accountant)

    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.TRIALING
    assert subscription.grace_until is None
    assert int(subscription.trial_ends_at or 0) - int(world.testbed.clock.now()) == (
        7 * MICROSECONDS_PER_DAY
    )
    assert {
        invoice.status for invoice in world.testbed.invoices(world.business.id)
    } == {InvoiceStatus.VOID}
    assert world.client().service_mode is ServiceMode.FULL


def test_a_paying_client_has_no_trial_to_extend() -> None:
    world = ActionWorld()
    world.testbed.clock.advance(days=14, hours=1)
    end_trial(world.testbed)
    pay_open_invoices(world.testbed, world.owner, world.business)

    with pytest.raises(ConflictError, match="trial"):
        extend(world, world.founder)


def test_a_discount_runs_until_the_end_of_its_last_local_day() -> None:
    world = ActionWorld()

    discount(world, world.founder)

    granted = world.testbed.subscription(world.business.id).discount
    assert granted is not None
    assert int(granted.percent) == 30
    assert granted.granted_by == world.founder.id
    # 2028-01-01T00:00 in Tbilisi (UTC+4) is 2027-12-31T20:00 UTC.
    assert int(granted.ends_at) == 1_830_283_200_000_000


@pytest.mark.parametrize("last_day", ["2020-01-31", "2026-02-30", "2099-01-01"])
def test_a_discount_needs_a_coming_calendar_day(last_day: str) -> None:
    world = ActionWorld()

    with pytest.raises(ValidationFailedError):
        world.give_discount.run(
            GiveDiscountCommand(
                user_id=world.founder.id,
                business_id=world.business.id,
                body=GiveDiscountBody(
                    percent=ClientDiscountPercent(10),
                    last_day=DiscountEndDate(last_day),
                    reason=REASON,
                ),
            )
        )


def test_a_waived_setup_fee_is_voided_and_never_invoiced_again() -> None:
    world = ActionWorld()
    world.testbed.clock.advance(days=14, hours=1)
    end_trial(world.testbed)
    setup_fee = next(
        invoice
        for invoice in world.testbed.invoices(world.business.id)
        if invoice.kind is InvoiceKind.SETUP_FEE
    )

    waive(world, world.accountant)

    assert world.testbed.subscription(world.business.id).is_setup_fee_waived
    stored = world.testbed.invoice_repo.get(world.business.id, setup_fee.id)
    assert stored is not None and stored.status is InvoiceStatus.VOID
    with pytest.raises(ConflictError, match="waived already"):
        waive(world, world.founder)

    pay_open_invoices(world.testbed, world.owner, world.business)
    kinds = [
        invoice.kind
        for invoice in world.testbed.invoices(world.business.id)
        if invoice.status is InvoiceStatus.PAID
    ]
    assert kinds == [InvoiceKind.SERVICE_PERIOD]


def test_a_paid_setup_fee_cannot_be_waived() -> None:
    world = ActionWorld()
    world.testbed.clock.advance(days=14, hours=1)
    end_trial(world.testbed)
    pay_open_invoices(world.testbed, world.owner, world.business)

    with pytest.raises(ConflictError, match="paid already"):
        waive(world, world.founder)
