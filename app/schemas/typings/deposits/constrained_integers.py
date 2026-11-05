"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class DepositAmountMinor(BaseConstrainedTypedInt):
    """
    The fixed deposit a policy asks, in minor units of its currency: for the
    whole booking, or for each guest (cents, tetri; JPY has none).

    Example:
        table_deposit = DepositAmountMinor(5000)  # 50.00 GEL
    """

    ge = 1


class DepositDueMinor(BaseConstrainedTypedInt):
    """
    What one deposit request asks the customer to pay, in minor units of its
    currency: the policy's amount, times the guests, or its percent of the
    booking's value, rounded once to the currency's precision.
    """

    ge = 1


class DepositHoldMinutes(BaseConstrainedTypedInt):
    """
    How long a booking waiting for its deposit keeps its place before it is
    released (15 minutes to a day).
    """

    ge = 15
    le = 1440


class DepositOutcomeCount(BaseConstrainedTypedInt):
    """How many bookings of a report period ended one way (came, did not come)."""

    ge = 0


class DepositPercent(BaseConstrainedTypedInt):
    """Whole percent of a booking's value a deposit policy asks (1 to 100)."""

    ge = 1
    le = 100


class DepositReportDays(BaseConstrainedTypedInt):
    """The days a deposits report looks back over (a week to a year)."""

    ge = 7
    le = 366


class DepositRefundCutoffHours(BaseConstrainedTypedInt):
    """
    Hours before the start a cancellation still gets the deposit back (0:
    any cancellation before the start; up to 30 days).
    """

    ge = 0
    le = 720


class DepositRequestCount(BaseConstrainedTypedInt):
    """How many deposit requests of a report period are in one state."""

    ge = 0


class DepositTotalMinor(BaseConstrainedTypedInt):
    """
    Deposits summed over a report period, in minor units of their currency
    (collected, or waiting to be refunded).
    """

    ge = 0


class NoShowPercent(BaseConstrainedTypedInt):
    """
    Whole percent of finished bookings whose guest did not come (0 to 100),
    of a sample large enough to say so.
    """

    ge = 0
    le = 100


# Keep abc order for all non example types, if possible.
