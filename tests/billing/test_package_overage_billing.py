"""Metering the package per month and billing the minutes above it."""

from typed_time_provider import Microseconds

from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    UsageKind,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_cabinet import (
    StartCheckoutCommand,
    StartCheckoutRequest,
    StartTrialCommand,
    StartTrialRequest,
)
from tests.billing.billing_settings import GEORGIA, ITALY, MICROSECONDS_PER_DAY
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.usage_steps import (
    SECONDS_IN_MINUTE,
    check_usage,
    read_usage,
    start_trial,
)


def pay_ahead_and_end_trial(
    testbed: BillingTestbed,
    owner: UserDocument,
    business: BusinessDocument,
) -> None:
    session = testbed.start_checkout.run(
        StartCheckoutCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartCheckoutRequest(),
        )
    )
    order = testbed.payment_order_repo.get(session.payment_order_id)
    assert order is not None
    testbed.deliver_flitt_callback(testbed.callback_parameters(order, "approved"))
    testbed.clock.advance(days=14, hours=1)
    testbed.run_job(testbed.end_trials, "end_trials")


def test_an_annual_plan_meters_the_package_per_month() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(phone_number="+995599123456")
    business = testbed.add_business(owner, GEORGIA)
    testbed.start_trial.run(
        StartTrialCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartTrialRequest(billing_period=BillingPeriod.ANNUAL),
        )
    )
    pay_ahead_and_end_trial(testbed, owner, business)
    period_start = testbed.subscription(business.id).period_start
    testbed.record_usage(
        business.id,
        UsageKind.VOICE_SECONDS,
        300 * SECONDS_IN_MINUTE,
        occurred_at=Microseconds(int(period_start) + MICROSECONDS_PER_DAY),
    )
    testbed.clock.move_to(Microseconds(int(period_start) + 40 * MICROSECONDS_PER_DAY))
    testbed.record_usage(business.id, UsageKind.VOICE_SECONDS, 300 * SECONDS_IN_MINUTE)

    usage = read_usage(testbed, owner, business)

    assert int(usage.used_voice_minutes) == 300
    assert int(usage.included_voice_minutes) == 400
    assert int(usage.overage_voice_minutes) == 0
    assert usage.period_start > period_start
    assert check_usage(testbed) == 0


def test_minutes_above_the_package_are_billed_once_per_month() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed)
    testbed.record_usage(business.id, UsageKind.VOICE_SECONDS, 900 * SECONDS_IN_MINUTE)
    pay_ahead_and_end_trial(testbed, owner, business)
    period = testbed.subscription(business.id)
    testbed.record_usage(
        business.id,
        UsageKind.VOICE_SECONDS,
        2_000 * SECONDS_IN_MINUTE,
        occurred_at=Microseconds(int(period.period_start) + MICROSECONDS_PER_DAY),
    )

    def bill() -> int:
        return testbed.run_job(testbed.invoice_usage_overage, "invoice_usage_overage")

    assert bill() == 0
    testbed.clock.move_to(period.period_end)

    assert bill() == 1
    assert bill() == 0

    [overage] = [
        invoice
        for invoice in testbed.invoices(business.id)
        if invoice.kind is InvoiceKind.USAGE_OVERAGE
    ]
    assert int(overage.amount_minor) == 1_600 * 44
    assert str(overage.currency_code) == "GEL"
    assert overage.status is InvoiceStatus.ISSUED
    assert (overage.period_start, overage.period_end) == (
        period.period_start,
        period.period_end,
    )
    assert "1,600" in str(overage.description) or "1 600" in str(
        overage.description
    ).replace("\xa0", " ")
    [(_, text)] = testbed.notifier.sent
    assert "704,00\xa0₾" in str(text)


def test_usage_within_the_package_is_not_billed() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed, ITALY)
    pay_ahead_and_end_trial(testbed, owner, business)
    period = testbed.subscription(business.id)
    testbed.record_usage(
        business.id,
        UsageKind.VOICE_SECONDS,
        400 * SECONDS_IN_MINUTE,
        occurred_at=period.period_start,
    )
    testbed.clock.move_to(period.period_end)

    assert testbed.run_job(testbed.invoice_usage_overage, "invoice_usage_overage") == 0
    assert testbed.notifier.sent == []
