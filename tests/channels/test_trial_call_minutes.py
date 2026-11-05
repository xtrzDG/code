"""
A free trial without a card on file takes MAX_TRIAL_DAILY_CALL_MINUTES of
calls a day (ABUSE-05: a trial nobody pays for cannot run hours of toll
fraud); a saved card or a paid plan lifts the day to MAX_DAILY_CALL_MINUTES.
A refused call goes to the missed-call flow like any other.
"""

from typing import Any

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.billing import (
    BillingPeriod,
    SubscriptionStatus,
    UsageKind,
)
from app.schemas.constants.payments import PaymentProvider
from app.schemas.domain.billing import SubscriptionDocument, UsageEventDocument
from app.schemas.domain.payment_methods import PaymentMethodSummary
from app.schemas.typings.billing.constrained_integers import (
    MoneyAmountMinor,
    UsageQuantity,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.channels.voice_service import (
    MAX_DAILY_CALL_MINUTES,
    MAX_TRIAL_DAILY_CALL_MINUTES,
)
from tests.channels.channels_payloads import HttpResponse, to_json_bytes
from tests.channels.voice_setup import (
    ASSISTANT_LINE,
    CALLER,
    VoiceSetup,
    build_voice_setup,
    tool_secret,
)

DAY: int = 24 * 60 * 60 * 1_000_000


def subscribe(
    setup: VoiceSetup, status: SubscriptionStatus, card_on_file: bool
) -> None:
    now = Microseconds(setup.testbed.clock.now_microseconds())
    setup.testbed.subscription_repo.save(
        SubscriptionDocument(
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
    )


def used_minutes(setup: VoiceSetup, minutes: int) -> None:
    now = setup.testbed.clock.now_microseconds()
    setup.testbed.usage_event_repo.append(
        UsageEventDocument(
            business_id=setup.business.id,
            kind=UsageKind.VOICE_SECONDS,
            quantity=UsageQuantity(minutes * 60),
            occurred_at=now,
            created_at=now,
            updated_at=now,
        )
    )


def post_start(setup: VoiceSetup) -> HttpResponse:
    body: dict[str, Any] = {
        "agent_id": "agent_1",
        "called_number": ASSISTANT_LINE,
        "caller_id": CALLER,
    }
    return setup.testbed.build_http_client().post(
        "/v1/voice/webhooks/conversation-initiation",
        content=to_json_bytes(body),
        headers={
            "X-Assistant-Business-Id": str(setup.business.id),
            "X-Assistant-Tool-Secret": tool_secret(setup.business.id),
        },
    )


@pytest.mark.parametrize(
    ("minutes", "status_code"),
    [(MAX_TRIAL_DAILY_CALL_MINUTES - 1, 200), (MAX_TRIAL_DAILY_CALL_MINUTES, 409)],
)
def test_a_trial_without_a_card_takes_an_hour_of_calls_a_day(
    minutes: int, status_code: int
) -> None:
    setup = build_voice_setup()
    subscribe(setup, SubscriptionStatus.TRIALING, card_on_file=False)
    used_minutes(setup, minutes)

    response = post_start(setup)

    assert MAX_TRIAL_DAILY_CALL_MINUTES == 60
    assert response.status_code == status_code, response.text
    if status_code == 409:
        assert f"its {MAX_TRIAL_DAILY_CALL_MINUTES} call minutes" in response.text


@pytest.mark.parametrize(
    ("status", "card_on_file"),
    [
        (SubscriptionStatus.TRIALING, True),
        (SubscriptionStatus.ACTIVE, False),
    ],
)
def test_a_saved_card_or_a_paid_plan_lifts_the_trial_cap(
    status: SubscriptionStatus, card_on_file: bool
) -> None:
    setup = build_voice_setup()
    subscribe(setup, status, card_on_file)
    used_minutes(setup, MAX_TRIAL_DAILY_CALL_MINUTES)

    assert post_start(setup).status_code == 200

    used_minutes(setup, MAX_DAILY_CALL_MINUTES - MAX_TRIAL_DAILY_CALL_MINUTES)
    refused = post_start(setup)
    assert refused.status_code == 409, refused.text
    assert f"its {MAX_DAILY_CALL_MINUTES} call minutes" in refused.text
