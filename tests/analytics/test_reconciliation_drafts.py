"""
The billing step the daily reconciliation adds where the replayed events
disagree with the stored subscription, and none where they agree.
"""

from app.schemas.constants.analytics import ProductEventName, ProductEventSource
from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceStatus,
    PlanKey,
    SubscriptionStatus,
)
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.analytics.reconciliation_drafts import (
    billing_corrections,
    is_paying,
)
from tests.analytics.metric_events import at_day, billing

N = ProductEventName
BUSINESS: BusinessId = BusinessId()
EUR: CurrencyCode = CurrencyCode("EUR")


def subscription(
    status: SubscriptionStatus,
    price: int = 4900,
    period: BillingPeriod = BillingPeriod.MONTHLY,
    grace_until: float | None = None,
) -> SubscriptionDocument:
    return SubscriptionDocument(
        business_id=BUSINESS,
        plan_key=PlanKey.VOICE_AND_CHAT,
        billing_period=period,
        price_minor=MoneyAmountMinor(price),
        currency_code=EUR,
        status=status,
        period_start=at_day(10),
        period_end=at_day(40),
        grace_until=None if grace_until is None else at_day(grace_until),
        created_at=at_day(1),
        updated_at=at_day(12),
    )


def paid_invoice(day: float) -> InvoiceDocument:
    return InvoiceDocument(
        business_id=BUSINESS,
        description=InvoiceDescription("Service period"),
        amount_minor=MoneyAmountMinor(4900),
        currency_code=EUR,
        status=InvoiceStatus.PAID,
        period_start=at_day(day),
        period_end=at_day(day + 30),
        created_at=at_day(day),
        updated_at=at_day(day),
    )


def test_an_unrecorded_payer_is_subscribed_from_the_first_payment() -> None:
    (draft,) = billing_corrections(
        subscription(SubscriptionStatus.ACTIVE), [paid_invoice(10)], [], at_day(20)
    )

    assert draft.name is N.SUBSCRIBED
    assert draft.source is ProductEventSource.RECONCILIATION
    assert draft.occurred_at == at_day(10)
    assert int(draft.properties.monthly_amount or 0) == 4900


def test_an_annual_price_is_spread_over_twelve_months() -> None:
    (draft,) = billing_corrections(
        subscription(SubscriptionStatus.ACTIVE, 49000, BillingPeriod.ANNUAL),
        [paid_invoice(10)],
        [],
        at_day(20),
    )

    assert int(draft.properties.monthly_amount or 0) == 4083


def test_agreeing_steps_need_no_correction() -> None:
    events = [billing(N.SUBSCRIBED, 10, BUSINESS, 4900)]

    assert (
        billing_corrections(
            subscription(SubscriptionStatus.ACTIVE),
            [paid_invoice(10)],
            events,
            at_day(20),
        )
        == []
    )


def test_a_price_the_steps_do_not_know_is_a_plan_change_after_them() -> None:
    events = [billing(N.SUBSCRIBED, 13, BUSINESS, 2900)]

    (draft,) = billing_corrections(
        subscription(SubscriptionStatus.ACTIVE), [paid_invoice(10)], events, at_day(20)
    )

    assert draft.name is N.PLAN_CHANGED
    assert int(draft.occurred_at or 0) > int(at_day(13))


def test_a_grace_that_ran_out_is_a_cancellation() -> None:
    events = [billing(N.SUBSCRIBED, 10, BUSINESS, 4900)]
    lapsed = subscription(SubscriptionStatus.PAST_DUE, grace_until=15)

    (draft,) = billing_corrections(lapsed, [paid_invoice(10)], events, at_day(20))

    assert draft.name is N.CANCELLED


def test_who_pays() -> None:
    now = at_day(20)
    in_grace = subscription(SubscriptionStatus.PAST_DUE, grace_until=25)

    assert is_paying(subscription(SubscriptionStatus.ACTIVE), [], now)
    assert is_paying(in_grace, [paid_invoice(10)], now)
    # A trial that ended unpaid never paid.
    assert not is_paying(in_grace, [], now)
    assert not is_paying(subscription(SubscriptionStatus.TRIALING), [], now)
    assert not is_paying(subscription(SubscriptionStatus.CANCELLED), [], now)
