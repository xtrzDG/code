"""Keep abc order."""

from base_typed_float import BaseConstrainedTypedFloat


class ValueReturnMultiple(BaseConstrainedTypedFloat):
    """
    How many times the money the assistant brought in a period covers what
    the business's plan costs for the same days ("≈ 3.7× the plan price"):
    the money estimate divided by the plan's cost, both in the business
    currency, rounded to one decimal.

    Example:
        multiple = ValueReturnMultiple(3.7)
    """

    ge = 0.0


# Keep abc order for all non example types, if possible.
