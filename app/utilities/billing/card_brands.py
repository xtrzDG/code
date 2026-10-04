"""
How an invoice prints a card's payment system. Flitt names it in capitals
("VISA", "MASTERCARD"); the invoice and the receipt use each brand's own
spelling ("Visa", "Mastercard"). A brand not listed here prints as the
provider sent it.
"""

from collections.abc import Mapping

from app.schemas.typings.invoicing.strings import PaymentCardBrand

# Keys: the provider's name in capitals without spaces, dashes or underscores.
BRAND_SPELLINGS: Mapping[str, str] = {
    "AMEX": "American Express",
    "AMERICANEXPRESS": "American Express",
    "DINERS": "Diners Club",
    "DINERSCLUB": "Diners Club",
    "DISCOVER": "Discover",
    "JCB": "JCB",
    "MAESTRO": "Maestro",
    "MASTERCARD": "Mastercard",
    "MIR": "Mir",
    "UNIONPAY": "UnionPay",
    "VISA": "Visa",
}
SEPARATORS: tuple[str, ...] = (" ", "-", "_")


def spell_card_brand(brand: PaymentCardBrand) -> str:
    """Mastercard for "MASTERCARD"; an unknown "Elcart" stays "Elcart"."""

    spoken: str = str(brand).strip()
    key: str = spoken.upper()
    for separator in SEPARATORS:
        key = key.replace(separator, "")

    return BRAND_SPELLINGS.get(key, spoken)
