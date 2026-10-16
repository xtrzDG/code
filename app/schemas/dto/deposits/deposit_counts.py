"""What the database counts and sums for the deposits report."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.deposits import DepositStatus
from app.schemas.typings.deposits.constrained_integers import (
    DepositOutcomeCount,
    DepositRequestCount,
    DepositTotalMinor,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode


class DepositSumRow(ImmutableDTO):
    """Deposit requests of one state and currency, counted and summed."""

    status: DepositStatus
    currency_code: CurrencyCode
    count: DepositRequestCount
    total_minor: DepositTotalMinor


class BookingOutcomeRow(ImmutableDTO):
    """
    Bookings of one status that started in a period, with the state of
    their deposit (None: none was asked).
    """

    status: BookingStatus
    deposit_status: DepositStatus | None = None
    count: DepositOutcomeCount
