"""
AUTOTEST_CRITICAL_SAMPLES and QUALITY_SAMPLE_*: how strictly autotests
judge a version and how much of real traffic the nightly judge scores.
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
        )
    )
