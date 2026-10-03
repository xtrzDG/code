"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class PendingChangeCount(BaseConstrainedTypedInt):
    """
    How many changes the owner made that customers do not get yet.

    Example:
        count = PendingChangeCount(3)
    """

    ge = 0
    le = 100_000


class SetupMinutesLeft(BaseConstrainedTypedInt):
    """
    Estimated minutes of setup still ahead of the owner (0 when done).

    Example:
        left = SetupMinutesLeft(7)
    """

    ge = 0
    le = 600


class SetupPercent(BaseConstrainedTypedInt):
    """
    Share of the setup steps done (skipped optional steps do not count).

    Example:
        progress = SetupPercent(40)
    """

    ge = 0
    le = 100


class SetupStepMinutes(BaseConstrainedTypedInt):
    """
    Typical minutes one setup step takes an owner.

    Example:
        offer = SetupStepMinutes(3)
    """

    ge = 0
    le = 120


# Keep abc order for all non example types, if possible.
