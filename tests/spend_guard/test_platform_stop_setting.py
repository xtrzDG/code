"""PLATFORM_DAILY_SPEND_STOP_PERCENT: 100 by default, 80 to 1000."""

import pytest

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.utilities.config_helpers.app_settings.spend_guard_settings_section import (
    read_spend_guard_settings,
)


def test_the_stop_is_the_whole_budget_by_default() -> None:
    settings = read_spend_guard_settings({})["spend_guard"]

    assert int(settings.platform_spend_stop_percent) == 100
    assert settings.platform_daily_budget_micro_usd is None


def test_the_stop_share_is_read_from_the_environment() -> None:
    settings = read_spend_guard_settings(
        {
            "PLATFORM_DAILY_SPEND_BUDGET_USD": "200",
            "PLATFORM_DAILY_SPEND_STOP_PERCENT": "120",
        }
    )["spend_guard"]

    assert int(settings.platform_spend_stop_percent) == 120
    assert settings.platform_daily_budget_micro_usd is not None
    assert int(settings.platform_daily_budget_micro_usd) == 200_000_000


@pytest.mark.parametrize("value", ["79", "1001", "0"])
def test_a_stop_below_the_warning_or_absurdly_high_is_refused(value: str) -> None:
    with pytest.raises(ValidationFailedError, match="PLATFORM_DAILY_SPEND_STOP_PERCENT"):
        read_spend_guard_settings({"PLATFORM_DAILY_SPEND_STOP_PERCENT": value})
