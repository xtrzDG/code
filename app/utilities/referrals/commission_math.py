"""A partner's commission on an invoice and the month it belongs to."""

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from typed_time_provider import Microseconds

from app.schemas.typings.referrals.constrained_strings import CommissionMonth

BASIS_POINTS_IN_WHOLE: Decimal = Decimal(10_000)
MICROSECONDS_IN_SECOND: int = 1_000_000


def commission_minor(base_minor: int, rate_basis_points: int) -> int:
    """`rate_basis_points` of `base_minor`, rounded half up to a minor unit."""

    share: Decimal = Decimal(base_minor) * Decimal(rate_basis_points)
    return int(
        (share / BASIS_POINTS_IN_WHOLE).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    )


def commission_month(moment: Microseconds) -> CommissionMonth:
    """The UTC calendar month of a moment, as YYYY-MM."""

    when: datetime = datetime.fromtimestamp(
        int(moment) / MICROSECONDS_IN_SECOND, tz=UTC
    )
    return CommissionMonth(f"{when.year:04d}-{when.month:02d}")
