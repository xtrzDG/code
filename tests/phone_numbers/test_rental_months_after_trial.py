"""
Rental months judged at their start: a month that began in the trial stays
on the platform, and a subscription left past due past its grace gives the
number back instead of piling up unpaid bills.
"""

import pytest

from app.schemas.constants.billing import InvoiceKind, SubscriptionStatus
from app.schemas.constants.phone_numbers import (
    PhoneNumberReleaseReason,
    PhoneNumberStatus,
)
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_cabinet import StartTrialCommand, StartTrialRequest
from app.schemas.typings.maintenance.booleans import IsReleaseGateOpen
from app.schemas.typings.maintenance.constrained_strings import ReleaseGateName
from app.use_cases.shared.billing_records import find_current_subscription
from app.utilities.storage import release_gates
from app.utilities.storage.release_gates import PHONE_NUMBER_RENTAL_GATE
from tests.billing.grace_steps import end_trial, enforce, pay_open_invoices
from tests.phone_numbers.phone_world import PhoneWorld

TRIAL_DAYS: int = 14
MONTH_DAYS: int = 31


def trial_business(world: PhoneWorld) -> tuple[UserDocument, BusinessDocument]:
    owner, business = world.owner_and_business()
    world.start_trial.run(
        StartTrialCommand(
            user_id=owner.id, business_id=business.id, request=StartTrialRequest()
        )
    )
    return owner, business


def bill(world: PhoneWorld) -> int:
    return world.run_job(world.bill_rentals, "bill_phone_number_rentals")


def rental_invoices(
    world: PhoneWorld, business: BusinessDocument
) -> list[InvoiceDocument]:
    return [
        invoice
        for invoice in world.invoices(business.id)
        if invoice.kind is InvoiceKind.NUMBER_RENTAL
    ]


def status_of(world: PhoneWorld, business: BusinessDocument) -> SubscriptionStatus:
    subscription = find_current_subscription(world.subscription_repo, business.id)
    assert subscription is not None
    return subscription.status


@pytest.mark.usefixtures("open_rental_gate")
def test_a_trial_that_ends_unpaid_gives_the_number_back_after_the_grace() -> None:
    world = PhoneWorld()
    owner, business = trial_business(world)
    world.rent_austin_number(owner, business)
    assert bill(world) == 1
    world.clock.advance(days=TRIAL_DAYS, hours=1)
    end_trial(world)
    assert status_of(world, business) is SubscriptionStatus.PAST_DUE

    for _ in range(3):
        world.clock.advance(days=MONTH_DAYS)
        enforce(world)
        bill(world)

    number = world.rented(business)
    assert number.status is PhoneNumberStatus.RELEASING
    assert number.release_reason is PhoneNumberReleaseReason.UNPAID
    assert rental_invoices(world, business) == []
    assert status_of(world, business) is SubscriptionStatus.PAST_DUE


@pytest.mark.usefixtures("open_rental_gate")
def test_a_month_that_begins_within_the_grace_is_still_billed() -> None:
    world = PhoneWorld()
    owner, business = trial_business(world)
    world.clock.advance(days=TRIAL_DAYS, hours=1)
    end_trial(world)
    assert status_of(world, business) is SubscriptionStatus.PAST_DUE

    world.rent_austin_number(owner, business)
    assert bill(world) == 1

    assert len(rental_invoices(world, business)) == 1
    assert world.rented(business).status is PhoneNumberStatus.ACTIVE


JOB_GATE_CHECK: str = (
    "app.use_cases.billing.number_rentals.bill_phone_number_rentals_use_case"
    ".is_gate_open"
)


def gate_closed_for_the_job(name: ReleaseGateName) -> IsReleaseGateOpen:
    """This release, as the rental job sees it: the rental gate is closed."""

    return name != PHONE_NUMBER_RENTAL_GATE and release_gates.is_gate_open(name)


@pytest.mark.usefixtures("open_rental_gate")
def test_catching_up_after_the_gate_opens_leaves_the_trial_month_unbilled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = PhoneWorld()
    owner, business = trial_business(world)
    pay_open_invoices(world, owner, business)
    world.rent_austin_number(owner, business)
    rented_at = world.rented(business).rented_at
    # This release: the gate is closed for the job; the next one opens it.
    monkeypatch.setattr(JOB_GATE_CHECK, gate_closed_for_the_job)
    assert bill(world) == 0
    world.clock.advance(days=TRIAL_DAYS, hours=1)
    end_trial(world)
    assert status_of(world, business) is SubscriptionStatus.ACTIVE

    monkeypatch.setattr(JOB_GATE_CHECK, release_gates.is_gate_open)
    assert bill(world) == 1

    assert rental_invoices(world, business) == []
    number = world.rented(business)
    assert number.status is PhoneNumberStatus.ACTIVE
    assert number.billed_until > rented_at

    world.clock.advance(days=MONTH_DAYS)
    assert bill(world) == 1
    [invoice] = rental_invoices(world, business)
    assert invoice.period_start == number.billed_until
