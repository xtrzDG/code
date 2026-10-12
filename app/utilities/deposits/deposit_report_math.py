"""
The arithmetic of the deposits report: money per currency from the summed
requests, and no-show rates that are shown only when a group has enough
finished bookings to say anything (an honest "not enough data" below).
"""

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.deposits import DepositStatus
from app.schemas.dto.deposits.deposit_counts import BookingOutcomeRow, DepositSumRow
from app.schemas.dto.deposits.deposit_report import DepositMoney, NoShowRate
from app.schemas.typings.deposits.constrained_integers import (
    DepositOutcomeCount,
    DepositRequestCount,
    DepositTotalMinor,
    NoShowPercent,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.deposits.booking_deposit_state import (
    COLLECTED_DEPOSIT_STATUSES,
    PAID_DEPOSIT_STATUSES,
)
from app.utilities.money.money_math import get_currency_minor_unit_digits

# Fewer finished bookings than this in a group show "not enough data".
MIN_FINISHED_BOOKINGS: DepositOutcomeCount = DepositOutcomeCount(20)
FINISHED_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.COMPLETED, BookingStatus.NO_SHOW}
)


def money_lines(paid_rows: Sequence[DepositSumRow]) -> list[DepositMoney]:
    """Collected (paid, kept) and to refund, per currency, largest first."""

    totals: dict[CurrencyCode, tuple[int, int]] = {}
    for row in paid_rows:
        collected, refund_due = totals.get(row.currency_code, (0, 0))
        if row.status in COLLECTED_DEPOSIT_STATUSES:
            collected += int(row.total_minor)
        elif row.status is DepositStatus.REFUND_DUE:
            refund_due += int(row.total_minor)
        totals[row.currency_code] = (collected, refund_due)

    return [
        DepositMoney(
            currency_code=code,
            currency_digits=get_currency_minor_unit_digits(code),
            collected_minor=DepositTotalMinor(collected),
            refund_due_minor=DepositTotalMinor(refund_due),
        )
        for code, (collected, refund_due) in sorted(
            totals.items(), key=lambda item: (-item[1][0], str(item[0]))
        )
        if collected or refund_due
    ]


def count_in(
    rows: Sequence[DepositSumRow], statuses: frozenset[DepositStatus]
) -> DepositRequestCount:
    return DepositRequestCount(
        sum(int(row.count) for row in rows if row.status in statuses)
    )


def no_show_rate(
    rows: Sequence[BookingOutcomeRow], *, with_deposit: bool
) -> NoShowRate:
    """The no-show rate of bookings with a paid deposit, or of those with none."""

    finished: int = 0
    no_shows: int = 0
    for row in rows:
        has_paid_deposit: bool = row.deposit_status in PAID_DEPOSIT_STATUSES
        if row.status not in FINISHED_STATUSES or has_paid_deposit is not with_deposit:
            continue
        if not with_deposit and row.deposit_status is not None:
            continue

        finished += int(row.count)
        if row.status is BookingStatus.NO_SHOW:
            no_shows += int(row.count)

    is_enough: bool = finished >= int(MIN_FINISHED_BOOKINGS)
    return NoShowRate(
        finished_count=DepositOutcomeCount(finished),
        no_show_count=DepositOutcomeCount(no_shows),
        has_enough_data=is_enough,
        no_show_percent=(
            NoShowPercent(
                int(
                    (Decimal(no_shows) * 100 / Decimal(finished)).quantize(
                        Decimal(1), rounding=ROUND_HALF_UP
                    )
                )
            )
            if is_enough
            else None
        ),
    )
