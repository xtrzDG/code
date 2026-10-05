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


class AverageJudgeScoreChange(BaseConstrainedTypedFloat):
    """
    How far an average judge score moved between two autotest runs (this
    version's against the live one's), from -4.0 to +4.0.
    """

    ge = -4.0
    le = 4.0


# Keep abc order for all non example types, if possible.
