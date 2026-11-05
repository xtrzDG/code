"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class ConversationQualityHundredths(BaseConstrainedTypedInt):
    """
    The judge's average score of one real conversation in hundredths of a
    point (4.6 of 5 is 460), stored as a whole number so the database can
    sum a business's scores per day.
    """

    ge = 100
    le = 500


class QualityDropPercent(BaseConstrainedTypedInt):
    """
    How many percent the last day's average quality of real conversations
    is below the week before's (0 when it did not drop).
    """

    ge = 0
    le = 100


class QualitySampleBudgetCents(BaseConstrainedTypedInt):
    """
    What one night's judging of real conversations may cost at most, in US
    cents (QUALITY_SAMPLE_BUDGET_CENTS; 0 turns the sampling off).
    """

    ge = 0
    le = 1_000_000


class QualitySampleBusinessLimit(BaseConstrainedTypedInt):
    """
    How many conversations of one business the nightly sampling judges at
    most (QUALITY_SAMPLE_PER_BUSINESS).
    """

    ge = 1
    le = 500


class QualitySampleCount(BaseConstrainedTypedInt):
    """How many real conversations the judge scored in a stretch of time."""

    ge = 0


class QualitySamplePercent(BaseConstrainedTypedInt):
    """
    The share of a day's real conversations the nightly sampling judges, in
    percent (QUALITY_SAMPLE_PERCENT; 0 turns it off).
    """

    ge = 0
    le = 100


class QualityScoreHundredthsTotal(BaseConstrainedTypedInt):
    """
    The sum of the average scores (in hundredths) of a stretch's scored
    conversations: divided by their count, the stretch's average.
    """

    ge = 0


# Keep abc order for all non example types, if possible.
