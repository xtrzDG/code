"""Periodic job: seasonal pauses start, bill their months and end on time."""

import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.subscription_event_repositories import (
    SubscriptionEventRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.subscription_lifecycle import (
    SubscriptionLifecyclePolicyRegistryContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import (
    BillingNoticeKind,
    InvoiceKind,
    InvoiceStatus,
    SubscriptionStatus,
)
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.subscription_lifecycle import SubscriptionEventKind
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.billing_ledger import BillingNotice, DueInvoicesRequest
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.subscription_lifecycle_policy import SubscriptionLifecyclePolicy
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.billing.lifecycle.lifecycle_events import (
    clear_pause,
    lifecycle_event,
)
from app.use_cases.billing.owner_notifications import notify_business_owners
from app.use_cases.billing.service_mode_switch import switch_service_mode
from app.use_cases.shared.billing_records import (
    find_current_subscription,
    list_open_invoices,
    list_subscription_invoices,
)
from app.use_cases.shared.business_walk import walk_businesses
from app.utilities.billing.pause_pricing import pause_month_price_minor

logger: logging.Logger = logging.getLogger(__name__)


class RunSubscriptionPausesUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Hourly job over every business, before the grace job:

    - a scheduled pause whose start has come (the paid period ended)
      begins: PAUSED, the assistant takes requests only (channels stay
      connected), the first paused month is billed at the pause price and
      the owners are told until when;
    - a running pause moves into its next month, which is billed;
    - a pause whose end has come resumes by itself: ACTIVE with full
      service, the renewal flow bills the next period (or the automatic
      charges a pause checkout started do), and the owners are told.

    Each step is recorded in `subscription_events`. Billing is idempotent
    (a month already billed is reused), so a run after a restart repeats
    nothing; one failing business never stops the others.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        subscription_event_repo: SubscriptionEventRepoContract,
        user_repo: UserRepoContract,
        issue_due_invoices: UseCaseContract[DueInvoicesRequest, list[InvoiceDocument]],
        lifecycle_policy_registry: SubscriptionLifecyclePolicyRegistryContract,
        manager_notifier: ManagerNotificationFacilitatorContract,
        billing_notice_transformer: TransformerContract[BillingNotice, MessageText],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._subscription_event_repo: SubscriptionEventRepoContract = (
            subscription_event_repo
        )
        self._user_repo: UserRepoContract = user_repo
        self._issue_due_invoices: UseCaseContract[
            DueInvoicesRequest, list[InvoiceDocument]
        ] = issue_due_invoices
        self._lifecycle_policy_registry: SubscriptionLifecyclePolicyRegistryContract = (
            lifecycle_policy_registry
        )
        self._manager_notifier: ManagerNotificationFacilitatorContract = (
            manager_notifier
        )
        self._billing_notice_transformer: TransformerContract[
            BillingNotice, MessageText
        ] = billing_notice_transformer
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        processed: int = 0
        for business in walk_businesses(self._business_repo):
            try:
                processed += int(self._advance(business))
            except Exception:
                logger.exception(
                    "The pause of business %s was not advanced.", business.id
                )

        return JobReport(processed_count=ProcessedItemCount(processed))

    def _advance(self, business: BusinessDocument) -> bool:
        subscription: SubscriptionDocument | None = find_current_subscription(
            self._subscription_repo, business.id
        )
        if subscription is None or subscription.pause_until is None:
            return False

        now: Microseconds = self._wall_clock.now_unix()
        if subscription.status is SubscriptionStatus.PAUSED:
            if now >= subscription.pause_until:
                self._resume(business, subscription, now)
                return True

            if now < subscription.period_end:
                return False

            self._bill_month(business, subscription, subscription.period_end, now)
            return True

        starts_at: Microseconds | None = subscription.pause_starts_at
        if (
            subscription.status is not SubscriptionStatus.ACTIVE
            or starts_at is None
            or now < starts_at
        ):
            return False

        self._start(business, subscription, starts_at, now)
        return True

    def _start(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        starts_at: Microseconds,
        now: Microseconds,
    ) -> None:
        for invoice in list_open_invoices(
            list_subscription_invoices(self._invoice_repo, subscription)
        ):
            # A renewal billed for a period the pause covers.
            if invoice.kind is InvoiceKind.SERVICE_PERIOD and int(
                invoice.period_start
            ) >= int(starts_at):
                invoice.status = InvoiceStatus.VOID
                invoice.updated_at = now
                self._invoice_repo.save(invoice)

        subscription.status = SubscriptionStatus.PAUSED
        subscription.grace_until = None
        month: InvoiceDocument = self._bill_month(
            business, subscription, starts_at, now
        )
        switch_service_mode(self._business_repo, business, ServiceMode.LEADS_ONLY, now)
        self._subscription_event_repo.record(
            lifecycle_event(subscription, SubscriptionEventKind.PAUSE_STARTED, now)
        )
        self._notify(
            business,
            BillingNoticeKind.PAUSE_STARTED,
            amount=Money(
                amount_minor=MoneyAmountMinor(
                    pause_month_price_minor(
                        subscription, int(self._policy().pause_price_percent)
                    )
                ),
                currency_code=month.currency_code,
            ),
            deadline=subscription.pause_until,
        )

    def _bill_month(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        month_start: Microseconds,
        now: Microseconds,
    ) -> InvoiceDocument:
        issued: list[InvoiceDocument] = self._issue_due_invoices.run(
            DueInvoicesRequest(
                business=business,
                subscription=subscription,
                period_start=month_start,
                pause_price_percent=self._policy().pause_price_percent,
            )
        )
        month: InvoiceDocument = issued[-1]
        subscription.period_start = month.period_start
        subscription.period_end = month.period_end
        subscription.updated_at = now
        self._subscription_repo.save(subscription)
        return month

    def _policy(self) -> SubscriptionLifecyclePolicy:
        return self._lifecycle_policy_registry.policy()

    def _resume(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        now: Microseconds,
    ) -> None:
        resumed = lifecycle_event(subscription, SubscriptionEventKind.RESUMED, now)
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.period_end = subscription.pause_until or subscription.period_end
        subscription.grace_until = None
        clear_pause(subscription)
        subscription.updated_at = now
        self._subscription_repo.save(subscription)
        switch_service_mode(self._business_repo, business, ServiceMode.FULL, now)
        self._subscription_event_repo.record(resumed)
        self._notify(business, BillingNoticeKind.PAUSE_ENDED)

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
