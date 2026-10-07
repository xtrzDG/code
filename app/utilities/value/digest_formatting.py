"""Numbers, money, periods and changes as an owner's digest writes them."""

from datetime import date
from decimal import Decimal

from babel import Locale
from babel.dates import format_date, format_interval, format_skeleton
from babel.numbers import format_currency, format_decimal

from app.schemas.constants.value import ValueReportKind
from app.schemas.dto.billing import Money
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.utilities.money.money_math import convert_money_to_major_units
from app.utilities.scheduling.localized_formatting import find_locale

LATIN_DIGITS: str = "latn"
MINUTES_PER_HOUR: int = 60


def format_count(count: int, language: LanguageTag) -> str:
    """1234 -> "1,234" (en), "1 234" (ru, ka); Latin digits everywhere."""

    return str(
        format_decimal(
            count, locale=find_locale(language), numbering_system=LATIN_DIGITS
        )
    )


def format_multiple(multiple: float, language: LanguageTag) -> str:
    """3.7 -> "3.7" (en), "3,7" (ru, ka): one decimal, Latin digits."""

    return str(
        format_decimal(
            Decimal(str(multiple)),
            format="#,##0.0",
            locale=find_locale(language),
            numbering_system=LATIN_DIGITS,
        )
    )


def format_whole_money(
    amount_minor: int,
    currency_code: CurrencyCode,
    language: LanguageTag,
) -> str:
    """An estimate in whole units of its currency: "2 640 ₾", "€2,640"."""

    locale: Locale = find_locale(language)
    major: Decimal = convert_money_to_major_units(
        Money(amount_minor=MoneyAmountMinor(amount_minor), currency_code=currency_code)
    ).quantize(Decimal(1))
    pattern: str = str(locale.currency_formats["standard"].pattern)
    whole_pattern: str = pattern.split(";")[0].replace(".00", "")
    return str(
        format_currency(
            major,
            str(currency_code),
            format=whole_pattern,
            locale=locale,
            currency_digits=False,
            numbering_system=LATIN_DIGITS,
        )
    )


def format_report_period(
    kind: ValueReportKind,
    date_from: date,
    date_to: date,
    language: LanguageTag,
) -> str:
    """The day, the week's range or the month of a report."""

    locale: Locale = find_locale(language)
    if kind is ValueReportKind.DAILY:
        return str(format_date(date_from, "long", locale=locale))

    if kind is ValueReportKind.MONTHLY:
        return str(format_skeleton("yMMMM", date_from, locale=locale))

    return str(format_interval(date_from, date_to, "MMMd", locale=locale))


def format_change(current: int, previous: int, language: LanguageTag) -> str | None:
    """
    "▲ 12%" or "▼ 8%" against the period before; None when there is
    nothing to compare with (the period before had none) or no change.
    """

    if previous <= 0 or current == previous:
        return None

    percent: int = round(abs(current - previous) * 100 / previous)
    arrow: str = "▲" if current > previous else "▼"
    return f"{arrow} {format_count(percent, language)}%"


def split_minutes(minutes: int) -> tuple[int, bool]:
    """Whole hours (rounded) from an hour on, else minutes: (amount, is_hours)."""

    if minutes >= MINUTES_PER_HOUR:
        return round(minutes / MINUTES_PER_HOUR), True

    return minutes, False
