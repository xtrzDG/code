"""
When a held place lapses, and until when a cancellation gets the deposit
back, as the customer reads it: the time alone when it is today at the
business, else the short date with the time, in the customer's language
(CLDR, Latin digits), in the business's time zone.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from babel.dates import format_skeleton
from typed_time_provider import Microseconds

from app.schemas.typings.deposits.strings import (
    DepositHoldEndText,
    DepositRefundDeadlineText,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.scheduling.localized_formatting import find_locale, isolate
from app.utilities.scheduling.zoned_time import (
    microseconds_to_seconds,
    to_local_moment,
)

MICROSECONDS_PER_MINUTE: int = 60 * 1_000_000
# Weekday, day and abbreviated month ("Tue, Oct 14" / "вт, 14 окт.").
SHORT_DATE_SKELETON: str = "MMMEd"
# Day and month, no weekday ("October 7" / "7 октября"), so a sentence
# such as "your booking on {date}" keeps its grammar in every language.
DAY_MONTH_SKELETON: str = "MMMMd"


def hold_end_text(
    ends_at: Microseconds,
    now: Microseconds,
    zone: ZoneInfo,
    language: LanguageTag,
) -> DepositHoldEndText:
    return DepositHoldEndText(moment_text(ends_at, now, zone, language))


def refund_deadline_text(
    deadline: Microseconds,
    now: Microseconds,
    zone: ZoneInfo,
    language: LanguageTag,
) -> DepositRefundDeadlineText:
    return DepositRefundDeadlineText(moment_text(deadline, now, zone, language))


def moment_text(
    moment: Microseconds,
    now: Microseconds,
    zone: ZoneInfo,
    language: LanguageTag,
) -> str:
    """The time alone when it is today at the business, else date and time."""

    local: datetime = local_moment(moment, zone)
    clock: str = local.strftime("%H:%M")
    if local.date() == local_moment(now, zone).date():
        return isolate(clock, language)

    day: str = format_skeleton(SHORT_DATE_SKELETON, local, locale=find_locale(language))
    return isolate(f"{day}, {clock}", language)


def day_month_text(value: date, language: LanguageTag) -> str:
    """The day and month of a booking in the customer's language."""

    return format_skeleton(DAY_MONTH_SKELETON, value, locale=find_locale(language))


def local_moment(moment: Microseconds, zone: ZoneInfo) -> datetime:
    return to_local_moment(microseconds_to_seconds(int(moment)), zone)


def minutes_later(moment: Microseconds, minutes: int) -> Microseconds:
    """A moment `minutes` after another (UTC microseconds)."""

    return Microseconds(int(moment) + minutes * MICROSECONDS_PER_MINUTE)
