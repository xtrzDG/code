"""When a discount given until a local calendar day stops applying."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.constrained_strings import DiscountEndDate
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.utilities.billing.billing_periods import to_local_datetime, to_microseconds

# A discount is a deal for a while, not forever.
MAX_DISCOUNT_DAYS: int = 3 * 366


def discount_ends_at(
    last_day: DiscountEndDate,
    timezone: TimezoneName,
    now: Microseconds,
) -> Microseconds:
    """
    The first moment after `last_day` in the business's time zone: a period
    starting before it is discounted.

    Raises:
        ValidationFailedError: a day the calendar does not have, a day
            already over, or one more than three years ahead.
    """

    try:
        day: date = date.fromisoformat(str(last_day))
    except ValueError as error:
        raise ValidationFailedError(f"{last_day} is not a calendar day.") from error

    today: date = to_local_datetime(now, timezone).date()
    if day < today:
        raise ValidationFailedError("The discount's last day is already over.")

    if (day - today).days > MAX_DISCOUNT_DAYS:
        raise ValidationFailedError("A discount runs for three years at most.")

    next_midnight = datetime.combine(
        day + timedelta(days=1), time.min, tzinfo=ZoneInfo(str(timezone))
    )
    return to_microseconds(next_midnight)
