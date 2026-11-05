"""What an invoice earns: the price before tax, only when paid, only once."""

from app.schemas.constants.billing import InvoiceStatus
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from tests.referrals.referral_billing_world import (
    ReferredWorld,
    invited_trial,
    partner_trial,
)


def _invoice(
    world: ReferredWorld,
    amount_minor: int,
    tax_minor: int | None = None,
    status: InvoiceStatus = InvoiceStatus.PAID,
) -> InvoiceDocument:
    now = world.paid.testbed.clock.now()
    return InvoiceDocument(
        business_id=world.business_id,
        description=InvoiceDescription("Call and message handling service"),
        amount_minor=MoneyAmountMinor(amount_minor),
        tax_minor=None if tax_minor is None else MoneyAmountMinor(tax_minor),
        currency_code=CurrencyCode("GEL"),
        status=status,
        period_start=now,
        period_end=now,
        paid_at=now if status is InvoiceStatus.PAID else None,
    )


def _record(world: ReferredWorld, *invoices: InvoiceDocument) -> None:
    business = world.paid.testbed.business(world.business_id)
    world.paid.testbed.referral_earnings.record_paid_invoices(business, list(invoices))


def test_the_commission_is_on_the_price_before_tax() -> None:
    world = partner_trial()

    _record(world, _invoice(world, amount_minor=11_800, tax_minor=1_800))

    [entry] = world.commissions()
    assert int(entry.base_minor) == 10_000
    assert int(entry.amount_minor) == 2_000


def test_unpaid_and_free_invoices_earn_nothing() -> None:
    world = invited_trial()
    assert world.referring is not None

    _record(
        world,
        _invoice(world, amount_minor=51_700, status=InvoiceStatus.ISSUED),
        _invoice(world, amount_minor=0),
    )

    assert world.credits(world.business_id) == []
    assert world.credits(world.referring.id) == []
    assert world.referral().first_paid_at is None


def test_a_commission_too_small_to_count_is_skipped() -> None:
    world = partner_trial()

    _record(world, _invoice(world, amount_minor=2), _invoice(world, amount_minor=3))

    assert len(world.commissions()) == 1


def test_a_business_nobody_referred_earns_nothing() -> None:
    world = partner_trial()
    testbed = world.paid.testbed
    business = testbed.business(world.business_id)
    business.referred_by = None
    testbed.business_repo.save(business)

    _record(world, _invoice(world, amount_minor=51_700))

    assert world.commissions() == []


def test_the_invited_business_gets_its_month_when_the_inviter_is_gone() -> None:
    world = invited_trial()
    assert world.referring is not None
    testbed = world.paid.testbed
    business = testbed.business(world.business_id)
    assert business.referred_by is not None
    business.referred_by.referring_business_id = BusinessId()
    testbed.business_repo.save(business)

    _record(world, _invoice(world, amount_minor=51_700))

    assert len(world.credits(world.business_id)) == 1
    assert world.referral().rewarded_at is not None
