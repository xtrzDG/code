"""
The local dates of value periods and reports, and when a report is due.

Every period is a run of whole local days of the business, compared with
the run just before it: the same number of days for the dashboard's
periods, the week before for a week, the month before for a month.
Reports are sent from 09:00 local time: the daily digest every morning
(yesterday), the weekly digest on Mondays (last Monday to Sunday) and the
monthly report on the 1st (last month). A report the worker could not
send at 09:00 still goes out later in the same day (daily), week (weekly)
or month (monthly), never after.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.schemas.constants.value import ValuePeriod, ValueReportKind
from app.schemas.typings.value.constrained_strings import ValueReportPeriodKey

DAYS_PER_WEEK: int = 7
REPORT_HOUR: int = 9
LAST_DAYS: dict[ValuePeriod, int] = {
    ValuePeriod.TODAY: 1,
    ValuePeriod.LAST_7_DAYS: 7,
    ValuePeriod.LAST_30_DAYS: 30,
    ValuePeriod.LAST_90_DAYS: 90,
}


@dataclass(frozen=True)
class ValueDates:
    """A run of local days and the run before it (both inclusive)."""

    date_from: date
    date_to: date
    previous_from: date
    previous_to: date


@dataclass(frozen=True)
class ReportPeriod:
    """The period one report summarizes, and its key."""

    kind: ValueReportKind
    period_key: ValueReportPeriodKey
    dates: ValueDates


def days_before(date_from: date, date_to: date) -> ValueDates:
    """`date_from` to `date_to` and as many days just before them."""

    length: int = (date_to - date_from).days + 1
    return ValueDates(
        date_from=date_from,
        date_to=date_to,
        previous_from=date_from - timedelta(days=length),
        previous_to=date_from - timedelta(days=1),
    )


def week_dates(monday: date) -> ValueDates:
    return ValueDates(
        date_from=monday,
        date_to=monday + timedelta(days=DAYS_PER_WEEK - 1),
        previous_from=monday - timedelta(days=DAYS_PER_WEEK),
        previous_to=monday - timedelta(days=1),
    )


def month_dates(first_day: date) -> ValueDates:
    last_day: date = next_month(first_day) - timedelta(days=1)
    previous_first: date = (first_day - timedelta(days=1)).replace(day=1)
    return ValueDates(
        date_from=first_day,
        date_to=last_day,
        previous_from=previous_first,
        previous_to=first_day - timedelta(days=1),
    )


def next_month(first_day: date) -> date:
    return (first_day.replace(day=28) + timedelta(days=4)).replace(day=1)


def month_so_far(today: date) -> ValueDates:
    """The 1st to today, and the same days of the month before (as far as it goes)."""

    first_day: date = today.replace(day=1)
    previous_first: date = (first_day - timedelta(days=1)).replace(day=1)
    previous_last: date = first_day - timedelta(days=1)
    return ValueDates(
        date_from=first_day,
        date_to=today,
        previous_from=previous_first,
        previous_to=min(previous_first + (today - first_day), previous_last),
    )


def period_dates(period: ValuePeriod, today: date) -> ValueDates:
    """The dates of a cabinet period ending today, or the last full week or month."""

    if period is ValuePeriod.THIS_MONTH:
        return month_so_far(today)

    if period is ValuePeriod.LAST_WEEK:
        this_monday: date = today - timedelta(days=today.weekday())
        return week_dates(this_monday - timedelta(days=DAYS_PER_WEEK))

    if period is ValuePeriod.LAST_MONTH:
        return month_dates((today.replace(day=1) - timedelta(days=1)).replace(day=1))

    return days_before(today - timedelta(days=LAST_DAYS[period] - 1), today)


def report_period(kind: ValueReportKind, today: date) -> ReportPeriod:
    """The period the report of `kind` sent today summarizes."""

    if kind is ValueReportKind.DAILY:
        yesterday: date = today - timedelta(days=1)
        return ReportPeriod(
            kind=kind,
            period_key=ValueReportPeriodKey(yesterday.isoformat()),
            dates=days_before(yesterday, yesterday),
        )

    if kind is ValueReportKind.WEEKLY:
        dates: ValueDates = period_dates(ValuePeriod.LAST_WEEK, today)
        iso_year, iso_week, _ = dates.date_from.isocalendar()
        return ReportPeriod(
            kind=kind,
            period_key=ValueReportPeriodKey(f"{iso_year:04d}-W{iso_week:02d}"),
            dates=dates,
        )

    dates = period_dates(ValuePeriod.LAST_MONTH, today)
    return ReportPeriod(
        kind=kind,
        period_key=ValueReportPeriodKey(dates.date_from.strftime("%Y-%m")),
        dates=dates,
    )


def is_report_due(kind: ValueReportKind, local_now: datetime) -> bool:
    """
    Whether the report of `kind` may go out now: from 09:00 local time on
    any day (daily), on any day of the week (weekly: Monday 09:00 is the
    first chance) or of the month (monthly: the 1st 09:00 is the first).
    """

    if kind is ValueReportKind.DAILY:
        return local_now.hour >= REPORT_HOUR

    first_day: bool = (
        local_now.weekday() == 0
        if kind is ValueReportKind.WEEKLY
        else local_now.day == 1
    )
    return not first_day or local_now.hour >= REPORT_HOUR
