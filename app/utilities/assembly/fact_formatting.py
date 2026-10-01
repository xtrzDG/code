"""
Deterministic, locale-neutral texts for the fact table and the instruction.

The instruction is English for the language model, so values are written the
same way for every country: 24-hour times, ISO dates, amounts with the ISO
currency code ("18.00 GEL", "1500 JPY") and phone numbers in international
format. The assistant translates them into the customer's language.
"""

from collections.abc import Sequence
from datetime import datetime
from zoneinfo import ZoneInfo

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat, PhoneNumberType
from typed_time_provider import Microseconds

from app.schemas.constants.businesses import Weekday
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.dto.billing import Money
from app.schemas.dto.localization import LanguageProfile, LocalizedText
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.utilities.money.money_math import convert_money_to_major_units

MINUTES_PER_HOUR: int = 60
MICROSECONDS_PER_SECOND: int = 1_000_000
ENGLISH_LANGUAGE_TAG: LanguageTag = LanguageTag("en")
TIME_RANGE_SEPARATOR: str = "–"
WEEKDAY_NAMES: dict[Weekday, str] = {
    Weekday.MONDAY: "Monday",
    Weekday.TUESDAY: "Tuesday",
    Weekday.WEDNESDAY: "Wednesday",
    Weekday.THURSDAY: "Thursday",
    Weekday.FRIDAY: "Friday",
    Weekday.SATURDAY: "Saturday",
    Weekday.SUNDAY: "Sunday",
}


def format_minute_of_day(minute_of_day: int) -> str:
    """540 -> "09:00"; 1440 (midnight at the end of the day) -> "24:00"."""

    hours, minutes = divmod(minute_of_day, MINUTES_PER_HOUR)
    return f"{hours:02d}:{minutes:02d}"


def format_opening_intervals(intervals: Sequence[OpeningInterval]) -> str:
    """Intervals of one day, earliest first: "09:00–13:00, 14:00–18:00"."""

    ordered_intervals: list[OpeningInterval] = sorted(
        intervals,
        key=lambda interval: (int(interval.opens_at), int(interval.closes_at)),
    )
    return ", ".join(
        format_minute_of_day(int(interval.opens_at))
        + TIME_RANGE_SEPARATOR
        + format_minute_of_day(int(interval.closes_at))
        for interval in ordered_intervals
    )


def format_weekly_hours(
    intervals: Sequence[OpeningInterval],
    closed_text: str = "Closed",
) -> list[tuple[str, str]]:
    """
    One (weekday name, hours) pair per day from Monday to Sunday; days
    without an interval get `closed_text`.
    """

    weekly_hours: list[tuple[str, str]] = []
    for weekday in Weekday:
        day_intervals: list[OpeningInterval] = [
            interval for interval in intervals if interval.weekday is weekday
        ]
        hours_text: str = (
            format_opening_intervals(day_intervals) if day_intervals else closed_text
        )
        weekly_hours.append((WEEKDAY_NAMES[weekday], hours_text))

    return weekly_hours


def format_compact_weekly_hours(intervals: Sequence[OpeningInterval]) -> str:
    """A whole week on one line: "Monday 10:00–22:00, Tuesday closed, ..."."""

    return ", ".join(
        f"{weekday_name} {hours_text}"
        for weekday_name, hours_text in format_weekly_hours(intervals, "closed")
    )


def format_money_amount(
    amount_minor: MoneyAmountMinor,
    currency_code: CurrencyCode,
) -> str:
    """
    Amount with the currency precision and ISO code, without grouping:
    1800 GEL -> "18.00 GEL", 1500 JPY -> "1500 JPY", 1250 KWD -> "1.250 KWD".
    """

    major_units = convert_money_to_major_units(
        Money(amount_minor=amount_minor, currency_code=currency_code)
    )
    return f"{format(major_units, 'f')} {currency_code}"


def format_international_phone_number(phone_number: E164PhoneNumber) -> str:
    """ "+995322123456" -> "+995 32 212 34 56" (E.164 when the plan is unknown)."""

    return format_phone_number_text(str(phone_number))


def format_phone_number_text(phone_number_text: str) -> str:
    """International format of a number written with "+", else the text as is."""

    try:
        parsed_number = phonenumbers.parse(phone_number_text, None)
    except NumberParseException:
        return phone_number_text

    return phonenumbers.format_number(parsed_number, PhoneNumberFormat.INTERNATIONAL)


def find_example_mobile_number(country_code: CountryCode) -> E164PhoneNumber | None:
    """
    A valid example mobile number of the country from its numbering plan
    (used as the AI customer's phone in autotests), or None.
    """

    example_number = phonenumbers.example_number_for_type(
        str(country_code),
        PhoneNumberType.MOBILE,
    )
    if example_number is None:
        return None

    return E164PhoneNumber(
        phonenumbers.format_number(example_number, PhoneNumberFormat.E164)
    )


def format_minutes(minutes: int) -> str:
    """1 -> "1 minute", 90 -> "90 minutes"."""

    return "1 minute" if minutes == 1 else f"{minutes} minutes"


def format_people(people: int) -> str:
    """1 -> "1 person", 4 -> "4 people"."""

    return "1 person" if people == 1 else f"{people} people"


def describe_language(
    language_tag: LanguageTag,
    language_profiles: Sequence[LanguageProfile],
) -> str:
    """ "Georgian (ka)"; just the tag when the language is not in the profiles."""

    for language_profile in language_profiles:
        if language_profile.tag == language_tag:
            return f"{language_profile.english_name} ({language_tag})"

    return str(language_tag)


def describe_languages(
    language_tags: Sequence[LanguageTag],
    language_profiles: Sequence[LanguageProfile],
) -> str:
    """ "Georgian (ka), Russian (ru), English (en)"."""

    return ", ".join(
        describe_language(language_tag, language_profiles)
        for language_tag in language_tags
    )


def read_english_text(text: LocalizedText) -> str:
    """The English value of a catalog text (English is mandatory there)."""

    english_value = text.values.get(ENGLISH_LANGUAGE_TAG)
    if english_value is not None:
        return str(english_value).strip()

    if not text.values:
        return ""

    return str(text.values[min(text.values)]).strip()


def read_english_rule_lines(text: LocalizedText) -> list[str]:
    """Rules stored one per line in a catalog text, English, without blanks."""

    return [
        line.strip() for line in read_english_text(text).splitlines() if line.strip()
    ]


def compute_local_date(now: Microseconds, timezone_name: TimezoneName) -> LocalDate:
    """Calendar date in the business time zone at the given UTC moment."""

    local_moment: datetime = datetime.fromtimestamp(
        int(now) // MICROSECONDS_PER_SECOND,
        tz=ZoneInfo(str(timezone_name)),
    )
    return LocalDate(local_moment.date().isoformat())


def unique_preserving_order(values: Sequence[str]) -> list[str]:
    """Drop repeated values (ignoring case and surrounding spaces), keep order."""

    seen_values: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        normalized_value: str = value.strip().casefold()
        if normalized_value == "" or normalized_value in seen_values:
            continue

        seen_values.add(normalized_value)
        unique_values.append(value.strip())

    return unique_values
