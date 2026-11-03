"""
A business's monthly hard stop on top of its daily limits (AI-09): its
provider spend since the first of its month (in its time zone) may reach
`MONTHLY_HARD_LIMIT_DAYS` times its daily hard limit, so a business kept
just under its daily limit day after day still stops. Past it the business
only takes messages for its team until its month ends, like past the daily
hard limit; raising the daily hard limit (`business_limits`) raises the
monthly one with it.

The month's spend is summed only on a turn that already spent something
today (the day the limit is crossed always has spend), and the first
process to see it stores a mark of the month: later turns settle with one
read by id.
"""

from datetime import UTC, datetime
from uuid import uuid5

from typed_time_provider import Microseconds

from app.schemas.dto.spend_guard import SpendLimits
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.schemas.typings.spend.constrained_integers import DailySpendLimitMicroUsd
from app.schemas.typings.spend.prefixed_id import SpendLimitMarkId
from app.utilities.scheduling.zoned_time import load_time_zone
from app.utilities.spend.spend_keys import SPEND_LIMIT_MARK_NAMESPACE

MONTHLY_HARD_LIMIT_DAYS: int = 10
MICROSECONDS_PER_SECOND: int = 1_000_000


def monthly_hard_limit(limits: SpendLimits) -> DailySpendLimitMicroUsd:
    """The month's hard limit: so many days at the daily hard limit."""

    return DailySpendLimitMicroUsd(
        int(limits.hard_limit_micro_usd) * MONTHLY_HARD_LIMIT_DAYS
    )


def business_month_start(
    now: Microseconds, timezone: TimezoneName
) -> tuple[str, Microseconds]:
    """The business's month that holds `now` ("2026-11") and when it began."""

    local: datetime = datetime.fromtimestamp(
        int(now) // MICROSECONDS_PER_SECOND, tz=UTC
    ).astimezone(load_time_zone(timezone))
    first: datetime = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return (
        first.strftime("%Y-%m"),
        Microseconds(int(first.timestamp()) * MICROSECONDS_PER_SECOND),
    )


def monthly_mark_id_of(business_id: BusinessId, month: str) -> SpendLimitMarkId:
    """One monthly hard mark per business and month (never a daily mark's id)."""

    return SpendLimitMarkId(
        uuid5(SPEND_LIMIT_MARK_NAMESPACE, f"{business_id}:month:{month}:hard_limit")
    )
