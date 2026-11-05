"""
Which payment provider charges the businesses of a country: Flitt in
Georgia and Armenia (the concept's auto-debit), Stripe in the European
Union, the United States and Israel. A country of neither region pays
through Flitt, which charges cards from anywhere.
"""

from app.schemas.constants.payments import PaymentProvider
from app.schemas.typings.localization.constrained_strings import CountryCode

FLITT_COUNTRY_CODES: frozenset[CountryCode] = frozenset(
    CountryCode(code) for code in ("AM", "GE")
)
EUROPEAN_UNION_COUNTRY_CODES: frozenset[CountryCode] = frozenset(
    CountryCode(code)
    for code in (
        "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR",
        "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL",
        "PT", "RO", "SE", "SI", "SK",
    )
)  # fmt: skip
STRIPE_COUNTRY_CODES: frozenset[CountryCode] = EUROPEAN_UNION_COUNTRY_CODES | {
    CountryCode("IL"),
    CountryCode("US"),
}
DEFAULT_PAYMENT_PROVIDER: PaymentProvider = PaymentProvider.FLITT


def regional_payment_provider(country_code: CountryCode) -> PaymentProvider:
    """The provider of the country's region, before any configuration."""

    if country_code in FLITT_COUNTRY_CODES:
        return PaymentProvider.FLITT

    if country_code in STRIPE_COUNTRY_CODES:
        return PaymentProvider.STRIPE

    return DEFAULT_PAYMENT_PROVIDER
