from typed_time_provider import Microseconds, WallClock

from app.contracts.billing import (
    PaymentGatewayAdapterContract,
    PaymentOrderRepoContract,
)
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
from app.schemas.constants.billing import InvoiceStatus, SubscriptionStatus
from app.schemas.constants.payments import PaymentStatus, PaymentWebhookOutcome
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.billing_ledger import BillingNotice, DueInvoicesRequest
from app.schemas.dto.payments import (
    PaymentNotification,
    PaymentWebhookDelivery,
    PaymentWebhookReceipt,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.billing.strings import PaymentNotificationKey
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.billing.grace_periods import start_grace_period
from app.use_cases.billing.owner_notifications import notify_business_owners
from app.use_cases.billing.payment_webhook.checkout_payment_settlement import (
    decline_checkout_payment,
    settle_checkout_payment,
)
from app.use_cases.billing.payment_webhook.payment_failure_notice import (
    build_payment_failed_notice,
)
from app.use_cases.billing.payment_webhook.payment_invoice_settlement import (
    record_renewal_invoice,
)
from app.use_cases.billing.payment_webhook.payment_order_lookup import (
    find_payment_order,
)
from app.use_cases.billing.payment_webhook.payment_order_rules import (
    FINAL_ORDER_STATUSES,
    build_notification_key,
    build_order_reference,
    is_stray_charge,
    require_expected_amount,
)
from app.use_cases.billing.payment_webhook.service_mode_restoration import (
    restore_full_service,
)
from app.use_cases.billing.payment_webhook.subscription_payment_transitions import (
    activate_paid_period,
)


class ProcessPaymentWebhookUseCase(
    UseCaseContract[PaymentWebhookDelivery, PaymentWebhookReceipt]
):
    """
    Apply a payment provider notification (POST /v1/payments/flitt/webhook).

    The gateway verifies the signature first; the payment order is found by
    the order id we sent (or the parent order of an automatic charge, or the
    echoed merchant data). Each (payment, status) pair is applied once, so
    repeated notifications answer DUPLICATE and change nothing.

    - approved, first payment of a checkout: its invoices become PAID and
      the card's automatic charges are remembered; the automatic charges of
      an earlier checkout are stopped, so only one schedule ever runs. The
      subscription becomes ACTIVE for the paid period that has started (a
      trial paid ahead stays in trial until it ends; a cancelled one is
      resumed), grace ends and the assistant serves in full. A payment that
      settles no bill (the bills were already paid) is marked for refund.
    - approved, later automatic charge of the current schedule: the next
      period is invoiced as PAID and becomes current once it starts.
    - an automatic charge of any other schedule (replaced, stopped, or of a
      cancelled subscription) is never booked as service: its schedule is
      stopped and an approved charge is marked for refund (REFUND_DUE).
    - declined: first payment - its invoices become FAILED; automatic
      charge - the next period is invoiced as FAILED and an active
      subscription becomes PAST_DUE with grace until now + the plan's grace
      days. Owners are told either way.
    - expired, created, processing, reversed: recorded on the payment order
      only (a reversal is handled by the platform admin).
    """

    def __init__(
        self,
        payment_gateway: PaymentGatewayAdapterContract,
        payment_order_repo: PaymentOrderRepoContract,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        plan_registry: PlanRegistryContract,
        issue_due_invoices: UseCaseContract[DueInvoicesRequest, list[InvoiceDocument]],
        manager_notifier: ManagerNotificationFacilitatorContract,
        billing_notice_transformer: TransformerContract[BillingNotice, MessageText],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._payment_gateway: PaymentGatewayAdapterContract = payment_gateway
        self._payment_order_repo: PaymentOrderRepoContract = payment_order_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._business_repo: BusinessRepoContract = business_repo
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

    def run(self, input_data: PaymentWebhookDelivery) -> PaymentWebhookReceipt:
        notification: PaymentNotification = self._payment_gateway.read_notification(
            input_data
        )
        payment_order: PaymentOrderDocument = find_payment_order(
            self._payment_order_repo, notification
        )
        notification_key: PaymentNotificationKey = build_notification_key(notification)
        if notification_key in payment_order.processed_notification_keys:
            return PaymentWebhookReceipt(
                outcome=PaymentWebhookOutcome.DUPLICATE,
                payment_order_id=payment_order.id,
            )

        business: BusinessDocument | None = self._business_repo.get(
            payment_order.business_id
        )
        subscription: SubscriptionDocument | None = self._subscription_repo.get(
            payment_order.business_id,
            payment_order.subscription_id,
        )
        if business is None or subscription is None:
            raise NotFoundError("The subscription of this payment was not found.")

        outcome: PaymentWebhookOutcome = self._apply(
            notification,
            payment_order,
            subscription,
            business,
        )
        now: Microseconds = self._wall_clock.now_unix()
        payment_order.processed_notification_keys.append(notification_key)
        if notification.payment_reference is not None:
            payment_order.last_payment_reference = notification.payment_reference

        if notification.failure_reason is not None:
            payment_order.last_failure_reason = notification.failure_reason

        payment_order.updated_at = now
        self._payment_order_repo.save(payment_order)
        return PaymentWebhookReceipt(
            outcome=outcome,
            payment_order_id=payment_order.id,
        )

    def _apply(
        self,
        notification: PaymentNotification,
        payment_order: PaymentOrderDocument,
        subscription: SubscriptionDocument,
        business: BusinessDocument,
    ) -> PaymentWebhookOutcome:
        match notification.status:
            case PaymentStatus.APPROVED:
                require_expected_amount(notification, payment_order)
                if is_stray_charge(payment_order, subscription):
                    self._stop_stray_schedule(payment_order)
                    payment_order.is_refund_due = True
                    return PaymentWebhookOutcome.REFUND_DUE

                return self._apply_approval(
                    notification, payment_order, subscription, business
                )
            case PaymentStatus.DECLINED:
                if is_stray_charge(payment_order, subscription):
                    self._stop_stray_schedule(payment_order)
                    return PaymentWebhookOutcome.IGNORED

                self._apply_decline(notification, payment_order, subscription, business)
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

    def _stop_stray_schedule(self, payment_order: PaymentOrderDocument) -> None:
        self._payment_gateway.stop_recurring(build_order_reference(payment_order))

    def _apply_approval(
        self,
        notification: PaymentNotification,
        payment_order: PaymentOrderDocument,
        subscription: SubscriptionDocument,
        business: BusinessDocument,
    ) -> PaymentWebhookOutcome:
        now: Microseconds = self._wall_clock.now_unix()
        outcome: PaymentWebhookOutcome = PaymentWebhookOutcome.APPLIED
        if payment_order.is_initial_payment_settled:
            record_renewal_invoice(
                self._invoice_repo,
                self._issue_due_invoices,
                business,
                subscription,
                InvoiceStatus.PAID,
                notification.payment_reference,
                now,
            )
        else:
            outcome = settle_checkout_payment(
                self._payment_gateway,
                self._invoice_repo,
                payment_order,
                subscription,
                notification.payment_reference,
                now,
            )

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

    def _apply_decline(
        self,
        notification: PaymentNotification,
        payment_order: PaymentOrderDocument,
        subscription: SubscriptionDocument,
        business: BusinessDocument,
    ) -> None:
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
            )
            failed_amount = Money(
                amount_minor=failed_invoice.amount_minor,
                currency_code=failed_invoice.currency_code,
            )
            if subscription.status is SubscriptionStatus.ACTIVE:
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
