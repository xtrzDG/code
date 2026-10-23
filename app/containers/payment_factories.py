"""
The Stripe client when its settings are present (the payment gateway that
routes every call to Flitt or Stripe, each behind its circuit, is built with
the provider resilience: app/containers/adapters/provider_resilience.py).
"""

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
