"""The card of a Stripe payment method, as the card on file keeps it."""

from typing import cast

from typed_time_provider import Microseconds

from app.schemas.constants.payments import PaymentProvider
from app.schemas.domain.payment_methods import PaymentMethodSummary
from app.schemas.typings.billing.constrained_integers import (
    PaymentCardExpiryMonth,
    PaymentCardExpiryYear,
)
from app.schemas.typings.invoicing.constrained_strings import PaymentCardLastDigits
from app.schemas.typings.invoicing.strings import PaymentCardBrand

MICROSECONDS_PER_SECOND: int = 1_000_000
MAX_CARD_BRAND_LENGTH: int = 30


def read_stripe_card(
    payment_method: object, saved_at_seconds: int
) -> PaymentMethodSummary | None:
    """Brand, last four digits and expiry of a card payment method."""

    if not isinstance(payment_method, dict):
        return None

    card: object = cast(dict[str, object], payment_method).get("card")
    if not isinstance(card, dict):
        return None

    fields: dict[str, object] = cast(dict[str, object], card)
    return PaymentMethodSummary(
        provider=PaymentProvider.STRIPE,
        brand=read_brand(fields.get("brand")),
        last_digits=read_last_digits(fields.get("last4")),
        expiry_month=read_number(fields.get("exp_month"), PaymentCardExpiryMonth),
        expiry_year=read_number(fields.get("exp_year"), PaymentCardExpiryYear),
        saved_at=Microseconds(saved_at_seconds * MICROSECONDS_PER_SECOND),
    )


def read_brand(raw_brand: object) -> PaymentCardBrand | None:
    if not isinstance(raw_brand, str) or raw_brand.strip() == "":
        return None

    return PaymentCardBrand(raw_brand.strip().upper()[:MAX_CARD_BRAND_LENGTH])


def read_last_digits(raw_digits: object) -> PaymentCardLastDigits | None:
    if not isinstance(raw_digits, str):
        return None

    try:
        return PaymentCardLastDigits(raw_digits)
    except ValueError:
        return None


def read_number[Number: (PaymentCardExpiryMonth, PaymentCardExpiryYear)](
    raw_number: object, number_type: type[Number]
) -> Number | None:
    if isinstance(raw_number, bool) or not isinstance(raw_number, int):
        return None

    try:
        return number_type(raw_number)
    except ValueError:
        return None
