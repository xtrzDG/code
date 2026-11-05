"""
AUTOTEST_CRITICAL_SAMPLES, QUALITY_SAMPLE_* and
QUALITY_SAMPLING_JUDGE_SAME_PROVIDER: how strictly autotests judge a
version, how much of real traffic the nightly judge scores and which
provider's model judges it.
"""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.quality_settings import (
    DEFAULT_AUTOTEST_CRITICAL_SAMPLES,
    DEFAULT_QUALITY_SAMPLE_BUDGET_CENTS,
    DEFAULT_QUALITY_SAMPLE_PER_BUSINESS,
    DEFAULT_QUALITY_SAMPLE_PERCENT,
    QualitySettings,
)
from app.schemas.typings.assistants.constrained_integers import AutotestSampleCount
from app.schemas.typings.quality.constrained_integers import (
    QualitySampleBudgetCents,
    QualitySampleBusinessLimit,
    QualitySamplePercent,
)
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    parse_setting,
    read_boolean,
    read_integer,
)


class QualitySettingsSection(TypedDict):
    """The `AppSettings` field of quality measurement."""

    quality: QualitySettings


def read_quality_settings(
    environment_variables: Mapping[str, str],
) -> QualitySettingsSection:
    def number(name: str, default: int) -> int:
        return read_integer(environment_variables, name, default)

    return QualitySettingsSection(
        quality=QualitySettings(
            autotest_critical_samples=parse_setting(
                "AUTOTEST_CRITICAL_SAMPLES",
                number("AUTOTEST_CRITICAL_SAMPLES", DEFAULT_AUTOTEST_CRITICAL_SAMPLES),
                AutotestSampleCount,
            ),
            sample_percent=parse_setting(
                "QUALITY_SAMPLE_PERCENT",
                number("QUALITY_SAMPLE_PERCENT", DEFAULT_QUALITY_SAMPLE_PERCENT),
                QualitySamplePercent,
            ),
            sample_per_business=parse_setting(
                "QUALITY_SAMPLE_PER_BUSINESS",
                number(
                    "QUALITY_SAMPLE_PER_BUSINESS", DEFAULT_QUALITY_SAMPLE_PER_BUSINESS
                ),
                QualitySampleBusinessLimit,
            ),
            sample_budget_cents=parse_setting(
                "QUALITY_SAMPLE_BUDGET_CENTS",
                number(
                    "QUALITY_SAMPLE_BUDGET_CENTS", DEFAULT_QUALITY_SAMPLE_BUDGET_CENTS
                ),
                QualitySampleBudgetCents,
            ),
            judge_same_provider=read_boolean(
                environment_variables, "QUALITY_SAMPLING_JUDGE_SAME_PROVIDER", True
            ),
        )
    )
