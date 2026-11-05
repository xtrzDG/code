"""
VAT on a price in minor units: the tax is the price times the rate,
rounded once, half up, to the currency's smallest unit (two digits for GEL
and EUR, none for JPY, three for KWD), and the total is their sum, so
subtotal + tax = total always holds to the unit. A total already charged
(an automatic charge) is split the other way: the price is the total
divided by one plus the rate, rounded the same way, and the tax the rest;
for a total that `add_tax` made, that gives back the same price.
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


def extract_tax(total: Money, decision: TaxDecision) -> TaxedAmount:
    """61006 GEL at 18 % -> price 51700, tax 9306 (the VAT inside a total)."""

    subtotal_minor: int = int(
        (
            Decimal(int(total.amount_minor))
            * BASIS_POINTS_IN_WHOLE
            / (BASIS_POINTS_IN_WHOLE + Decimal(int(decision.rate_basis_points)))
        ).quantize(WHOLE_MINOR_UNIT, rounding=ROUND_HALF_UP)
    )
    return TaxedAmount(
        subtotal=Money(
            amount_minor=MoneyAmountMinor(subtotal_minor),
            currency_code=total.currency_code,
        ),
        tax=Money(
            amount_minor=MoneyAmountMinor(int(total.amount_minor) - subtotal_minor),
            currency_code=total.currency_code,
        ),
        total=total,
        decision=decision,
    )
