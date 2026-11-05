from app.contracts.payment_methods import PaymentProviderRegistryContract
from app.registries.billing.payment_regions import (
    DEFAULT_PAYMENT_PROVIDER,
    regional_payment_provider,
)
from app.schemas.configurations.payment_settings import PaymentSettings
from app.schemas.constants.payments import PaymentProvider
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.utilities.storage.release_gates import STRIPE_PAYMENTS_GATE, is_gate_open


class PaymentProviderRegistry(PaymentProviderRegistryContract):
    """
    The payment provider of a business by its country (`payment_regions`):
    Flitt for Georgia and Armenia, Stripe for the EU, the US and Israel.

    Stripe is chosen only while it is configured (STRIPE_SECRET_KEY and
    STRIPE_WEBHOOK_SECRET) and the `stripe_payments` release gate is open,
    since until then the previous release could not read a Stripe order;
    otherwise those owners keep paying through Flitt.
    """

    def __init__(self, payment_settings: PaymentSettings) -> None:
        self._is_stripe_configured: bool = (
            payment_settings.stripe_secret_key is not None
            and payment_settings.stripe_webhook_secret is not None
        )

    def select(self, country_code: CountryCode) -> PaymentProvider:
        provider: PaymentProvider = regional_payment_provider(country_code)
        if provider is PaymentProvider.STRIPE and not self._is_stripe_available():
            return DEFAULT_PAYMENT_PROVIDER

        return provider

    def _is_stripe_available(self) -> bool:
        return self._is_stripe_configured and bool(is_gate_open(STRIPE_PAYMENTS_GATE))
