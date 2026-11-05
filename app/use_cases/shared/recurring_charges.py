"""Stop the automatic charges a subscription runs at its payment provider."""

from app.contracts.billing import (
    PaymentGatewayAdapterContract,
    PaymentOrderRepoContract,
)
from app.schemas.constants.payments import PaymentProvider
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.typings.billing.prefixed_id import PaymentOrderId


def stop_recurring_charges(
    payment_gateway: PaymentGatewayAdapterContract,
    payment_order_repo: PaymentOrderRepoContract,
    subscription: SubscriptionDocument,
    *,
    keep_order_id: PaymentOrderId | None = None,
) -> None:
    """
    Stop the charges at the provider that runs them (rows from before
    Stripe are Flitt's) and forget their card: the card summary and every
    saved card token of the subscription's orders (a token can charge the
    card again), except the order `keep_order_id` whose card replaces
    them. A new checkout or card setup starts the next schedule. Nothing
    runs, nothing happens. The caller saves the subscription.
    """

    if subscription.provider_reference is None:
        return

    payment_gateway.stop_recurring(
        subscription.payment_provider or PaymentProvider.FLITT,
        subscription.provider_reference,
    )
    subscription.provider_reference = None
    subscription.payment_method_summary = None
    forget_card_tokens(payment_order_repo, subscription, keep_order_id)


def forget_card_tokens(
    payment_order_repo: PaymentOrderRepoContract,
    subscription: SubscriptionDocument,
    keep_order_id: PaymentOrderId | None = None,
) -> None:
    """Drop the sealed card tokens of the subscription's orders, but one."""

    def drop_token(order: PaymentOrderDocument) -> PaymentOrderDocument | None:
        if order.sealed_card_token is None:
            return None

        order.sealed_card_token = None
        return order

    for order in payment_order_repo.list_by_business(subscription.business_id):
        if (
            order.subscription_id == subscription.id
            and order.id != keep_order_id
            and order.sealed_card_token is not None
        ):
            payment_order_repo.update(order.business_id, order.id, drop_token)
