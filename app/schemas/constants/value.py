from enum import StrEnum


class ValueReportKind(StrEnum):
    """
    A stored summary of what the assistant did for a business: the daily
    digest (yesterday), the weekly digest (last Monday to Sunday) or the
    monthly report (last calendar month).
    """

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ValuePeriod(StrEnum):
    """
    A period the cabinet asks the value of, in the business time zone:
    today, the last 7, 30 or 90 days up to today, this month so far, the
    last full week (Monday to Sunday) or the last full calendar month.
    Each is compared with the period just before it (of the same length;
    the month before for a month, the same days of the month before for
    this month so far).
    """

    TODAY = "today"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    LAST_90_DAYS = "90d"
    THIS_MONTH = "this_month"
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"


class AverageCheckSource(StrEnum):
    """
    Where the average check of the money estimate comes from: the owner
    set it, the typical check of the niche (converted into the business
    currency with an official rate), or none is known (no money estimate).
    """

    OWNER = "owner"
    NICHE_DEFAULT = "niche_default"
    NONE = "none"


class RevenueSource(StrEnum):
    """
    What the money estimate of a period rests on: the bookings' own values
    (service prices, stays' nightly rates), those plus the average check
    for the bookings without one, or the average check alone.
    """

    BOOKED_VALUES = "booked_values"
    MIXED = "mixed"
    AVERAGE_CHECK = "average_check"


class ValueBasis(StrEnum):
    """
    What earns the business money in the estimate: bookings the assistant
    made, or, for niches that take orders and requests instead of
    bookings, the requests it took.
    """

    BOOKINGS = "bookings"
    REQUESTS = "requests"


class ValueReportDelivery(StrEnum):
    """
    What happened to a stored report: queued for at least one owner
    (SENT), nobody wanted it or could get it (NO_RECIPIENTS), or the
    period was quiet (no conversation, booking or request) and it was not
    sent (QUIET).
    """

    SENT = "sent"
    NO_RECIPIENTS = "no_recipients"
    QUIET = "quiet"
