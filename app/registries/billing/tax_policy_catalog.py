"""
Standard VAT rates of the countries a registered seller may invoice from,
in basis points (1800 = 18 %). A seller country missing here cannot turn
PLATFORM_VAT_REGISTERED on: add its rate first (and have an accountant
check its wording in `billing_document_texts.py`).
"""

from collections.abc import Mapping

from app.schemas.typings.invoicing.constrained_integers import TaxRateBasisPoints
from app.schemas.typings.localization.constrained_strings import CountryCode

STANDARD_VAT_RATES: Mapping[CountryCode, TaxRateBasisPoints] = {
    # Tax Code of Georgia, article 169: 18 % on taxable supplies.
    CountryCode("GE"): TaxRateBasisPoints(1800),
}
