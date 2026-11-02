"""
A free trial without a card on file sends at most
TRIAL_BUSINESS_DAILY_LIMIT text-backs a day (ABUSE-05: a trial nobody pays
for cannot be turned into an SMS pump through spoofed missed calls); a
saved card or a paid plan lifts the day to BUSINESS_DAILY_LIMIT.
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.billing import BillingPeriod, SubscriptionStatus
from app.schemas.constants.calls import TextBackSkipReason, TextBackStatus
from app.schemas.constants.payments import PaymentProvider
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.payment_methods import PaymentMethodSummary
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.use_cases.voice.missed_calls.text_back_rules import (
    BUSINESS_DAILY_LIMIT,
    TRIAL_BUSINESS_DAILY_LIMIT,
    business_daily_limit,
)
from tests.calls.call_steps import missed_calls, report_missed_call, save_call_settings
from tests.channels.voice_setup import VoiceSetup, build_voice_setup

DAY: int = 24 * 60 * 60 * 1_000_000


def subscription(
    setup: VoiceSetup, status: SubscriptionStatus, card_on_file: bool
) -> SubscriptionDocument:
    now = Microseconds(setup.testbed.clock.now_microseconds())
    return SubscriptionDocument(
        business_id=setup.business.id,
        plan_key=setup.business.plan_key,
        billing_period=BillingPeriod.MONTHLY,
        price_minor=MoneyAmountMinor(4_900),
        currency_code=CurrencyCode("EUR"),
        status=status,
        trial_ends_at=Microseconds(int(now) + 14 * DAY),
        period_start=now,
        period_end=Microseconds(int(now) + 14 * DAY),
        payment_method_summary=(
            PaymentMethodSummary(provider=PaymentProvider.FLITT, saved_at=now)
            if card_on_file
            else None
        ),
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def setup() -> VoiceSetup:
    voice_setup = build_voice_setup()
    save_call_settings(voice_setup, template_name=None)
    return voice_setup


def callers(count: int) -> list[str]:
    """Distinct Georgian mobiles, each calling once."""

    return [f"+99559{index:07d}" for index in range(count)]


def test_a_trial_without_a_card_texts_back_twenty_callers_a_day(
    setup: VoiceSetup,
) -> None:
    setup.testbed.subscription_repo.save(
        subscription(setup, SubscriptionStatus.TRIALING, card_on_file=False)
    )

    for caller in callers(int(TRIAL_BUSINESS_DAILY_LIMIT) + 5):
        report_missed_call(setup, caller)

    missed = missed_calls(setup)
    assert int(TRIAL_BUSINESS_DAILY_LIMIT) == 20
    assert sum(call.status is TextBackStatus.QUEUED for call in missed) == 20
    assert [
        call.skip_reason for call in missed if call.status is TextBackStatus.SKIPPED
    ] == [TextBackSkipReason.DAILY_LIMIT] * 5


@pytest.mark.parametrize(
    ("status", "card_on_file", "limit"),
    [
        (SubscriptionStatus.TRIALING, False, TRIAL_BUSINESS_DAILY_LIMIT),
        (SubscriptionStatus.TRIALING, True, BUSINESS_DAILY_LIMIT),
        (SubscriptionStatus.ACTIVE, False, BUSINESS_DAILY_LIMIT),
    ],
)
def test_a_card_or_a_paid_plan_lifts_the_trial_cap(
    setup: VoiceSetup,
    status: SubscriptionStatus,
    card_on_file: bool,
    limit: int,
) -> None:
    assert business_daily_limit(subscription(setup, status, card_on_file)) == limit
    assert business_daily_limit(None) == BUSINESS_DAILY_LIMIT


def test_with_a_card_the_twenty_first_caller_is_texted_too(setup: VoiceSetup) -> None:
    setup.testbed.subscription_repo.save(
        subscription(setup, SubscriptionStatus.TRIALING, card_on_file=True)
    )

    for caller in callers(int(TRIAL_BUSINESS_DAILY_LIMIT) + 1):
        report_missed_call(setup, caller)

    assert all(call.status is TextBackStatus.QUEUED for call in missed_calls(setup))
