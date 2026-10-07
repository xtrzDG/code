"""Dates and times shown to customers, in the business time zone and language."""

import datetime
import zoneinfo
from collections.abc import Mapping
from typing import cast

from babel import Locale
from babel.dates import format_date, format_time

from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)
from app.utilities.localization.babel_locales import find_babel_locale

FALLBACK_LOCALE_IDENTIFIER: str = "en"
DATETIME_FORMAT_LENGTH: str = "medium"
DEFAULT_DATETIME_PATTERN: str = "{1} {0}"


def format_local_moment(
    unix_seconds: int,
    timezone_name: TimezoneName,
    language_tag: LanguageTag,
) -> str:
    """
    A moment as the customer reads it: "Oct 3, 2026, 7:30 PM" in English,
    "3 окт. 2026 г., 19:30" in Russian; clock and order follow CLDR.
    Unknown time zones fall back to UTC, unknown languages to English.
    """

    try:
        zone: datetime.tzinfo = zoneinfo.ZoneInfo(str(timezone_name))
    except zoneinfo.ZoneInfoNotFoundError, ValueError:
        zone = datetime.UTC

    local_moment: datetime.datetime = datetime.datetime.fromtimestamp(
        unix_seconds,
        tz=zone,
    )
    babel_locale: Locale = find_babel_locale(language_tag) or Locale.parse(
        FALLBACK_LOCALE_IDENTIFIER
    )
    date_text: str = format_date(
        local_moment.date(),
        format=DATETIME_FORMAT_LENGTH,
        locale=babel_locale,
    )
    time_text: str = format_time(
        local_moment.time(), format="short", locale=babel_locale
    )
    pattern_text: str = read_datetime_pattern(babel_locale)
    return pattern_text.replace("{1}", date_text).replace("{0}", time_text)


def read_datetime_pattern(babel_locale: Locale) -> str:
    """CLDR pattern joining date ({1}) and time ({0}), e.g. "{1}, {0}"."""

    datetime_formats: Mapping[str, object] = cast(
        Mapping[str, object],
        babel_locale.datetime_formats,
    )
    pattern: object = datetime_formats.get(DATETIME_FORMAT_LENGTH)
    return pattern if isinstance(pattern, str) else DEFAULT_DATETIME_PATTERN
