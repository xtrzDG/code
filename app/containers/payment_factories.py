"""
Factories of the payment providers: the Stripe client when its settings are
present, and the one payment gateway the use cases see, which routes every
call to Flitt or Stripe by the provider it names.
"""

from typed_time_provider import Microseconds, WallClock

from app.adapters.payments.flitt_payment_gateway_adapter import (
    FlittPaymentGatewayAdapter,
)
from app.adapters.payments.payment_gateway_router_adapter import (
    PaymentGatewayRouterAdapter,
)
from app.adapters.payments.stripe_billing_adapter import StripeBillingAdapter
from app.clients.flitt.flitt_client import FlittClient
from app.clients.stripe.stripe_client import StripeClient
from app.schemas.configurations.app_settings import AppSettings


def build_stripe_client(settings: AppSettings) -> StripeClient | None:
    """Stripe client when its secret key is set (the webhook secret may follow)."""

    if settings.payments.stripe_secret_key is None:
        return None

    return StripeClient(
        secret_key=settings.payments.stripe_secret_key,
        webhook_secret=settings.payments.stripe_webhook_secret,
    )


def build_payment_gateway(
    flitt_client: FlittClient | None,
    stripe_client: StripeClient | None,
    settings: AppSettings,
    wall_clock: WallClock[Microseconds],
) -> PaymentGatewayRouterAdapter:
    return PaymentGatewayRouterAdapter(
        flitt_gateway=FlittPaymentGatewayAdapter(
            flitt_client=flitt_client,
            app_base_url=settings.app_base_url,
            wall_clock=wall_clock,
        ),
        stripe_gateway=StripeBillingAdapter(
            stripe_client=stripe_client,
            cabinet_base_url=settings.cabinet_base_url,
            wall_clock=wall_clock,
        ),
    )
