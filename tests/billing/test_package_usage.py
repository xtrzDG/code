from typed_time_provider import Microseconds

from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    PackageMetric,
    PlanKey,
    UsageKind,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_cabinet import (
    BillingOverviewQuery,
    CancelSubscriptionCommand,
    PackageUsageView,
    StartCheckoutCommand,
    StartCheckoutRequest,
    StartTrialCommand,
    StartTrialRequest,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.billing.billing_testbed import (
    GEORGIA,
    ITALY,
    MICROSECONDS_PER_DAY,
    BillingTestbed,
    CountryPreset,
)

SECONDS_IN_MINUTE: int = 60


def start_trial(
    testbed: BillingTestbed,
    country: CountryPreset = GEORGIA,
    plan_key: PlanKey = PlanKey.VOICE_AND_CHAT,
) -> tuple[UserDocument, BusinessDocument]:
    owner = (
        testbed.add_user(phone_number="+995599123456")
        if country is GEORGIA
        else testbed.add_user(email="owner@example.it")
    )
    business = testbed.add_business(owner, country, plan_key=plan_key)
    testbed.start_trial.run(
        StartTrialCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartTrialRequest(),
        )
    )
    return owner, business


def read_usage(
    testbed: BillingTestbed,
    owner: UserDocument,
    business: BusinessDocument,
    language: str | None = None,
) -> PackageUsageView:
    overview = testbed.get_overview.run(
        BillingOverviewQuery(
            user_id=owner.id,
            business_id=business.id,
            display_language=None if language is None else LanguageTag(language),
        )
    )
    assert overview.usage is not None
    return overview.usage


def check_usage(testbed: BillingTestbed) -> int:
    return testbed.run_job(testbed.check_package_usage, "check_package_usage")


def test_overview_counts_minutes_dialogs_and_prices_the_overage_in_lari() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed)
    other_owner = testbed.add_user(email="other@example.com")
    other_business = testbed.add_business(other_owner, ITALY)
    before_trial = Microseconds(int(testbed.clock.now()) - MICROSECONDS_PER_DAY)
    testbed.record_usage(business.id, UsageKind.VOICE_SECONDS, 24_000)
    testbed.record_usage(business.id, UsageKind.VOICE_SECONDS, 590)
    testbed.record_usage(
        business.id, UsageKind.VOICE_SECONDS, 6_000, occurred_at=before_trial
    )
    testbed.record_usage(other_business.id, UsageKind.VOICE_SECONDS, 60_000)
    for _ in range(3):
        testbed.record_usage(business.id, UsageKind.DIALOG, 1)

    testbed.record_usage(business.id, UsageKind.LLM_INPUT_TOKENS, 5_000)

    usage = read_usage(testbed, owner, business)

    assert int(usage.used_voice_minutes) == 410
    assert int(usage.included_voice_minutes) == 400
    assert usage.voice_usage_percent == 102
    assert int(usage.used_dialogs) == 3
    assert usage.dialog_usage_percent == 0
    assert int(usage.overage_voice_minutes) == 10
    assert usage.overage_price_per_minute.text == "0,44\xa0₾"
    assert usage.overage_price_per_minute.is_estimated is True
    assert usage.overage_cost.text == "4,40\xa0₾"
    assert usage.period_start == testbed.subscription(business.id).period_start


def test_overage_in_euro_is_exact() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed, ITALY)
    testbed.record_usage(business.id, UsageKind.VOICE_SECONDS, 410 * SECONDS_IN_MINUTE)

    usage = read_usage(testbed, owner, business, language="en")

    assert usage.overage_price_per_minute.text == "€0.15"
    assert usage.overage_price_per_minute.is_estimated is False
    assert usage.overage_cost.text == "€1.50"


def test_chat_plan_has_no_minute_package() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed, ITALY, plan_key=PlanKey.CHAT)
    testbed.record_usage(business.id, UsageKind.DIALOG, 950)

    usage = read_usage(testbed, owner, business)

    assert usage.voice_usage_percent is None
    assert int(usage.included_dialogs) == 1000
    assert usage.dialog_usage_percent == 95
    assert int(usage.overage_voice_minutes) == 0


def test_warning_at_eighty_percent_is_sent_once_per_period() -> None:
    testbed = BillingTestbed()
    _, business = start_trial(testbed)
    testbed.record_usage(business.id, UsageKind.VOICE_SECONDS, 319 * SECONDS_IN_MINUTE)
    assert check_usage(testbed) == 0

    testbed.record_usage(business.id, UsageKind.VOICE_SECONDS, SECONDS_IN_MINUTE)
    assert check_usage(testbed) == 1
    assert check_usage(testbed) == 0

    [(_, text)] = testbed.notifier.sent
    assert str(text) == (
        "Funicular VR: ამ პერიოდში გამოყენებულია ტარიფის ზარის წუთების 80% "
        "(320 / 400). პაკეტს ზემოთ ყოველი წუთი ღირს 0,44\xa0₾."
    )
    subscription = testbed.subscription(business.id)
    warning = testbed.warning_repo.find(
        business.id,
        subscription.id,
        PackageMetric.VOICE_MINUTES,
        subscription.period_start,
    )
    assert warning is not None
    assert warning.usage_percent == 80
    assert (
        testbed.warning_repo.find(
            business.id,
            subscription.id,
            PackageMetric.DIALOGS,
            subscription.period_start,
        )
        is None
    )


def test_dialogs_are_warned_separately_and_again_in_the_next_period() -> None:
    testbed = BillingTestbed()
    _, business = start_trial(testbed, ITALY)
    testbed.record_usage(business.id, UsageKind.DIALOG, 1_200)
    testbed.record_usage(business.id, UsageKind.VOICE_SECONDS, 330 * SECONDS_IN_MINUTE)

    assert check_usage(testbed) == 2

    testbed.clock.advance(days=15)
    assert check_usage(testbed) == 0
    testbed.record_usage(business.id, UsageKind.DIALOG, 1_300)
    assert check_usage(testbed) == 1
    assert "86% of the dialogs" in testbed.notifier.texts()[-1]


def test_undelivered_warning_is_retried() -> None:
    testbed = BillingTestbed()
    _, business = start_trial(testbed)
    testbed.record_usage(business.id, UsageKind.DIALOG, 1_500)
    testbed.notifier.is_delivering = False

    assert check_usage(testbed) == 0

    testbed.notifier.is_delivering = True
    assert check_usage(testbed) == 1
    assert len(testbed.notifier.sent) == 2


def test_cancelled_subscriptions_are_not_warned() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed)
    testbed.cancel_subscription.run(
        CancelSubscriptionCommand(user_id=owner.id, business_id=business.id)
    )
    testbed.record_usage(business.id, UsageKind.DIALOG, 1_500)

    assert check_usage(testbed) == 0


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
