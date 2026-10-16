"""
VAT is rounded once, half up, to the smallest unit of the invoice's
currency, and the VAT inside a total charged is the same split back.
"""

import pytest

from app.schemas.constants.invoicing import TaxTreatment
from app.schemas.dto.billing import Money
from app.schemas.dto.invoicing import TaxDecision
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.invoicing.constrained_integers import TaxRateBasisPoints
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.billing.tax_math import add_tax, extract_tax

GEORGIAN_VAT = TaxDecision(
    treatment=TaxTreatment.STANDARD, rate_basis_points=TaxRateBasisPoints(1800)
)


def money(amount_minor: int, currency: str) -> Money:
    return Money(
        amount_minor=MoneyAmountMinor(amount_minor),
        currency_code=CurrencyCode(currency),
    )


@pytest.mark.parametrize(
    ("subtotal", "currency", "tax", "total"),
    [
        # 517.00 GEL: 93.06 exactly.
        (51_700, "GEL", 9_306, 61_006),
        # 0.15 EUR: 0.027 -> 0.03 (half up).
        (15, "EUR", 3, 18),
        # 0.25 EUR: 0.045 -> 0.05, the half goes up.
        (25, "EUR", 5, 30),
        # 0.24 EUR: 0.0432 -> 0.04.
        (24, "EUR", 4, 28),
        # 1 234 JPY has no minor unit: 222.12 -> 222.
        (1_234, "JPY", 222, 1_456),
        # 1 247 JPY: 224.46 -> 224; 1 250 JPY: 225 exactly.
        (1_247, "JPY", 224, 1_471),
        # 12.345 KWD has three digits: 2.2221 -> 2.222.
        (12_345, "KWD", 2_222, 14_567),
        # Nothing to tax.
        (0, "GEL", 0, 0),
    ],
)
def test_vat_is_rounded_to_the_currency_digits(
    subtotal: int, currency: str, tax: int, total: int
) -> None:
    taxed = add_tax(money(subtotal, currency), GEORGIAN_VAT)

    assert int(taxed.tax.amount_minor) == tax
    assert int(taxed.total.amount_minor) == total
    assert taxed.total.currency_code == taxed.tax.currency_code == currency


def test_no_vat_leaves_the_price_as_it_is() -> None:
    no_vat = TaxDecision(
        treatment=TaxTreatment.REVERSE_CHARGE, rate_basis_points=TaxRateBasisPoints(0)
    )

    taxed = add_tax(money(51_700, "GEL"), no_vat)

    assert (int(taxed.tax.amount_minor), int(taxed.total.amount_minor)) == (0, 51_700)


@pytest.mark.parametrize("rate", [0, 500, 1800, 2000, 2150])
def test_the_vat_inside_a_total_splits_back_to_the_same_price(rate: int) -> None:
    decision = TaxDecision(
        treatment=TaxTreatment.STANDARD, rate_basis_points=TaxRateBasisPoints(rate)
    )
    for subtotal in range(0, 20_001, 7):
        taxed = add_tax(money(subtotal, "GEL"), decision)
        split = extract_tax(taxed.total, decision)

        assert split.subtotal == taxed.subtotal
        assert split.tax == taxed.tax


def test_a_total_from_before_vat_is_split_with_vat_inside() -> None:
    # 517.00 GEL charged by an automatic charge started before registration.
    split = extract_tax(money(51_700, "GEL"), GEORGIAN_VAT)

    assert int(split.subtotal.amount_minor) == 43_814
    assert int(split.tax.amount_minor) == 7_886
    assert int(split.subtotal.amount_minor) + int(split.tax.amount_minor) == 51_700
