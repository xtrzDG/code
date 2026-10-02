"""
Billing of the demo businesses: a running trial or a paid monthly
subscription, and metered usage spread over the days of the current
package window (the dashboard and billing pages read it).
"""

from typed_time_provider import Microseconds

from app.contracts.registries import PlanRegistryContract
from app.registries.demo.demo_clock import MICROSECONDS_PER_SECOND, DemoClock
from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    PackageMetric,
    SubscriptionStatus,
    UsageKind,
)
from app.schemas.domain.billing import (
    InvoiceDocument,
    SubscriptionDocument,
    UsageEventDocument,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.package_usage import PackageUsageWarningDocument
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    PackageUsagePercent,
    UsageQuantity,
)
from app.schemas.typings.billing.strings import (
    InvoiceDescription,
    PaymentProviderReference,
)
from app.utilities.billing.billing_periods import add_calendar_months, add_local_days

SECONDS_PER_MINUTE: int = 60
SECONDS_PER_DAY: int = 24 * 60 * 60
# Provider costs behind the usage (concept section 9): about a third of a
# US cent of model time per dialog, ElevenLabs Agents about 8 cents a minute.
DIALOG_COST_MICRO_USD: int = 3200
VOICE_COST_MICRO_USD_PER_SECOND: int = 1333
# Busier and quieter days, so the daily numbers do not look generated.
DAY_WEIGHTS: tuple[int, ...] = (9, 11, 8, 12, 14, 10, 7, 13, 9, 12, 10, 15, 8, 11)


def price_of(plan_registry: PlanRegistryContract, business: BusinessDocument) -> Money:
    """The monthly price in the business currency when the price book has it."""

    plan: PlanDefinition = plan_registry.get(business.plan_key)
    return (
        plan_registry.find_local_monthly_price(
            business.plan_key, business.currency_code
        )
        or plan.monthly_price
    )


def trial_subscription(
    plan_registry: PlanRegistryContract,
    business: BusinessDocument,
    started_at: Microseconds,
) -> SubscriptionDocument:
    """The plan's free trial, started at `started_at` (still running)."""

    price: Money = price_of(plan_registry, business)
    trial_days: int = int(plan_registry.get(business.plan_key).trial_days)
    trial_ends_at: Microseconds = add_local_days(
        started_at, trial_days, business.timezone
    )
    return SubscriptionDocument(
        business_id=business.id,
        plan_key=business.plan_key,
        billing_period=BillingPeriod.MONTHLY,
        price_minor=price.amount_minor,
        currency_code=price.currency_code,
        status=SubscriptionStatus.TRIALING,
        trial_ends_at=trial_ends_at,
        period_start=started_at,
        period_end=trial_ends_at,
        created_at=started_at,
        updated_at=started_at,
    )


def paid_subscription(
    plan_registry: PlanRegistryContract,
    business: BusinessDocument,
    period_start: Microseconds,
    reference: str,
    invoice_line: str,
) -> tuple[SubscriptionDocument, InvoiceDocument]:
    """An active monthly subscription and the paid invoice of its period."""

    price: Money = price_of(plan_registry, business)
    period_end: Microseconds = add_calendar_months(period_start, 1, business.timezone)
    subscription = SubscriptionDocument(
        business_id=business.id,
        plan_key=business.plan_key,
        billing_period=BillingPeriod.MONTHLY,
        price_minor=price.amount_minor,
        currency_code=price.currency_code,
        status=SubscriptionStatus.ACTIVE,
        period_start=period_start,
        period_end=period_end,
        provider_reference=PaymentProviderReference(reference),
        created_at=period_start,
        updated_at=period_start,
    )
    invoice = InvoiceDocument(
        business_id=business.id,
        subscription_id=subscription.id,
        kind=InvoiceKind.SERVICE_PERIOD,
        description=InvoiceDescription(invoice_line),
        amount_minor=price.amount_minor,
        currency_code=price.currency_code,
        status=InvoiceStatus.PAID,
        period_start=period_start,
        period_end=period_end,
        provider_reference=PaymentProviderReference(f"{reference}-1"),
        created_at=period_start,
        updated_at=period_start,
    )
    return subscription, invoice


def daily_usage(
    business: BusinessDocument,
    clock: DemoClock,
    since: Microseconds,
    dialogs: int,
    voice_minutes: int,
) -> list[UsageEventDocument]:
    """
    `dialogs` dialogs and `voice_minutes` call minutes between `since` and
    now, one event of each kind per day at noon, weighted by DAY_WEIGHTS.
    """

    day_count: int = max(1, (int(clock.now) - int(since)) // (SECONDS_PER_DAY * 10**6))
    weights: list[int] = [
        DAY_WEIGHTS[day % len(DAY_WEIGHTS)] for day in range(day_count)
    ]
    events: list[UsageEventDocument] = []
    for kind, total, cost_per_unit in (
        (UsageKind.DIALOG, dialogs, DIALOG_COST_MICRO_USD),
        (
            UsageKind.VOICE_SECONDS,
            voice_minutes * SECONDS_PER_MINUTE,
            VOICE_COST_MICRO_USD_PER_SECOND,
        ),
    ):
        if total == 0:
            continue

        shares: list[int] = split_total(total, weights)
        for day, quantity in enumerate(shares):
            moment = Microseconds(
                int(since) + (day * SECONDS_PER_DAY + 3600) * MICROSECONDS_PER_SECOND
            )
            events.append(
                UsageEventDocument(
                    business_id=business.id,
                    kind=kind,
                    quantity=UsageQuantity(quantity),
                    cost_micro_usd=CostMicroUsd(quantity * cost_per_unit),
                    occurred_at=moment,
                    created_at=moment,
                    updated_at=moment,
                )
            )

    return events


def usage_warning(
    subscription: SubscriptionDocument,
    metric: PackageMetric,
    percent: int,
    sent_at: Microseconds,
) -> PackageUsageWarningDocument:
    """The owners were already warned about this metric in this window."""

    return PackageUsageWarningDocument(
        business_id=subscription.business_id,
        subscription_id=subscription.id,
        metric=metric,
        period_start=subscription.period_start,
        usage_percent=PackageUsagePercent(percent),
        created_at=sent_at,
        updated_at=sent_at,
    )


def split_total(total: int, weights: list[int]) -> list[int]:
    """`total` split by `weights`; the rounding remainder goes to the last day."""

    weight_sum: int = sum(weights)
    shares: list[int] = [total * weight // weight_sum for weight in weights]
    shares[-1] += total - sum(shares)
    return shares
