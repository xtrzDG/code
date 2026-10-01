from typed_time_provider import Microseconds, WallClock

from app.contracts.billing import PackageUsageWarningRepoContract
from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories import (
    BusinessRepoContract,
    SubscriptionRepoContract,
    UsageEventRepoContract,
    UserRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import (
    BillingNoticeKind,
    PackageMetric,
    SubscriptionStatus,
)
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.package_usage import PackageUsageWarningDocument
from app.schemas.dto.billing import PlanDefinition
from app.schemas.dto.billing_ledger import BillingNotice, PackageUsageTotals
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.billing.constrained_integers import PackageUsagePercent
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.billing.billing_records import find_current_subscription
from app.use_cases.billing.owner_notifications import notify_business_owners
from app.use_cases.billing.package_usage import (
    compute_usage_percent,
    summarize_package_usage,
)
from app.use_cases.billing.subscription_pricing import price_overage_per_minute
from app.utilities.billing.billing_periods import find_usage_window

WARNING_THRESHOLD_PERCENT: int = 80


class CheckPackageUsageUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Daily background job (concept section 9): sum the usage of the current
    billing period and warn the owners once per period when 80 % or more of
    the included call minutes or dialogs are used.

    The minutes warning names the price of a minute above the package. A
    warning is recorded only after at least one owner received it, so a
    failed delivery is retried on the next run. Cancelled subscriptions are
    not warned.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        subscription_repo: SubscriptionRepoContract,
        usage_event_repo: UsageEventRepoContract,
        package_usage_warning_repo: PackageUsageWarningRepoContract,
        user_repo: UserRepoContract,
        plan_registry: PlanRegistryContract,
        exchange_rate_registry: ExchangeRateRegistryContract,
        manager_notifier: ManagerNotificationFacilitatorContract,
        billing_notice_transformer: TransformerContract[BillingNotice, MessageText],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._package_usage_warning_repo: PackageUsageWarningRepoContract = (
            package_usage_warning_repo
        )
        self._user_repo: UserRepoContract = user_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._exchange_rate_registry: ExchangeRateRegistryContract = (
            exchange_rate_registry
        )
        self._manager_notifier: ManagerNotificationFacilitatorContract = (
            manager_notifier
        )
        self._billing_notice_transformer: TransformerContract[
            BillingNotice,
            MessageText,
        ] = billing_notice_transformer
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        warnings_sent: int = 0
        for business in self._business_repo.list_all():
            subscription: SubscriptionDocument | None = find_current_subscription(
                self._subscription_repo,
                business.id,
            )
            if subscription is None or subscription.status in {
                SubscriptionStatus.CANCELLED,
                SubscriptionStatus.INCOMPLETE,
            }:
                continue

            warnings_sent += self._check_business(business, subscription)

        return JobReport(processed_count=ProcessedItemCount(warnings_sent))

    def _check_business(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
    ) -> int:
        now: Microseconds = self._wall_clock.now_unix()
        plan: PlanDefinition = self._plan_registry.get(subscription.plan_key)
        window_start, window_end = find_usage_window(
            subscription,
            now,
            business.timezone,
        )
        totals: PackageUsageTotals = summarize_package_usage(
            self._usage_event_repo.list_by_business_between(
                business.id,
                window_start,
                window_end,
            ),
            window_start,
            window_end,
        )
        warnings_sent: int = 0
        for metric, used, included in (
            (
                PackageMetric.VOICE_MINUTES,
                int(totals.used_voice_minutes),
                int(plan.included_voice_minutes),
            ),
            (
                PackageMetric.DIALOGS,
                int(totals.used_dialogs),
                int(plan.included_dialogs),
            ),
        ):
            usage_percent: PackageUsagePercent | None = compute_usage_percent(
                used,
                included,
            )
            if (
                usage_percent is None
                or int(usage_percent) < WARNING_THRESHOLD_PERCENT
                or self._package_usage_warning_repo.find(
                    business.id,
                    subscription.id,
                    metric,
                    window_start,
                )
                is not None
            ):
                continue

            if self._warn(business, subscription, plan, totals, metric, usage_percent):
                self._package_usage_warning_repo.save(
                    PackageUsageWarningDocument(
                        business_id=business.id,
                        subscription_id=subscription.id,
                        metric=metric,
                        period_start=window_start,
                        usage_percent=usage_percent,
                        created_at=now,
                        updated_at=now,
                    )
                )
                warnings_sent += 1

        return warnings_sent

    def _warn(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        plan: PlanDefinition,
        totals: PackageUsageTotals,
        metric: PackageMetric,
        usage_percent: PackageUsagePercent,
    ) -> bool:
        is_voice: bool = metric is PackageMetric.VOICE_MINUTES
        notice = BillingNotice(
            kind=BillingNoticeKind.PACKAGE_USAGE_WARNING,
            language=business.owner_language,
            timezone=business.timezone,
            business_name=business.name,
            metric=metric,
            usage_percent=usage_percent,
            used_voice_minutes=totals.used_voice_minutes if is_voice else None,
            included_voice_minutes=plan.included_voice_minutes if is_voice else None,
            used_dialogs=None if is_voice else totals.used_dialogs,
            included_dialogs=None if is_voice else plan.included_dialogs,
            overage_price_per_minute=(
                price_overage_per_minute(
                    plan,
                    subscription.currency_code,
                    self._exchange_rate_registry,
                )[0]
                if is_voice
                else None
            ),
        )
        delivered: int = notify_business_owners(
            business,
            self._user_repo,
            self._manager_notifier,
            self._billing_notice_transformer.transform(notice),
        )
        return delivered > 0
