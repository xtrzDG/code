"""Days of the sub-processor list: in force on a day, notice windows, UTC days."""

from datetime import UTC, date, datetime, timedelta

from typed_time_provider import Microseconds

from app.schemas.dto.legal import SubprocessorChange, SubprocessorEntry
from app.schemas.typings.legal.constrained_integers import SubprocessorNoticeDays
from app.schemas.typings.legal.constrained_strings import SubprocessorChangeDate

MICROSECONDS_PER_SECOND: int = 1_000_000


def utc_day(now: Microseconds) -> date:
    """The UTC calendar day of a moment."""

    return datetime.fromtimestamp(int(now) / MICROSECONDS_PER_SECOND, tz=UTC).date()


def to_day(value: SubprocessorChangeDate) -> date:
    return date.fromisoformat(str(value))


def change_date(day: date) -> SubprocessorChangeDate:
    return SubprocessorChangeDate(day.isoformat())


def is_in_force(entry: SubprocessorEntry, day: date) -> bool:
    """Used on `day`: added by then and not removed yet."""

    if to_day(entry.added_on) > day:
        return False

    return entry.removed_on is None or day < to_day(entry.removed_on)


def notice_opens_on(
    change: SubprocessorChange, notice_days: SubprocessorNoticeDays
) -> date:
    """The first day owners are told: the notice period before it takes effect."""

    return to_day(change.effective_on) - timedelta(days=int(notice_days))


def notice_grace_ends_on(
    change: SubprocessorChange, notice_days: SubprocessorNoticeDays
) -> date:
    """
    The last day a missed notice still goes out (late): as long after the
    change as the notice period, for a job that could not run in time.
    """

    return to_day(change.effective_on) + timedelta(days=int(notice_days))


def is_notice_due(
    change: SubprocessorChange, notice_days: SubprocessorNoticeDays, day: date
) -> bool:
    """Owners are told from the notice period's first day to the end of grace."""

    return (
        notice_opens_on(change, notice_days)
        <= day
        <= notice_grace_ends_on(change, notice_days)
    )


def is_late_notice(change: SubprocessorChange, day: date) -> bool:
    """A notice sent on or after the day the change took effect."""

    return day >= to_day(change.effective_on)
