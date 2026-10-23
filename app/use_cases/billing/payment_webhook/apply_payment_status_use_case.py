from typed_time_provider import Microseconds, WallClock

from app.contracts.billing import (
    PaymentGatewayAdapterContract,
    PaymentOrderRepoContract,
)
from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.payment_methods import PaymentRetryRepoContract
from app.contracts.referrals import ReferralEarningsFacilitatorContract
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import InvoiceStatus, SubscriptionStatus
from app.schemas.constants.payments import (
    PaymentRetryOutcome,
    PaymentStatus,
    PaymentWebhookOutcome,
)
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.billing_ledger import BillingNotice, DueInvoicesRequest
from app.schemas.dto.payment_webhooks import PaymentStatusChange
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.billing.grace_periods import start_grace_period
from app.use_cases.billing.owner_notifications import notify_business_owners
from app.use_cases.billing.payment_webhook.card_on_file_recording import (
    is_card_setup_verification,
)
from app.use_cases.billing.payment_webhook.checkout_payment_settlement import (
    decline_checkout_payment,
    settle_checkout_payment,
)
from app.use_cases.billing.payment_webhook.payment_failure_notice import (
    build_payment_failed_notice,
    invoice_amount,
)
from app.use_cases.billing.payment_webhook.payment_invoice_settlement import (
    paid_order_invoices,
    record_renewal_invoice,
)
from app.use_cases.billing.payment_webhook.payment_order_rules import (
    FINAL_ORDER_STATUSES,
    is_stray_charge,
    require_expected_amount,
    stop_stray_schedule,
)
from app.use_cases.billing.payment_webhook.payment_retry_settlement import (
    find_retried_invoice,
    record_retry_outcome,
    settle_retry_approval,
)
from app.use_cases.shared.service_mode_restoration import restore_full_service
from app.use_cases.shared.subscription_payment_transitions import activate_paid_period


class ApplyPaymentStatusUseCase(
    UseCaseContract[PaymentStatusChange, PaymentWebhookOutcome]
):
    """
    What a payment's status does to its order, invoices and subscription
    (ProcessPaymentWebhookUseCase hands it each new (payment, status) pair).

    - approved, first payment of a checkout: its invoices become PAID and
      the card's automatic charges replace those of an earlier checkout (one
      schedule ever runs). The subscription becomes ACTIVE for the paid
      period that has started (a trial paid ahead stays in trial until it
      ends; a cancelled one is resumed), grace ends and the assistant
      serves in full. Money that settles no bill is marked for refund.
    - approved, later automatic charge of the current schedule: the next
      period is invoiced as PAID (for what was charged); a retry of a
      declined charge pays the invoice it retried (and records the
      retry's answer); a retry whose invoice is already paid is marked
      for refund (REFUND_DUE). Either way the paid
      period becomes current once it starts and what the paid invoices
      earn a referral is recorded.
    - an automatic charge of any other schedule (replaced, stopped, or of a
      cancelled subscription) is never booked as service: its schedule is
      stopped and an approved charge is marked for refund (REFUND_DUE).
    - declined: first payment - its invoices become FAILED; automatic
      charge - the next period is invoiced as FAILED and an active
      subscription (or a trial that has ended) becomes PAST_DUE with grace
      until now + the plan's grace days. Owners are told either way. A
      declined retry changes no bill (its row records the decline): the
      dunning job tells the owners.
    - a card setup's own verification only records its status: the card it
      saved settled the setup already.
    - expired, created, processing, reversed: recorded on the payment order
      only (a reversal is handled by the platform admin).
    """

    def __init__(
        self,
        payment_gateway: PaymentGatewayAdapterContract,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        plan_registry: PlanRegistryContract,
        issue_due_invoices: UseCaseContract[DueInvoicesRequest, list[InvoiceDocument]],
        manager_notifier: ManagerNotificationFacilitatorContract,
        billing_notice_transformer: TransformerContract[BillingNotice, MessageText],
        wall_clock: WallClock[Microseconds],
        referral_earnings: ReferralEarningsFacilitatorContract,
        payment_retry_repo: PaymentRetryRepoContract,
        payment_order_repo: PaymentOrderRepoContract,
    ) -> None:
        self._payment_gateway: PaymentGatewayAdapterContract = payment_gateway
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._user_repo: UserRepoContract = user_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._issue_due_invoices: UseCaseContract[
            DueInvoicesRequest, list[InvoiceDocument]
        ] = issue_due_invoices
        self._manager_notifier: ManagerNotificationFacilitatorContract = (
            manager_notifier
        )
        self._billing_notice_transformer: TransformerContract[
            BillingNotice, MessageText
        ] = billing_notice_transformer
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._referral_earnings: ReferralEarningsFacilitatorContract = referral_earnings
        self._payment_retry_repo: PaymentRetryRepoContract = payment_retry_repo
        self._payment_order_repo: PaymentOrderRepoContract = payment_order_repo

    def run(self, input_data: PaymentStatusChange) -> PaymentWebhookOutcome:
        notification = input_data.notification
        payment_order = input_data.payment_order
        if is_card_setup_verification(notification, payment_order):
            if payment_order.status not in FINAL_ORDER_STATUSES:
                payment_order.status = notification.status

            return PaymentWebhookOutcome.IGNORED

        match notification.status:
            case PaymentStatus.APPROVED:
                require_expected_amount(notification, payment_order)
                if is_stray_charge(payment_order, input_data.subscription):
                    stop_stray_schedule(self._payment_gateway, payment_order)
                    payment_order.is_refund_due = True
                    return PaymentWebhookOutcome.REFUND_DUE

                return self._apply_approval(input_data)
            case PaymentStatus.DECLINED:
                if is_stray_charge(payment_order, input_data.subscription):
                    stop_stray_schedule(self._payment_gateway, payment_order)
                    return PaymentWebhookOutcome.IGNORED

                if notification.is_retry and payment_order.is_initial_payment_settled:
                    self._record_declined_retry(input_data)
                    return PaymentWebhookOutcome.IGNORED

                self._apply_decline(input_data)
                return PaymentWebhookOutcome.APPLIED
            case PaymentStatus.REVERSED:
                payment_order.status = PaymentStatus.REVERSED
                return PaymentWebhookOutcome.APPLIED
            case (
                PaymentStatus.EXPIRED | PaymentStatus.CREATED | PaymentStatus.PROCESSING
            ):
                if payment_order.status not in FINAL_ORDER_STATUSES:
                    payment_order.status = notification.status

                return PaymentWebhookOutcome.IGNORED

    def _apply_approval(self, change: PaymentStatusChange) -> PaymentWebhookOutcome:
        notification, payment_order = change.notification, change.payment_order
        subscription, business = change.subscription, change.business
        now: Microseconds = self._wall_clock.now_unix()
        outcome: PaymentWebhookOutcome = PaymentWebhookOutcome.APPLIED
        if payment_order.is_initial_payment_settled:
            retried: InvoiceDocument | None = find_retried_invoice(
                self._payment_retry_repo,
                self._invoice_repo,
                payment_order,
                subscription,
                notification,
            )
            paid: list[InvoiceDocument]
            if retried is None:
                paid = [
                    record_renewal_invoice(
                        self._invoice_repo,
                        self._issue_due_invoices,
                        business,
                        subscription,
                        InvoiceStatus.PAID,
                        notification.payment_reference,
                        now,
                        charge=notification,
                    )
                ]
            else:
                paid, outcome = settle_retry_approval(
                    self._payment_retry_repo,
                    self._invoice_repo,
                    payment_order,
                    retried,
                    notification,
                    now,
                )
        else:
            outcome = settle_checkout_payment(
                self._payment_gateway,
                self._payment_order_repo,
                self._invoice_repo,
                payment_order,
                subscription,
                notification.payment_reference,
                now,
                card=notification.card,
            )
            paid = paid_order_invoices(self._invoice_repo, payment_order)

        self._referral_earnings.record_paid_invoices(business, paid)
        payment_order.status = PaymentStatus.APPROVED
        activate_paid_period(self._invoice_repo, subscription, now)
        subscription.updated_at = now
        self._subscription_repo.save(subscription)
        if subscription.status in {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
        }:
            restore_full_service(self._business_repo, business, now)

        return outcome

    def _record_declined_retry(self, change: PaymentStatusChange) -> None:
        """A declined retry changes no bill; its row says it was declined."""

        record_retry_outcome(
            self._payment_retry_repo,
            change.payment_order,
            find_retried_invoice(
                self._payment_retry_repo,
                self._invoice_repo,
                change.payment_order,
                change.subscription,
                change.notification,
            ),
            change.notification,
            PaymentRetryOutcome.DECLINED,
            self._wall_clock.now_unix(),
        )

    def _apply_decline(self, change: PaymentStatusChange) -> None:
        notification, payment_order = change.notification, change.payment_order
        subscription, business = change.subscription, change.business
        now: Microseconds = self._wall_clock.now_unix()
        failed_amount: Money
        if payment_order.is_initial_payment_settled:
            failed_invoice: InvoiceDocument = record_renewal_invoice(
                self._invoice_repo,
                self._issue_due_invoices,
                business,
                subscription,
                InvoiceStatus.FAILED,
                notification.payment_reference,
                now,
                charge=notification,
            )
            failed_amount = invoice_amount(failed_invoice)
            is_trial_over: bool = (
                subscription.status is SubscriptionStatus.TRIALING
                and subscription.trial_ends_at is not None
                and now >= subscription.trial_ends_at
            )
            if subscription.status is SubscriptionStatus.ACTIVE or is_trial_over:
                start_grace_period(self._plan_registry, subscription, business, now)
        else:
            failed_amount = decline_checkout_payment(
                self._invoice_repo,
                payment_order,
                subscription,
                notification.payment_reference,
                now,
            )

        if payment_order.status not in FINAL_ORDER_STATUSES:
            payment_order.status = PaymentStatus.DECLINED

        subscription.updated_at = now
        self._subscription_repo.save(subscription)
        notify_business_owners(
            business,
            self._user_repo,
            self._manager_notifier,
            self._billing_notice_transformer.transform(
                build_payment_failed_notice(business, subscription, failed_amount)
            ),
        )
