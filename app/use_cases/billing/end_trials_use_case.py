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
from app.schemas.constants.billing import BillingNoticeKind, SubscriptionStatus
from app.schemas.constants.businesses import ServiceMode
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import PlanDefinition
from app.schemas.dto.billing_ledger import BillingNotice, DueInvoicesRequest
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.billing.owner_notifications import notify_business_owners
from app.use_cases.shared.billing_records import (
    advance_to_paid_periods,
    find_covering_paid_invoice,
    find_current_subscription,
    find_paid_period_invoice,
    list_open_invoices,
    list_subscription_invoices,
    sum_invoice_amounts,
)
from app.utilities.billing.billing_periods import add_local_days


class EndTrialsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Background job: end free trials whose `trial_ends_at` has passed.

    A trial paid ahead at checkout becomes ACTIVE for the paid period. A
    trial without payment gets the invoices of its first period (with the
    setup fee for monthly billing) and becomes PAST_DUE with grace until
    now + the plan's grace days; the owners are told what to pay and until
    when the assistant keeps full service.
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
            if subscription is None or not self._is_trial_over(subscription):
                continue

            self._end_trial(business, subscription)
            processed += 1

        return JobReport(processed_count=ProcessedItemCount(processed))

    def _is_trial_over(self, subscription: SubscriptionDocument) -> bool:
        return (
            subscription.status is SubscriptionStatus.TRIALING
            and subscription.trial_ends_at is not None
            and self._wall_clock.now_unix() >= subscription.trial_ends_at
        )

    def _end_trial(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
    ) -> None:
        now: Microseconds = self._wall_clock.now_unix()
        trial_ends_at: Microseconds = subscription.trial_ends_at or now
        invoices: list[InvoiceDocument] = list_subscription_invoices(
            self._invoice_repo,
            subscription,
        )
        paid_invoice: InvoiceDocument | None = find_paid_period_invoice(
            invoices,
            trial_ends_at,
        ) or find_covering_paid_invoice(invoices, now)
        if paid_invoice is not None:
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.period_start = paid_invoice.period_start
            subscription.period_end = paid_invoice.period_end
            subscription.grace_until = None
            advance_to_paid_periods(subscription, invoices, now)
            subscription.updated_at = now
            self._subscription_repo.save(subscription)

            def restore_full_service(current: BusinessDocument) -> None:
                # Changed on the business as stored now, so an owner's edit
                # saved while the job runs is kept.
                if current.service_mode is not ServiceMode.FULL:
                    current.service_mode = ServiceMode.FULL
                    current.updated_at = now

            self._business_repo.update(business.id, restore_full_service)
            return

        self._issue_due_invoices.run(
            DueInvoicesRequest(
                business=business,
                subscription=subscription,
                period_start=trial_ends_at,
                is_setup_fee_included=True,
            )
        )
        plan: PlanDefinition = self._plan_registry.get(subscription.plan_key)
        subscription.status = SubscriptionStatus.PAST_DUE
        subscription.grace_until = add_local_days(
            now,
            int(plan.grace_period_days),
            business.timezone,
        )
        subscription.updated_at = now
        self._subscription_repo.save(subscription)
        open_invoices: list[InvoiceDocument] = list_open_invoices(
            list_subscription_invoices(self._invoice_repo, subscription)
        )
        notify_business_owners(
            business,
            self._user_repo,
            self._manager_notifier,
            self._billing_notice_transformer.transform(
                BillingNotice(
                    kind=BillingNoticeKind.TRIAL_ENDED_UNPAID,
                    language=business.owner_language,
                    timezone=business.timezone,
                    business_name=business.name,
                    amount=sum_invoice_amounts(open_invoices),
                    deadline=subscription.grace_until,
                )
            ),
        )
