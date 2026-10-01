"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class WizardStepNumber(BaseConstrainedTypedInt):
    """
    Position of a step in the six-step profile wizard (1..6).

    Example:
        offer_step = WizardStepNumber(3)
    """

    ge = 1
    le = 6


# Keep abc order for all non example types, if possible.
