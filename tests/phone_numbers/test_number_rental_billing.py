"""Each rental month of a number: billed, on the platform, or the number goes back."""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.billing import InvoiceKind, UsageKind
from app.schemas.constants.phone_numbers import (
    PhoneNumberReleaseReason,
    PhoneNumberStatus,
)
from app.schemas.domain.billing import InvoiceDocument, UsageEventDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_cabinet import StartTrialCommand, StartTrialRequest
from tests.billing.grace_steps import end_trial, pay_open_invoices
from tests.phone_numbers.phone_world import PhoneWorld

TRIAL_DAYS: int = 14
MONTH_DAYS: int = 31


def paying_business(world: PhoneWorld) -> tuple[UserDocument, BusinessDocument]:
    """A monthly subscription paid after the trial, charges automatic."""

    owner, business = world.owner_and_business()
    world.start_trial.run(
        StartTrialCommand(
            user_id=owner.id, business_id=business.id, request=StartTrialRequest()
        )
    )
    pay_open_invoices(world, owner, business)
    world.clock.advance(days=TRIAL_DAYS, hours=1)
    end_trial(world)
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


def rental_usage(
    world: PhoneWorld, business: BusinessDocument
) -> list[UsageEventDocument]:
    return [
        event
        for event in world.usage_event_repo.list_by_business_between(
            business.id, Microseconds(0), Microseconds(world.clock.now() + 1)
        )
        if event.kind is UsageKind.NUMBER_RENTAL
    ]


@pytest.mark.usefixtures("open_rental_gate")
def test_a_paying_customer_gets_a_bill_each_month() -> None:
    world = PhoneWorld()
    owner, business = paying_business(world)
    world.rent_austin_number(owner, business)
    rented_at = world.rented(business).rented_at

    assert bill(world) == 1
    assert bill(world) == 0

    [invoice] = rental_invoices(world, business)
    assert int(invoice.amount_minor) == 500
    assert str(invoice.currency_code) == "GEL"
    assert invoice.period_start == rented_at
    assert "+1 512-555-0142" in str(invoice.description)
    [usage] = rental_usage(world, business)
    assert int(usage.cost_micro_usd) == 1_150_000
    number = world.rented(business)
    assert number.billed_until == invoice.period_end
    assert any("5,00" in text or "5.00" in text for text in world.notifier.texts())

    world.clock.advance(days=MONTH_DAYS)
    assert bill(world) == 1
    assert len(rental_invoices(world, business)) == 2
    assert len(rental_usage(world, business)) == 2


@pytest.mark.usefixtures("open_rental_gate")
def test_a_month_in_the_trial_is_on_the_platform() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()
    world.start_trial.run(
        StartTrialCommand(
            user_id=owner.id, business_id=business.id, request=StartTrialRequest()
        )
    )
    world.rent_austin_number(owner, business)

    assert bill(world) == 1

    assert rental_invoices(world, business) == []
    assert len(rental_usage(world, business)) == 1
    assert world.rented(business).status is PhoneNumberStatus.ACTIVE


@pytest.mark.usefixtures("open_rental_gate")
def test_nobody_paying_gives_the_number_back_after_its_first_month() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()
    world.rent_austin_number(owner, business)

    # The first month of a number taken before any payment: on the platform.
    assert bill(world) == 1
    assert rental_invoices(world, business) == []
    world.clock.advance(days=MONTH_DAYS)

    assert bill(world) == 1

    number = world.rented(business)
    assert number.status is PhoneNumberStatus.RELEASING
    assert number.release_reason is PhoneNumberReleaseReason.UNPAID
    assert len(rental_usage(world, business)) == 1
    assert world.notifier.texts() != []


@pytest.mark.usefixtures("open_rental_gate")
def test_months_missed_while_the_job_was_down_are_billed_one_by_one() -> None:
    world = PhoneWorld()
    owner, business = paying_business(world)
    world.rent_austin_number(owner, business)
    world.clock.advance(days=2 * MONTH_DAYS + 1)

    assert bill(world) == 3

    invoices = rental_invoices(world, business)
    assert len(invoices) == 3
    assert [invoice.period_end for invoice in invoices[:-1]] == [
        invoice.period_start for invoice in invoices[1:]
    ]
    assert world.rented(business).billed_until > world.clock.now()


def test_before_the_rental_gate_opens_no_month_is_billed_or_recorded() -> None:
    world = PhoneWorld()
    owner, business = paying_business(world)
    world.rent_austin_number(owner, business)
    rented_at = world.rented(business).rented_at

    assert bill(world) == 0

    assert rental_invoices(world, business) == []
    assert rental_usage(world, business) == []
    assert world.rented(business).billed_until == rented_at
