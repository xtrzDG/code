from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import (
    BillingNoticeKind,
    InvoiceStatus,
    SubscriptionStatus,
)
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.billing_ledger import BillingNotice, DueInvoicesRequest
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.billing.grace_periods import (
    start_grace_period,
    start_overage_grace,
)
from app.use_cases.billing.owner_notifications import notify_business_owners
from app.use_cases.billing.service_mode_switch import switch_service_mode
from app.use_cases.shared.billing_records import (
    advance_to_paid_periods,
    find_covering_paid_invoice,
    find_current_subscription,
    find_next_period_start,
    list_subscription_invoices,
)
from app.use_cases.shared.business_walk import walk_businesses

# An automatic charge is dated by day; wait this long past the period end
# for its notification before treating the renewal as missed.
RENEWAL_TOLERANCE_MICROSECONDS: int = 24 * 60 * 60 * 1_000_000


class EnforceGracePeriodsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Background job: keep service modes in line with payments.

    - PAST_DUE past `grace_until`: the assistant only takes requests
      (LEADS_ONLY, concept "только принять заявку"); owners are told.
    - CANCELLED: keeps full service through every period already paid
      (paid ahead in the trial too), then LEADS_ONLY as well.
    - ACTIVE whose period ended: moves into a period paid ahead, otherwise,
      a day after the end, the renewal is missed - the next period is
      invoiced and the subscription becomes PAST_DUE with grace.
    - ACTIVE with an unpaid bill for minutes above the package: PAST_DUE
      with grace counted from the day the bill was issued.
    - ACTIVE, or TRIALING within its trial, but still LEADS_ONLY (paid):
      back to FULL.
    - PAUSED: LEADS_ONLY; a pause scheduled replaces the renewal.
    - A live business without any subscription (never started the trial),
      or whose subscription waits for its first payment (INCOMPLETE), is
      not entitled to service: LEADS_ONLY.

    Each switch re-reads the business and changes only its service mode,
    so an owner's edit made while the job runs is kept.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        user_repo: UserRepoContract,
        plan_registry: PlanRegistryContract,
        issue_due_invoices: UseCaseContract[DueInvoicesRequest, list[InvoiceDocument]],
        manager_notifier: ManagerNotificationFacilitatorContract,
        billing_notice_transformer: TransformerContract[BillingNotice, MessageText],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._user_repo: UserRepoContract = user_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._issue_due_invoices: UseCaseContract[
            DueInvoicesRequest,
            list[InvoiceDocument],
        ] = issue_due_invoices
        self._manager_notifier: ManagerNotificationFacilitatorContract = (
            manager_notifier
        )
        self._billing_notice_transformer: TransformerContract[
            BillingNotice,
            MessageText,
        ] = billing_notice_transformer
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        processed: int = 0
        for business in walk_businesses(self._business_repo):
            subscription: SubscriptionDocument | None = find_current_subscription(
                self._subscription_repo,
                business.id,
            )
            if subscription is None:
                if business.status is BusinessStatus.LIVE and switch_service_mode(
                    self._business_repo,
                    business,
                    ServiceMode.LEADS_ONLY,
                    self._wall_clock.now_unix(),
                ):
                    processed += 1

                continue

            if self._enforce(business, subscription):
                processed += 1

        return JobReport(processed_count=ProcessedItemCount(processed))

    def _enforce(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
    ) -> bool:
        now: Microseconds = self._wall_clock.now_unix()
        match subscription.status:
            case SubscriptionStatus.INCOMPLETE:
                return business.status is BusinessStatus.LIVE and (
                    switch_service_mode(
                        self._business_repo, business, ServiceMode.LEADS_ONLY, now
                    )
                )
            case SubscriptionStatus.ACTIVE:
                return self._enforce_active(business, subscription, now)
            case SubscriptionStatus.TRIALING:
                is_trial_running: bool = (
                    subscription.trial_ends_at is None
                    or now < subscription.trial_ends_at
                )
                return is_trial_running and switch_service_mode(
                    self._business_repo,
                    business,
                    ServiceMode.FULL,
                    now,
                )
            case SubscriptionStatus.PAST_DUE:
                return self._enforce_past_due(business, subscription, now)
            case SubscriptionStatus.CANCELLED:
                return self._enforce_cancelled(business, subscription, now)
            case SubscriptionStatus.PAUSED:
                return switch_service_mode(
                    self._business_repo, business, ServiceMode.LEADS_ONLY, now
                )

    def _enforce_cancelled(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        now: Microseconds,
    ) -> bool:
        invoices: list[InvoiceDocument] = list_subscription_invoices(
            self._invoice_repo,
            subscription,
        )
        has_moved: bool = advance_to_paid_periods(subscription, invoices, now)
        if has_moved:
            subscription.updated_at = now
            self._subscription_repo.save(subscription)

        if (
            now < subscription.period_end
            or find_covering_paid_invoice(invoices, now) is not None
            or not switch_service_mode(
                self._business_repo, business, ServiceMode.LEADS_ONLY, now
            )
        ):
            return has_moved

        self._notify(business, BillingNoticeKind.SUBSCRIPTION_ENDED)
        return True

    def _enforce_active(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        now: Microseconds,
    ) -> bool:
        invoices: list[InvoiceDocument] = list_subscription_invoices(
            self._invoice_repo,
            subscription,
        )
        has_moved: bool = advance_to_paid_periods(subscription, invoices, now)
        if start_overage_grace(self._plan_registry, subscription, business, invoices):
            subscription.updated_at = now
            self._subscription_repo.save(subscription)
            return True

        if now < subscription.period_end + RENEWAL_TOLERANCE_MICROSECONDS:
            if has_moved:
                subscription.updated_at = now
                self._subscription_repo.save(subscription)

            return (
                switch_service_mode(
                    self._business_repo, business, ServiceMode.FULL, now
                )
                or has_moved
            )

        if subscription.pause_starts_at is not None:
            # The pause job starts the scheduled pause instead of a renewal.
            if has_moved:
                self._subscription_repo.save(subscription)

            return has_moved

        issued: list[InvoiceDocument] = self._issue_due_invoices.run(
            DueInvoicesRequest(
                business=business,
                subscription=subscription,
                period_start=find_next_period_start(subscription, invoices),
            )
        )
        if all(invoice.status is InvoiceStatus.PAID for invoice in issued):
            # The team's discount or credit paid the period: no grace, no notice.
            advance_to_paid_periods(subscription, invoices + issued, now)
            subscription.updated_at = now
            self._subscription_repo.save(subscription)
            return True

        self._start_grace(business, subscription, now)
        self._notify(
            business,
            BillingNoticeKind.RENEWAL_MISSED,
            amount=Money(
                amount_minor=issued[-1].amount_minor,
                currency_code=issued[-1].currency_code,
            ),
            deadline=subscription.grace_until,
        )
        return True

    def _enforce_past_due(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        now: Microseconds,
    ) -> bool:
        if subscription.grace_until is None:
            self._start_grace(business, subscription, now)
            return True

        if now < subscription.grace_until or not switch_service_mode(
            self._business_repo,
            business,
            ServiceMode.LEADS_ONLY,
            now,
        ):
            return False

        self._notify(business, BillingNoticeKind.LEADS_ONLY_STARTED)
        return True

    def _start_grace(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        now: Microseconds,
    ) -> None:
        start_grace_period(self._plan_registry, subscription, business, now)
        subscription.updated_at = now
        self._subscription_repo.save(subscription)

    def _notify(
        self,
        business: BusinessDocument,
        kind: BillingNoticeKind,
        amount: Money | None = None,
        deadline: Microseconds | None = None,
    ) -> None:
        notify_business_owners(
            business,
            self._user_repo,
            self._manager_notifier,
            self._billing_notice_transformer.transform(
                BillingNotice(
                    kind=kind,
                    language=business.owner_language,
                    timezone=business.timezone,
                    business_name=business.name,
                    amount=amount,
                    deadline=deadline,
                )
            ),
        )
