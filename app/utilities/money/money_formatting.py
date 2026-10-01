"""Money rendered for people in any CLDR language."""

from babel import Locale
from babel.numbers import format_currency

from app.schemas.dto.billing import Money
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import FormattedMoneyText
from app.utilities.localization.language_tags import require_babel_locale
from app.utilities.money.money_math import convert_money_to_major_units


def format_money(money: Money, language_tag: LanguageTag) -> FormattedMoneyText:
    """
    Format with the CLDR pattern of the language and the currency's precision.

    Examples: 517.00 GEL is "517,00 ₾" in ka, "517,00 GEL" in ru and
    "GEL517.00" in en; 1234 JPY is "¥1,234" in en. Digits are Latin in every
    language so amounts stay comparable across channels.

    Raises:
        UnsupportedLanguageError: CLDR has no data for the language.
    """

    display_locale: Locale = require_babel_locale(language_tag)
    return FormattedMoneyText(
        format_currency(
            convert_money_to_major_units(money),
            str(money.currency_code),
            locale=display_locale,
        )
    )
