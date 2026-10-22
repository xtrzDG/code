from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.billing import (
    PaymentGatewayAdapterContract,
    PaymentOrderRepoContract,
)
from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.constants.payments import PaymentWebhookOutcome
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payment_webhooks import PaymentStatusChange
from app.schemas.dto.payments import (
    PaymentMethodNotice,
    PaymentNotification,
    PaymentWebhookDelivery,
    PaymentWebhookReceipt,
    VerifiedPaymentEvent,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.billing.strings import PaymentNotificationKey
from app.use_cases.billing.payment_webhook.card_on_file_recording import (
    build_card_notice_key,
    is_pending_card_setup,
    keep_current_card,
    record_card_references,
    settle_card_setup,
)
from app.use_cases.billing.payment_webhook.payment_order_lookup import (
    find_payment_order,
    find_payment_order_by_reference,
)
from app.use_cases.billing.payment_webhook.payment_order_rules import (
    build_notification_key,
)
from app.utilities.analytics.billing_event_drafts import payment_events


class ProcessPaymentWebhookUseCase(
    UseCaseContract[PaymentWebhookDelivery, PaymentWebhookReceipt]
):
    """
    Apply a payment provider notification (POST /v1/payments/flitt/webhook
    and POST /v1/payments/stripe/webhook).

    The gateway verifies the signature first and says what the event is:
    a payment's status, a saved card, both, or neither (IGNORED). The
    payment order is found by the order id we sent (or the parent order of
    an automatic charge, or the echoed merchant data). Each (payment,
    status) pair and each saved card is applied once.

    - a saved card: the provider's references of the order's charges and
      the card's token (sealed) are kept on the order; a card setup's
      charges become the subscription's; the card becomes the card on
      file (APPLIED) when its order's charges are the ones that run.
    - a payment's status: `ApplyPaymentStatusUseCase` applies it (paid,
      declined and retried invoices, grace, owner notices), and product
      events record what changed.
    """

    def __init__(
        self,
        payment_gateway: PaymentGatewayAdapterContract,
        payment_order_repo: PaymentOrderRepoContract,
        subscription_repo: SubscriptionRepoContract,
        business_repo: BusinessRepoContract,
        apply_payment_status: UseCaseContract[
            PaymentStatusChange, PaymentWebhookOutcome
        ],
        secret_cipher: SecretCipherAdapterContract,
        wall_clock: WallClock[Microseconds],
        product_events: RecordProductEventFacilitatorContract,
    ) -> None:
        self._payment_gateway: PaymentGatewayAdapterContract = payment_gateway
        self._payment_order_repo: PaymentOrderRepoContract = payment_order_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._apply_payment_status: UseCaseContract[
            PaymentStatusChange, PaymentWebhookOutcome
        ] = apply_payment_status
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._product_events: RecordProductEventFacilitatorContract = product_events

    def run(self, input_data: PaymentWebhookDelivery) -> PaymentWebhookReceipt:
        event: VerifiedPaymentEvent = self._payment_gateway.read_notification(
            input_data
        )
        payment: PaymentNotification | None = event.payment
        card: PaymentMethodNotice | None = event.payment_method
        if payment is not None:
            payment_order: PaymentOrderDocument = find_payment_order(
                self._payment_order_repo, payment
            )
        elif card is not None:
            payment_order = find_payment_order_by_reference(
                self._payment_order_repo, card.order_reference
            )
        else:
            return PaymentWebhookReceipt(outcome=PaymentWebhookOutcome.IGNORED)

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

        business: BusinessDocument | None = self._business_repo.get(
            payment_order.business_id
        )
        subscription: SubscriptionDocument | None = self._subscription_repo.get(
            payment_order.business_id, payment_order.subscription_id
        )
        if business is None or subscription is None:
            raise NotFoundError("The subscription of this payment was not found.")

        outcome: PaymentWebhookOutcome = PaymentWebhookOutcome.IGNORED
        if new_card is not None:
            outcome = self._record_card(new_card, payment_order, subscription)

        if new_payment is not None:
            previous_status: SubscriptionStatus = subscription.status
            payment_outcome: PaymentWebhookOutcome = self._apply_payment_status.run(
                PaymentStatusChange(
                    notification=new_payment,
                    payment_order=payment_order,
                    subscription=subscription,
                    business=business,
                )
            )
            self._product_events.record(
                *payment_events(
                    new_payment.status, payment_outcome, previous_status, subscription
                )
            )
            if payment_outcome is not PaymentWebhookOutcome.IGNORED:
                outcome = payment_outcome

            processed.append(build_notification_key(new_payment))
            if new_payment.payment_reference is not None:
                payment_order.last_payment_reference = new_payment.payment_reference

            if new_payment.failure_reason is not None:
                payment_order.last_failure_reason = new_payment.failure_reason

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
        return PaymentWebhookReceipt(outcome=outcome, payment_order_id=payment_order.id)

    def _record_card(
        self,
        card: PaymentMethodNotice,
        payment_order: PaymentOrderDocument,
        subscription: SubscriptionDocument,
    ) -> PaymentWebhookOutcome:
        record_card_references(card, payment_order, self._secret_cipher)
        if not is_pending_card_setup(payment_order):
            return PaymentWebhookOutcome.IGNORED

        settle_card_setup(self._payment_gateway, payment_order, subscription)
        return PaymentWebhookOutcome.APPLIED
