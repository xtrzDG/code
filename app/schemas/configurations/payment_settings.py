from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.platform.strings import PlatformSecret


class PaymentSettings(ImmutableDTO):
    """
    Stripe, the payment provider of owners in the EU, the US and Israel
    (Flitt's are FLITT_*):

    - `stripe_secret_key` (STRIPE_SECRET_KEY): the account's restricted or
      secret API key; without it nobody is routed to Stripe;
    - `stripe_webhook_secret` (STRIPE_WEBHOOK_SECRET): the signing secret
      of the webhook endpoint `/v1/payments/stripe/webhook`; without it
      every Stripe notification is refused, so nothing is marked paid
      unverified.

    Owners are routed to Stripe only when both are set and the
    `stripe_payments` release gate is open (docs/LAUNCH.md).
    """

    stripe_secret_key: PlatformSecret | None = Field(default=None, repr=False)
    stripe_webhook_secret: PlatformSecret | None = Field(default=None, repr=False)
