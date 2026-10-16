"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class FeedbackDelayMinutes(BaseConstrainedTypedInt):
    """
    How long after a visit ends the customer is asked how it went: from a
    quarter of an hour to three days.

    Example:
        delay = FeedbackDelayMinutes(120)
    """

    ge = 15
    le = 3 * 24 * 60


class FeedbackRequestCount(BaseConstrainedTypedInt):
    """How many feedback requests of one kind fall into a period."""

    ge = 0


class FeedbackScoreTotal(BaseConstrainedTypedInt):
    """The sum of the visit ratings of a period (for their average)."""

    ge = 0


class ReviewLinkClickCount(BaseConstrainedTypedInt):
    """How often a customer opened the review link they were sent."""

    ge = 0


class ReviewStatsPeriodDays(BaseConstrainedTypedInt):
    """The days back the review statistics cover (Settings → Reviews)."""

    ge = 1
    le = 366


class VisitScore(BaseConstrainedTypedInt):
    """
    The customer's rating of a visit, from 1 (bad) to 5 (excellent).

    Example:
        score = VisitScore(5)
    """

    ge = 1
    le = 5


# Keep abc order for all non example types, if possible.
