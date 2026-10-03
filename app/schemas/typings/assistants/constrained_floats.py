"""Keep abc order."""

from base_typed_float import BaseConstrainedTypedFloat


class AutotestPassRate(BaseConstrainedTypedFloat):
    """Share of passed autotest scenarios, from 0.0 to 1.0."""

    ge = 0.0
    le = 1.0


class AverageJudgeScore(BaseConstrainedTypedFloat):
    """Mean judge score over scenarios and criteria (launch threshold 4.0)."""

    ge = 1.0
    le = 5.0


# Keep abc order for all non example types, if possible.
