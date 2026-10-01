"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class PeriodItemCount(BaseConstrainedTypedInt):
    """
    How many items of one kind fall into a dashboard period.

    Example:
        conversations = PeriodItemCount(42)
    """

    ge = 0


class UsedVoiceMinutes(BaseConstrainedTypedInt):
    """Package voice minutes used in a period, rounded up to whole minutes."""

    ge = 0


# Keep abc order for all non example types, if possible.
