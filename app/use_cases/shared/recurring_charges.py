"""Stop the automatic charges a subscription runs at its payment provider."""

from app.contracts.billing import PaymentGatewayAdapterContract
from app.schemas.constants.payments import PaymentProvider
from app.schemas.domain.billing import SubscriptionDocument


def stop_recurring_charges(
    payment_gateway: PaymentGatewayAdapterContract,
    subscription: SubscriptionDocument,
) -> None:
    """
    Stop the charges at the provider that runs them (rows from before
    Stripe are Flitt's) and forget their card: a new checkout or card
    setup starts the next schedule. Nothing runs, nothing happens. The
    caller saves the subscription.
    """

    if subscription.provider_reference is None:
        return

    payment_gateway.stop_recurring(
        subscription.payment_provider or PaymentProvider.FLITT,
        subscription.provider_reference,
    )
    subscription.provider_reference = None
    subscription.payment_method_summary = None
