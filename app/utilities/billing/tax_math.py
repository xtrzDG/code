"""
VAT on a price in minor units: the tax is the price times the rate,
rounded once, half up, to the currency's smallest unit (two digits for GEL
and EUR, none for JPY, three for KWD), and the total is their sum, so
subtotal + tax = total always holds to the unit.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.schemas.dto.billing import Money
from app.schemas.dto.invoicing import TaxDecision, TaxedAmount
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor

BASIS_POINTS_IN_WHOLE: Decimal = Decimal(10_000)
WHOLE_MINOR_UNIT: Decimal = Decimal(1)


def add_tax(subtotal: Money, decision: TaxDecision) -> TaxedAmount:
    """51700 GEL at 18 % -> tax 9306, total 61006; 1234 JPY -> tax 222."""

    tax_minor: int = int(
        (
            Decimal(int(subtotal.amount_minor))
            * Decimal(int(decision.rate_basis_points))
            / BASIS_POINTS_IN_WHOLE
        ).quantize(WHOLE_MINOR_UNIT, rounding=ROUND_HALF_UP)
    )
    return TaxedAmount(
        subtotal=subtotal,
        tax=Money(
            amount_minor=MoneyAmountMinor(tax_minor),
            currency_code=subtotal.currency_code,
        ),
        total=Money(
            amount_minor=MoneyAmountMinor(int(subtotal.amount_minor) + tax_minor),
            currency_code=subtotal.currency_code,
        ),
        decision=decision,
    )
