from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.assistants.constrained_integers import AutotestSampleCount
from app.schemas.typings.quality.constrained_integers import (
    QualitySampleBudgetCents,
    QualitySampleBusinessLimit,
    QualitySamplePercent,
)

DEFAULT_AUTOTEST_CRITICAL_SAMPLES: int = 2
DEFAULT_QUALITY_SAMPLE_PERCENT: int = 5
DEFAULT_QUALITY_SAMPLE_PER_BUSINESS: int = 20
DEFAULT_QUALITY_SAMPLE_BUDGET_CENTS: int = 500


class QualitySettings(ImmutableDTO):
    """
    How quality is measured. Autotests play each launch-critical scenario
    AUTOTEST_CRITICAL_SAMPLES times and pass it only when every play passed
    (pass^k). Every night the judge scores QUALITY_SAMPLE_PERCENT of the
    day's real conversations, at most QUALITY_SAMPLE_PER_BUSINESS of one
    business and QUALITY_SAMPLE_BUDGET_CENTS of model cost in all.
    """

    autotest_critical_samples: AutotestSampleCount = AutotestSampleCount(
        DEFAULT_AUTOTEST_CRITICAL_SAMPLES
    )
    sample_percent: QualitySamplePercent = QualitySamplePercent(
        DEFAULT_QUALITY_SAMPLE_PERCENT
    )
    sample_per_business: QualitySampleBusinessLimit = QualitySampleBusinessLimit(
        DEFAULT_QUALITY_SAMPLE_PER_BUSINESS
    )
    sample_budget_cents: QualitySampleBudgetCents = QualitySampleBudgetCents(
        DEFAULT_QUALITY_SAMPLE_BUDGET_CENTS
    )
