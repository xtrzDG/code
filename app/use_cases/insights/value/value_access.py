"""Who sees what of the value model, and the business's own today."""

from datetime import date, timedelta

from typed_time_provider import Microseconds, WallClock

from app.schemas.constants.users import BusinessMemberRole
from app.schemas.constants.value import AverageCheckSource, ValuePeriod
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.value.value_model import ValueModel, ValueModelQuery, ValueTotals
from app.schemas.dto.value.value_views import BusinessValueQuery
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    microseconds_to_seconds,
    parse_local_date,
    to_local_date,
    to_local_moment,
)
from app.utilities.value.value_periods import (
    LAST_DAYS,
    ValueDates,
    days_before,
    period_dates,
)

MAX_PERIOD_DAYS: int = 366


def sees_money(business: BusinessDocument, user_id: UserId) -> bool:
    """Owners (and platform admins, who act as owners) see money; staff do not."""

    return not any(
        member.user_id == user_id and member.role is BusinessMemberRole.STAFF
        for member in business.members
    )


def without_money(model: ValueModel) -> ValueModel:
    """The value model with every amount left out (the counts stay)."""

    def counts_only(totals: ValueTotals) -> ValueTotals:
        return totals.model_copy(update={"estimated_revenue_minor": None})

    return model.model_copy(
        update={
            "average_check_minor": None,
            "average_check_source": AverageCheckSource.NONE,
            "typical_check_minor": None,
            "current": counts_only(model.current),
            "previous": counts_only(model.previous),
        }
    )


def local_today(
    business: BusinessDocument, wall_clock: WallClock[Microseconds]
) -> date:
    seconds: int = microseconds_to_seconds(int(wall_clock.now_unix()))
    return to_local_moment(seconds, load_time_zone(business.timezone)).date()


def choose_value_dates(query: BusinessValueQuery, today: date) -> ValueDates:
    """
    A named period, else the local dates asked for (compared with as many
    days before them), else the last 30 days.
    """

    if query.period is not None:
        return period_dates(query.period, today)

    if query.date_from is None and query.date_to is None:
        return period_dates(ValuePeriod.LAST_30_DAYS, today)

    date_to: date = today if query.date_to is None else parse_local_date(query.date_to)
    date_from: date = (
        date_to - timedelta(days=LAST_DAYS[ValuePeriod.LAST_30_DAYS] - 1)
        if query.date_from is None
        else parse_local_date(query.date_from)
    )
    if date_from > date_to:
        raise ValidationFailedError("The start date is after the end date.")

    if (date_to - date_from).days + 1 > MAX_PERIOD_DAYS:
        raise ValidationFailedError(
            f"The period may be at most {MAX_PERIOD_DAYS} days long."
        )

    return days_before(date_from, date_to)


def value_model_query(business: BusinessDocument, dates: ValueDates) -> ValueModelQuery:
    return ValueModelQuery(
        business_id=business.id,
        date_from=to_local_date(dates.date_from),
        date_to=to_local_date(dates.date_to),
        previous_date_from=to_local_date(dates.previous_from),
        previous_date_to=to_local_date(dates.previous_to),
    )
