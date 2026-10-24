"""Package usage in the overview and the 80% usage warnings."""

from typed_time_provider import Microseconds

from app.schemas.constants.billing import PackageMetric, PlanKey, UsageKind
from app.schemas.dto.billing_cabinet import CancelSubscriptionCommand
from tests.billing.billing_settings import ITALY, MICROSECONDS_PER_DAY
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.usage_steps import (
    SECONDS_IN_MINUTE,
    check_usage,
    read_usage,
    start_trial,
)


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
