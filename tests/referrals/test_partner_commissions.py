"""A partner's commission on every invoice their businesses pay."""

import logging

import pytest

from app.schemas.constants.billing import InvoiceKind, InvoiceStatus
from app.schemas.constants.referrals import CommissionStatus, PartnerStatus
from app.utilities.referrals.commission_math import commission_month
from tests.admin_actions.action_steps import mark_paid
from tests.admin_actions.action_world import ActionWorld
from tests.billing.grace_steps import end_trial
from tests.billing.paid_world import checkout, pay, payment_order
from tests.referrals.referral_billing_world import (
    PARTNER_RATE,
    add_partner,
    partner_trial,
    refer_by_partner,
)


def test_a_partner_earns_on_every_paid_invoice() -> None:
    world = partner_trial()
    assert world.partner is not None
    session = checkout(world.paid)

    assert world.commissions() == []

    pay(world.paid, session)

    invoices = world.paid.testbed.invoices(world.business_id)
    entries = {entry.invoice_id: entry for entry in world.commissions()}
    assert set(entries) == {invoice.id for invoice in invoices}
    for invoice in invoices:
        entry = entries[invoice.id]
        base = int(invoice.amount_minor) - int(invoice.tax_minor or 0)
        assert entry.partner_id == world.partner.id
        assert entry.business_id == world.business_id
        assert int(entry.base_minor) == base
        assert entry.rate_basis_points == PARTNER_RATE
        assert int(entry.amount_minor) == base * int(PARTNER_RATE) // 10_000
        assert entry.currency_code == invoice.currency_code
        assert entry.accrued_at == invoice.paid_at
        assert entry.month == commission_month(entry.accrued_at)
        assert entry.status is CommissionStatus.ACCRUED


def test_each_renewal_earns_its_own_commission() -> None:
    world = partner_trial()
    session = checkout(world.paid)
    pay(world.paid, session)
    world.paid.testbed.clock.advance(days=14, hours=1)
    world.paid.testbed.run_job(world.paid.testbed.end_trials, "end_trials")
    earned_before = len(world.commissions())

    world.renew(payment_order(world.paid, session), payment_id=2)

    renewal = world.paid.testbed.invoices(world.business_id)[-1]
    assert renewal.status is InvoiceStatus.PAID
    assert len(world.commissions()) == earned_before + 1
    assert renewal.id in {entry.invoice_id for entry in world.commissions()}


def test_an_invoice_earns_once_however_often_it_is_reported() -> None:
    world = partner_trial()
    session = checkout(world.paid)
    pay(world.paid, session)
    earned = len(world.commissions())

    order = payment_order(world.paid, session)
    world.paid.testbed.deliver_flitt_callback(
        world.paid.testbed.callback_parameters(order, "approved", payment_id=1)
    )

    assert len(world.commissions()) == earned


def test_a_paused_partner_earns_nothing_new() -> None:
    world = partner_trial(PartnerStatus.PAUSED)

    pay(world.paid, checkout(world.paid))

    assert world.commissions() == []


def test_a_partners_business_gets_no_month_of_credit() -> None:
    world = partner_trial()

    pay(world.paid, checkout(world.paid))

    assert world.credits(world.business_id) == []
    referral = world.referral()
    assert referral.first_paid_at is not None
    assert referral.rewarded_at is None


def test_an_invoice_an_admin_marks_paid_earns_the_commission() -> None:
    world = ActionWorld()
    testbed = world.testbed
    partner = add_partner(testbed)
    refer_by_partner(testbed, world.business.id, partner)
    testbed.clock.advance(days=14, hours=1)
    end_trial(testbed)
    period = next(
        invoice
        for invoice in testbed.invoices(world.business.id)
        if invoice.kind is InvoiceKind.SERVICE_PERIOD
    )

    mark_paid(world, world.accountant, period.id)

    entries = [
        entry
        for entry in testbed.referrals.commission_entry_repo.list_of_month(
            partner.id, commission_month(testbed.clock.now()), CommissionStatus.ACCRUED
        )
    ]
    assert [entry.invoice_id for entry in entries] == [period.id]


def test_an_earnings_failure_is_logged_and_the_payment_stands(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = partner_trial()
    testbed = world.paid.testbed

    def broken(*_: object) -> None:
        raise RuntimeError("storage is down")

    monkeypatch.setattr(testbed.referrals.partner_repo, "get", broken)
    with caplog.at_level(logging.ERROR):
        pay(world.paid, checkout(world.paid))

    assert world.commissions() == []
    assert all(
        invoice.status is InvoiceStatus.PAID
        for invoice in testbed.invoices(world.business_id)
    )
    assert "were not recorded" in caplog.text
