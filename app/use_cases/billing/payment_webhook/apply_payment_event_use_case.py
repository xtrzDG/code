from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.billing import (
    PaymentGatewayAdapterContract,
    PaymentOrderRepoContract,
)
from app.contracts.payment_declines import PaymentDeclineWatchFacilitatorContract
from app.contracts.payment_locks import PaymentNotificationLockRegistryContract
from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.constants.payments import PaymentStatus, PaymentWebhookOutcome
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payment_webhooks import PaymentStatusChange
from app.schemas.dto.payments import (
    PaymentMethodNotice,
    PaymentNotification,
    PaymentWebhookReceipt,
    VerifiedPaymentEvent,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.billing.strings import PaymentNotificationKey
from app.use_cases.billing.payment_state_events import log_payment_state_change
from app.use_cases.billing.payment_webhook.card_on_file_recording import (
    build_card_notice_key,
    is_pending_card_setup,
    keep_current_card,
    record_card_references,
    settle_card_setup,
)
from app.use_cases.billing.payment_webhook.payment_order_lookup import (
    find_event_order,
)
from app.use_cases.billing.payment_webhook.payment_order_rules import (
    build_notification_key,
    is_overtaken_approval,
)
from app.utilities.analytics.billing_event_drafts import payment_events


class ApplyPaymentEventUseCase(
    UseCaseContract[VerifiedPaymentEvent, PaymentWebhookReceipt]
):
    """
    Apply a verified payment provider notification (the queued job
    `apply_payment_notification`; the webhooks of Flitt and Stripe only
    verify and queue it, API-03).

    The event says what happened: a payment's status, a saved card, both,
    or neither (IGNORED). The payment order is found by the order id we
    sent (or the parent order of an automatic charge, or the echoed
    merchant data). Each (payment, status) pair and each saved card is
    applied once: the order's applied notification keys are read, checked
    and stored under the order's notification lock, so two copies of one
    notification apply once and the second is a DUPLICATE. A new payment
    status is read back from the provider before it takes effect
    (`confirm_notification`: Flitt's status API for an approval or a
    refund; a ConflictError leaves the order unchanged and the job tries
    again later). An approval delivered after the reversal (a refund or a
    chargeback) of the same payment pays nothing: the refund stands and
    the late approval is recorded as seen (IGNORED).

    - a saved card: the provider's references of the order's charges and
      the card's token (sealed) are kept on the order; a card setup's
      charges become the subscription's; the card becomes the card on
      file (APPLIED) when its order's charges are the ones that run.
    - a payment's status: `ApplyPaymentStatusUseCase` applies it (paid,
      declined and retried invoices, grace, owner notices), and product
      events record what changed. A declined payment (not a retry of a
      declined automatic charge) counts for the business's card-testing
      watch (LOG-05).
    """

    def __init__(
        self,
        payment_gateway: PaymentGatewayAdapterContract,
        notification_lock: PaymentNotificationLockRegistryContract,
        payment_order_repo: PaymentOrderRepoContract,
        subscription_repo: SubscriptionRepoContract,
        business_repo: BusinessRepoContract,
        apply_payment_status: UseCaseContract[
            PaymentStatusChange, PaymentWebhookOutcome
        ],
        secret_cipher: SecretCipherAdapterContract,
        wall_clock: WallClock[Microseconds],
        product_events: RecordProductEventFacilitatorContract,
        payment_declines: PaymentDeclineWatchFacilitatorContract,
    ) -> None:
        self._payment_gateway: PaymentGatewayAdapterContract = payment_gateway
        self._notification_lock: PaymentNotificationLockRegistryContract = (
            notification_lock
        )
        self._payment_order_repo: PaymentOrderRepoContract = payment_order_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._apply_payment_status: UseCaseContract[
            PaymentStatusChange, PaymentWebhookOutcome
        ] = apply_payment_status
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._product_events: RecordProductEventFacilitatorContract = product_events
        self._payment_declines: PaymentDeclineWatchFacilitatorContract = (
            payment_declines
        )

    def run(self, input_data: VerifiedPaymentEvent) -> PaymentWebhookReceipt:
        payment_order: PaymentOrderDocument | None = find_event_order(
            self._payment_order_repo, input_data
        )
        if payment_order is None:
            return PaymentWebhookReceipt(outcome=PaymentWebhookOutcome.IGNORED)

        with self._notification_lock.lock_for_order(
            payment_order.business_id, payment_order.id
        ):
            # Read again under the lock: a copy applied meanwhile is seen.
            current: PaymentOrderDocument = (
                self._payment_order_repo.get(payment_order.id) or payment_order
            )
            return self._apply(input_data.payment, input_data.payment_method, current)

    def _apply(
        self,
        payment: PaymentNotification | None,
        card: PaymentMethodNotice | None,
        payment_order: PaymentOrderDocument,
    ) -> PaymentWebhookReceipt:
        processed: list[PaymentNotificationKey] = (
            payment_order.processed_notification_keys
        )
        new_card: PaymentMethodNotice | None = (
            card
            if card is not None and build_card_notice_key(card) not in processed
            else None
        )
        new_payment: PaymentNotification | None = (
            payment
            if payment is not None and build_notification_key(payment) not in processed
            else None
        )
        if new_card is None and new_payment is None:
            return PaymentWebhookReceipt(
                outcome=PaymentWebhookOutcome.DUPLICATE,
                payment_order_id=payment_order.id,
            )

        if new_payment is not None and is_overtaken_approval(new_payment, processed):
            return self._skip_overtaken(new_payment, new_card, payment_order)

        status_before: PaymentStatus = payment_order.status
        business: BusinessDocument | None = self._business_repo.get(
            payment_order.business_id
        )
        subscription: SubscriptionDocument | None = self._subscription_repo.get(
            payment_order.business_id, payment_order.subscription_id
        )
        if business is None or subscription is None:
            raise NotFoundError("The subscription of this payment was not found.")

        if new_payment is not None:
            self._payment_gateway.confirm_notification(new_payment)

        outcome: PaymentWebhookOutcome = PaymentWebhookOutcome.IGNORED
        if new_card is not None:
            outcome = self._record_card(new_card, payment_order, subscription)

        if new_payment is not None:
            outcome = self._apply_payment(
                new_payment, payment_order, subscription, business, outcome
            )

        now: Microseconds = self._wall_clock.now_unix()
        if new_card is not None:
            if new_card.summary is not None and (
                keep_current_card(subscription, payment_order, new_card.summary)
                and outcome is PaymentWebhookOutcome.IGNORED
            ):
                outcome = PaymentWebhookOutcome.APPLIED

            processed.append(build_card_notice_key(new_card))
            subscription.updated_at = now
            self._subscription_repo.save(subscription)

        payment_order.updated_at = now
        self._payment_order_repo.save(payment_order)
        log_payment_state_change(
            payment_order,
            status_before,
            None if new_payment is None else new_payment.status,
            outcome,
        )
        return PaymentWebhookReceipt(outcome=outcome, payment_order_id=payment_order.id)

    def _apply_payment(
        self,
        payment: PaymentNotification,
        payment_order: PaymentOrderDocument,
        subscription: SubscriptionDocument,
        business: BusinessDocument,
        outcome: PaymentWebhookOutcome,
    ) -> PaymentWebhookOutcome:
        previous_status: SubscriptionStatus = subscription.status
        payment_outcome: PaymentWebhookOutcome = self._apply_payment_status.run(
            PaymentStatusChange(
                notification=payment,
                payment_order=payment_order,
                subscription=subscription,
                business=business,
            )
        )
        self._product_events.record(
            *payment_events(
                payment.status, payment_outcome, previous_status, subscription
            )
        )
        if payment.status is PaymentStatus.DECLINED and not payment.is_retry:
            self._payment_declines.record_decline(payment_order.business_id)

        payment_order.processed_notification_keys.append(
            build_notification_key(payment)
        )
        if payment.payment_reference is not None:
            payment_order.last_payment_reference = payment.payment_reference

        if payment.failure_reason is not None:
            payment_order.last_failure_reason = payment.failure_reason

        if payment_outcome is PaymentWebhookOutcome.IGNORED:
            return outcome

        return payment_outcome

    def _skip_overtaken(
        self,
        payment: PaymentNotification,
        card: PaymentMethodNotice | None,
        payment_order: PaymentOrderDocument,
    ) -> PaymentWebhookReceipt:
        """A late approval of a reversed payment: seen, nothing paid or saved."""

        payment_order.processed_notification_keys.append(
            build_notification_key(payment)
        )
        if card is not None:
            payment_order.processed_notification_keys.append(
                build_card_notice_key(card)
            )

        payment_order.updated_at = self._wall_clock.now_unix()
        self._payment_order_repo.save(payment_order)
        log_payment_state_change(
            payment_order,
            payment_order.status,
            payment.status,
            PaymentWebhookOutcome.IGNORED,
        )
        return PaymentWebhookReceipt(
            outcome=PaymentWebhookOutcome.IGNORED, payment_order_id=payment_order.id
        )

    def _record_card(
        self,
        card: PaymentMethodNotice,
        payment_order: PaymentOrderDocument,
        subscription: SubscriptionDocument,
    ) -> PaymentWebhookOutcome:
        record_card_references(card, payment_order, self._secret_cipher)
        if not is_pending_card_setup(payment_order):
            return PaymentWebhookOutcome.IGNORED

        settle_card_setup(
            self._payment_gateway, self._payment_order_repo, payment_order, subscription
        )
        return PaymentWebhookOutcome.APPLIED
