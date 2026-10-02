"""The package of the current billing window, as the dashboard shows it."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import (
    SubscriptionRepoContract,
    UsageEventRepoContract,
)
from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import PlanDefinition
from app.schemas.dto.billing_ledger import PackageUsageTotals
from app.schemas.dto.operations.dashboard import DashboardPackageUsage
from app.use_cases.billing.billing_records import find_current_subscription
from app.use_cases.billing.package_usage import (
    compute_overage_minutes,
    compute_usage_percent,
    summarize_package_usage,
)
from app.utilities.billing.billing_periods import find_usage_window


def build_dashboard_package_usage(
    subscription_repo: SubscriptionRepoContract,
    plan_registry: PlanRegistryContract,
    usage_event_repo: UsageEventRepoContract,
    wall_clock: WallClock[Microseconds],
    business: BusinessDocument,
) -> DashboardPackageUsage | None:
    """
    The current billing window's package; None without a subscription or
    while it waits for its first payment (INCOMPLETE: no service yet).
    """

    subscription: SubscriptionDocument | None = find_current_subscription(
        subscription_repo, business.id
    )
    if subscription is None or subscription.status is SubscriptionStatus.INCOMPLETE:
        return None

    plan: PlanDefinition = plan_registry.get(subscription.plan_key)
    window_start, window_end = find_usage_window(
        subscription, wall_clock.now_unix(), business.timezone
    )
    totals: PackageUsageTotals = summarize_package_usage(
        usage_event_repo.list_by_business_between(
            business.id, window_start, window_end
        ),
        window_start,
        window_end,
    )
    return DashboardPackageUsage(
        period_start=window_start,
        period_end=window_end,
        used_voice_minutes=totals.used_voice_minutes,
        included_voice_minutes=plan.included_voice_minutes,
        voice_usage_percent=compute_usage_percent(
            int(totals.used_voice_minutes), int(plan.included_voice_minutes)
        ),
        overage_voice_minutes=compute_overage_minutes(
            totals.used_voice_minutes, int(plan.included_voice_minutes)
        ),
        used_dialogs=totals.used_dialogs,
        included_dialogs=plan.included_dialogs,
        dialog_usage_percent=compute_usage_percent(
            int(totals.used_dialogs), int(plan.included_dialogs)
        ),
    )
