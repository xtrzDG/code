from typed_time_provider import Microseconds, WallClock

from app.contracts.billing import (
    PaymentGatewayAdapterContract,
    PaymentOrderRepoContract,
)
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
from app.schemas.constants.billing import (
    BillingNoticeKind,
    InvoiceKind,
    InvoiceStatus,
    SubscriptionStatus,
)
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.payments import PaymentStatus, PaymentWebhookOutcome
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.dto.billing_ledger import BillingNotice, DueInvoicesRequest
from app.schemas.dto.payments import (
    PaymentNotification,
    PaymentWebhookDelivery,
    PaymentWebhookReceipt,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.billing.strings import (
    PaymentNotificationKey,
    PaymentProviderReference,
)
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.billing.billing_records import (
    OPEN_INVOICE_STATUSES,
    find_covering_paid_invoice,
    find_next_period_start,
    list_subscription_invoices,
)
from app.use_cases.billing.owner_notifications import notify_business_owners
from app.utilities.billing.billing_periods import add_local_days

FINAL_ORDER_STATUSES: frozenset[PaymentStatus] = frozenset(
    {PaymentStatus.APPROVED, PaymentStatus.REVERSED}
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
        payment_order: PaymentOrderDocument = self._find_payment_order(notification)
        notification_key = PaymentNotificationKey(
            f"{notification.payment_reference or notification.order_reference}"
            f":{notification.status.value}"
        )
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

    def _find_payment_order(
        self,
        notification: PaymentNotification,
    ) -> PaymentOrderDocument:
        for reference in (
            notification.order_reference,
            notification.parent_order_reference,
            notification.merchant_reference,
        ):
            payment_order_id: PaymentOrderId | None = parse_payment_order_id(reference)
            if payment_order_id is None:
                continue

            payment_order: PaymentOrderDocument | None = self._payment_order_repo.get(
                payment_order_id
            )
            if payment_order is not None:
                return payment_order

        raise NotFoundError("Payment order was not found.")

    def _apply(
        self,
        notification: PaymentNotification,
        payment_order: PaymentOrderDocument,
        subscription: SubscriptionDocument,
        business: BusinessDocument,
    ) -> PaymentWebhookOutcome:
        match notification.status:
            case PaymentStatus.APPROVED:
                self._require_expected_amount(notification, payment_order)
                if self._is_stray_charge(payment_order, subscription):
                    self._stop_stray_schedule(payment_order)
                    payment_order.is_refund_due = True
                    return PaymentWebhookOutcome.REFUND_DUE

                return self._apply_approval(
                    notification, payment_order, subscription, business
                )
            case PaymentStatus.DECLINED:
                if self._is_stray_charge(payment_order, subscription):
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

    def _require_expected_amount(
        self,
        notification: PaymentNotification,
        payment_order: PaymentOrderDocument,
    ) -> None:
        expected_amount: int = int(
            payment_order.recurring_amount_minor
            if payment_order.is_initial_payment_settled
            else payment_order.amount_minor
        )
        amount: Money | None = notification.amount
        if (
            amount is None
            or amount.currency_code != payment_order.currency_code
            or int(amount.amount_minor) != expected_amount
        ):
            raise ValidationFailedError(
                "The approved amount does not match the payment order."
            )

    def _is_stray_charge(
        self,
        payment_order: PaymentOrderDocument,
        subscription: SubscriptionDocument,
    ) -> bool:
        """
        An automatic charge of a schedule the subscription no longer uses:
        replaced by a later checkout, stopped by a plan change, or of a
        cancelled subscription.
        """

        return payment_order.is_initial_payment_settled and (
            subscription.status is SubscriptionStatus.CANCELLED
            or subscription.provider_reference != build_order_reference(payment_order)
        )

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
            self._record_renewal(
                business,
                subscription,
                InvoiceStatus.PAID,
                notification.payment_reference,
                now,
            )
        else:
            order_reference: PaymentProviderReference = build_order_reference(
                payment_order
            )
            previous_reference: PaymentProviderReference | None = (
                subscription.provider_reference
            )
            if previous_reference is not None and previous_reference != order_reference:
                self._payment_gateway.stop_recurring(previous_reference)

            settled_count: int = self._settle_order_invoices(
                payment_order,
                InvoiceStatus.PAID,
                notification.payment_reference,
                now,
            )
            if settled_count == 0:
                payment_order.is_refund_due = True
                outcome = PaymentWebhookOutcome.REFUND_DUE

            payment_order.is_initial_payment_settled = True
            subscription.provider_reference = order_reference
            self._resume_cancelled(subscription, now)

        payment_order.status = PaymentStatus.APPROVED
        self._activate_paid_period(subscription, now)
        subscription.updated_at = now
        self._subscription_repo.save(subscription)
        if subscription.status in {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
        } and (business.service_mode is not ServiceMode.FULL):
            business.service_mode = ServiceMode.FULL
            business.updated_at = now
            self._business_repo.save(business)

        return outcome

    def _resume_cancelled(
        self,
        subscription: SubscriptionDocument,
        now: Microseconds,
    ) -> None:
        """
        A checkout paid after cancelling resumes the subscription: the trial
        while it still runs, otherwise the paid period (see below).
        """

        if subscription.status is not SubscriptionStatus.CANCELLED:
            return

        if subscription.trial_ends_at is not None and now < subscription.trial_ends_at:
            subscription.status = SubscriptionStatus.TRIALING

    def _activate_paid_period(
        self,
        subscription: SubscriptionDocument,
        now: Microseconds,
    ) -> None:
        is_trial_running: bool = (
            subscription.status is SubscriptionStatus.TRIALING
            and subscription.trial_ends_at is not None
            and now < subscription.trial_ends_at
        )
        if is_trial_running:
            return

        covering: InvoiceDocument | None = find_covering_paid_invoice(
            list_subscription_invoices(self._invoice_repo, subscription),
            now,
        )
        if covering is None:
            return

        subscription.status = SubscriptionStatus.ACTIVE
        subscription.period_start = covering.period_start
        subscription.period_end = covering.period_end
        subscription.grace_until = None

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
            failed_invoice: InvoiceDocument = self._record_renewal(
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
                self._start_grace(subscription, business, now)
        else:
            self._settle_order_invoices(
                payment_order,
                InvoiceStatus.FAILED,
                notification.payment_reference,
                now,
            )
            failed_amount = Money(
                amount_minor=payment_order.amount_minor,
                currency_code=payment_order.currency_code,
            )

        if payment_order.status not in FINAL_ORDER_STATUSES:
            payment_order.status = PaymentStatus.DECLINED

        subscription.updated_at = now
        self._subscription_repo.save(subscription)
        self._notify_owners(
            business,
            BillingNotice(
                kind=BillingNoticeKind.PAYMENT_FAILED,
                language=business.owner_language,
                timezone=business.timezone,
                business_name=business.name,
                amount=failed_amount,
                deadline=(
                    subscription.grace_until
                    if subscription.status is SubscriptionStatus.PAST_DUE
                    else None
                ),
            ),
        )

    def _record_renewal(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        status: InvoiceStatus,
        payment_reference: PaymentProviderReference | None,
        now: Microseconds,
    ) -> InvoiceDocument:
        """
        Invoice of the period an automatic charge was for. An invoice that
        already carries this provider payment is reused (a declined charge
        later approved becomes PAID), so a repeated delivery never bills a
        second period.
        """

        invoices: list[InvoiceDocument] = list_subscription_invoices(
            self._invoice_repo,
            subscription,
        )
        for invoice in invoices:
            if (
                payment_reference is None
                or invoice.kind is not InvoiceKind.SERVICE_PERIOD
                or invoice.provider_reference != payment_reference
            ):
                continue

            if status is InvoiceStatus.PAID and invoice.status in OPEN_INVOICE_STATUSES:
                invoice.status = InvoiceStatus.PAID
                invoice.updated_at = now
                self._invoice_repo.save(invoice)

            return invoice

        return self._issue_due_invoices.run(
            DueInvoicesRequest(
                business=business,
                subscription=subscription,
                period_start=find_next_period_start(subscription, invoices),
                status=status,
                payment_reference=payment_reference,
            )
        )[-1]

    def _start_grace(
        self,
        subscription: SubscriptionDocument,
        business: BusinessDocument,
        now: Microseconds,
    ) -> None:
        plan: PlanDefinition = self._plan_registry.get(subscription.plan_key)
        subscription.status = SubscriptionStatus.PAST_DUE
        subscription.grace_until = add_local_days(
            now,
            int(plan.grace_period_days),
            business.timezone,
        )

    def _settle_order_invoices(
        self,
        payment_order: PaymentOrderDocument,
        status: InvoiceStatus,
        payment_reference: PaymentProviderReference | None,
        now: Microseconds,
    ) -> int:
        """
        Mark the checkout's invoices and return how many changed. A payment
        is money received, so an approved payment marks even a voided
        invoice as paid; a decline touches open invoices only.
        """

        changed_count: int = 0
        for invoice_id in payment_order.invoice_ids:
            invoice: InvoiceDocument | None = self._invoice_repo.get(
                payment_order.business_id,
                invoice_id,
            )
            if invoice is None or invoice.status is InvoiceStatus.PAID:
                continue

            if status is InvoiceStatus.FAILED and (
                invoice.status not in OPEN_INVOICE_STATUSES
            ):
                continue

            invoice.status = status
            if payment_reference is not None:
                invoice.provider_reference = payment_reference

            invoice.updated_at = now
            self._invoice_repo.save(invoice)
            changed_count += 1

        return changed_count

    def _notify_owners(self, business: BusinessDocument, notice: BillingNotice) -> None:
        notify_business_owners(
            business,
            self._user_repo,
            self._manager_notifier,
            self._billing_notice_transformer.transform(notice),
        )


def build_order_reference(
    payment_order: PaymentOrderDocument,
) -> PaymentProviderReference:
    """Provider reference of the automatic charges a checkout started."""

    return PaymentProviderReference(str(payment_order.id))


def parse_payment_order_id(
    reference: PaymentProviderReference | None,
) -> PaymentOrderId | None:
    """Our payment order id inside a provider reference, if it is one."""

    if reference is None:
        return None

    try:
        return PaymentOrderId(str(reference))
    except TypeError, ValueError:
        return None
