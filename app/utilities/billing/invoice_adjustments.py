"""
What comes off an invoice's price before tax: the client's discount, then
the credit the platform team granted.

The discount is the price times its percent, rounded once, half up, to the
currency's smallest unit; the credit used is what the client has, up to the
price left after the discount. The subtotal (what the VAT is computed on)
is the price minus both, so `price = discount + credit + subtotal` holds to
the unit, and a credit never takes the subtotal below zero.

Example: 517.00 GEL with 30 % off and 100.00 GEL of credit is 155.10 off,
100.00 of credit and a subtotal of 261.90 (VAT then goes on top of it).
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from typed_time_provider import Microseconds

from app.schemas.constants.billing import InvoiceKind
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.typings.billing.constrained_integers import ClientDiscountPercent

PERCENT_IN_WHOLE: Decimal = Decimal(100)
WHOLE_MINOR_UNIT: Decimal = Decimal(1)


@dataclass(frozen=True)
class PriceAdjustment:
    """An invoice price split into its discount, its credit and the rest."""

    discount_percent: ClientDiscountPercent | None
    discount_minor: int
    credit_minor: int
    subtotal_minor: int


def discount_amount(price_minor: int, percent: ClientDiscountPercent) -> int:
    """51700 at 30 % -> 15510; 999 at 15 % -> 150 (149.85, half up)."""

    return int(
        (Decimal(price_minor) * Decimal(int(percent)) / PERCENT_IN_WHOLE).quantize(
            WHOLE_MINOR_UNIT, rounding=ROUND_HALF_UP
        )
    )


def discount_for_period(
    subscription: SubscriptionDocument,
    kind: InvoiceKind,
    period_start: Microseconds,
) -> ClientDiscountPercent | None:
    """
    The client's discount on a service period that starts before the
    discount ends; setup fees and overage are never discounted.
    """

    discount = subscription.discount
    if (
        discount is None
        or kind is not InvoiceKind.SERVICE_PERIOD
        or int(period_start) >= int(discount.ends_at)
    ):
        return None

    return discount.percent


def adjust_price(
    price_minor: int,
    discount_percent: ClientDiscountPercent | None,
    available_credit_minor: int,
) -> PriceAdjustment:
    """The discount first, then as much credit as the rest of the price takes."""

    discount: int = 0
    if discount_percent is not None:
        discount = discount_amount(price_minor, discount_percent)

    after_discount: int = max(0, price_minor - discount)
    credit: int = max(0, min(available_credit_minor, after_discount))
    return PriceAdjustment(
        discount_percent=discount_percent if discount > 0 else None,
        discount_minor=discount,
        credit_minor=credit,
        subtotal_minor=after_discount - credit,
    )
