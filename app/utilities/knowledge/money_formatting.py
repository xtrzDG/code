"""Format money in minor units for any currency and language (Babel / CLDR)."""

from decimal import Decimal

from babel import Locale, UnknownLocaleError
from babel.numbers import format_currency, get_currency_precision

from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import FormattedMoneyText
from app.utilities.knowledge.localized_texts import FALLBACK_LANGUAGE_TAG


def format_money_minor(
    amount_minor: MoneyAmountMinor,
    currency_code: CurrencyCode,
    language_tag: LanguageTag,
) -> FormattedMoneyText:
    """
    Format an amount in minor units, e.g. 1800 GEL in "ka" -> "18,00 ₾".

    The number of minor digits comes from CLDR (JPY 0, GEL 2, KWD 3). Digits
    are always Latin so the invented-numbers guard can compare amounts.
    """

    minor_digits: int = get_currency_precision(currency_code)
    amount: Decimal = Decimal(int(amount_minor)).scaleb(-minor_digits)
    return FormattedMoneyText(
        format_currency(
            amount,
            currency_code,
            locale=resolve_babel_locale(language_tag),
            numbering_system="latn",
        )
    )


def resolve_babel_locale(language_tag: LanguageTag) -> Locale:
    """The CLDR locale of a BCP 47 tag, then of its language, then English."""

    candidate_tags: list[str] = [language_tag, language_tag.split("-")[0]]
    candidate_tags.append(FALLBACK_LANGUAGE_TAG)
    for candidate_tag in candidate_tags:
        try:
            return Locale.parse(candidate_tag, sep="-")
        except UnknownLocaleError, ValueError:
            continue

    return Locale("en")
