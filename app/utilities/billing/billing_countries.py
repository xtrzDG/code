"""Which ISO codes are countries a buyer can be established in."""

from babel.numbers import get_territory_currencies

from app.schemas.typings.localization.constrained_strings import CountryCode
from app.utilities.localization.cldr_language_names import (
    get_english_locale,
    read_locale_name,
)

# CLDR names these regions, but nobody is established in them.
NOT_COUNTRIES: frozenset[str] = frozenset({"EU", "EZ", "UN", "ZZ"})


def is_billing_country(country_code: CountryCode) -> bool:
    """A territory CLDR names and gives a currency (GE, DE, XK; not ZZ, EU, AQ)."""

    code: str = str(country_code)
    return (
        code not in NOT_COUNTRIES
        and read_locale_name(get_english_locale().territories, code) is not None
        and get_territory_currencies(code) != []
    )
