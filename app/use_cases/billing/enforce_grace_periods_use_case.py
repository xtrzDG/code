from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories import (
    BusinessRepoContract,
    InvoiceRepoContract,
    SubscriptionRepoContract,
    UserRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import BillingNoticeKind, SubscriptionStatus
from app.schemas.constants.businesses import ServiceMode
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.dto.billing_ledger import BillingNotice, DueInvoicesRequest
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.billing.billing_records import (
    advance_to_paid_periods,
    find_current_subscription,
    find_next_period_start,
    list_subscription_invoices,
)
from app.use_cases.billing.owner_notifications import notify_business_owners
from app.utilities.billing.billing_periods import add_local_days

# An automatic charge is dated by day; wait this long past the period end
# for its notification before treating the renewal as missed.
RENEWAL_TOLERANCE_MICROSECONDS: int = 24 * 60 * 60 * 1_000_000


class EnforceGracePeriodsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Background job: keep service modes in line with payments.

    - PAST_DUE past `grace_until`: the assistant only takes requests
      (LEADS_ONLY, concept "только принять заявку"); owners are told.
    - CANCELLED past the end of its period: LEADS_ONLY as well.
    - ACTIVE whose period ended: moves into a period paid ahead, otherwise,
      a day after the end, the renewal is missed - the next period is
      invoiced and the subscription becomes PAST_DUE with grace.
    - ACTIVE, or TRIALING within its trial, but still LEADS_ONLY (paid):
      back to FULL.
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
        for business in self._business_repo.list_all():
            subscription: SubscriptionDocument | None = find_current_subscription(
                self._subscription_repo,
                business.id,
            )
            if subscription is not None and self._enforce(business, subscription):
                processed += 1

        return JobReport(processed_count=ProcessedItemCount(processed))

    def _enforce(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
    ) -> bool:
        now: Microseconds = self._wall_clock.now_unix()
        match subscription.status:
            case SubscriptionStatus.ACTIVE:
                return self._enforce_active(business, subscription, now)
            case SubscriptionStatus.TRIALING:
                is_trial_running: bool = (
                    subscription.trial_ends_at is None
                    or now < subscription.trial_ends_at
                )
                return is_trial_running and self._set_service_mode(
                    business,
                    ServiceMode.FULL,
                    now,
                )
            case SubscriptionStatus.PAST_DUE:
                return self._enforce_past_due(business, subscription, now)
            case SubscriptionStatus.CANCELLED:
                if now < subscription.period_end or not self._set_service_mode(
                    business,
                    ServiceMode.LEADS_ONLY,
                    now,
                ):
                    return False

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
        if now < subscription.period_end + RENEWAL_TOLERANCE_MICROSECONDS:
            if has_moved:
                subscription.updated_at = now
                self._subscription_repo.save(subscription)

            return self._set_service_mode(business, ServiceMode.FULL, now) or has_moved

        issued: list[InvoiceDocument] = self._issue_due_invoices.run(
            DueInvoicesRequest(
                business=business,
                subscription=subscription,
                period_start=find_next_period_start(subscription, invoices),
            )
        )
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

        if now < subscription.grace_until or not self._set_service_mode(
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
        plan: PlanDefinition = self._plan_registry.get(subscription.plan_key)
        subscription.status = SubscriptionStatus.PAST_DUE
        subscription.grace_until = add_local_days(
            now,
            int(plan.grace_period_days),
            business.timezone,
        )
        subscription.updated_at = now
        self._subscription_repo.save(subscription)

    def _set_service_mode(
        self,
        business: BusinessDocument,
        service_mode: ServiceMode,
        now: Microseconds,
    ) -> bool:
        """Switch the mode; return False when it already was that mode."""

        if business.service_mode is service_mode:
            return False

        business.service_mode = service_mode
        business.updated_at = now
        self._business_repo.save(business)
        return True

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
