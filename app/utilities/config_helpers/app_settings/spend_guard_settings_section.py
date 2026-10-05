"""
SPEND_*, PLATFORM_DAILY_SPEND_BUDGET_USD, CALL_* and API_*: the spend
guard's limits, the voice call caps and the generic request limits.
"""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.spend_guard_settings import (
    DEFAULT_API_EXPORTS_PER_USER_PER_MINUTE,
    DEFAULT_API_REQUESTS_PER_IP_PER_MINUTE,
    DEFAULT_API_REQUESTS_PER_USER_PER_MINUTE,
    DEFAULT_CALL_MAX_DURATION_SECONDS,
    DEFAULT_CALL_SILENCE_END_SECONDS,
    DEFAULT_HARD_LIMIT_MULTIPLE,
    DEFAULT_SOFT_LIMIT_MULTIPLE,
    SpendGuardSettings,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.spend.constrained_integers import (
    ApiRequestsPerMinute,
    CallMaxDurationSeconds,
    CallSilenceEndSeconds,
    PlatformDailySpendBudgetMicroUsd,
    SpendLimitMultiple,
)
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_text,
    parse_setting,
    read_integer,
)

MICRO_USD_PER_USD: int = 1_000_000


class SpendGuardSettingsSection(TypedDict):
    """The `AppSettings` field of the spend guard."""

    spend_guard: SpendGuardSettings


def read_spend_guard_settings(
    environment_variables: Mapping[str, str],
) -> SpendGuardSettingsSection:
    """
    Every variable is optional (see `SpendGuardSettings`).

    Raises:
        ValidationFailedError: a value out of its range, or a hard limit
            multiple below the soft one.
    """

    def integer[Typed](name: str, default: int, typed: type[Typed]) -> Typed:
        return parse_setting(
            name, read_integer(environment_variables, name, default), typed
        )

    budget_usd: int = read_integer(
        environment_variables, "PLATFORM_DAILY_SPEND_BUDGET_USD", 0
    )
    settings = SpendGuardSettings(
        soft_limit_multiple=integer(
            "SPEND_SOFT_LIMIT_MULTIPLE", DEFAULT_SOFT_LIMIT_MULTIPLE, SpendLimitMultiple
        ),
        hard_limit_multiple=integer(
            "SPEND_HARD_LIMIT_MULTIPLE", DEFAULT_HARD_LIMIT_MULTIPLE, SpendLimitMultiple
        ),
        soft_limit_model_id=optional_text(
            environment_variables, "SPEND_SOFT_LIMIT_MODEL_ID", LlmModelId
        ),
        platform_daily_budget_micro_usd=(
            None
            if budget_usd == 0
            else parse_setting(
                "PLATFORM_DAILY_SPEND_BUDGET_USD",
                budget_usd * MICRO_USD_PER_USD,
                PlatformDailySpendBudgetMicroUsd,
            )
        ),
        call_max_duration_seconds=integer(
            "CALL_MAX_DURATION_SECONDS",
            DEFAULT_CALL_MAX_DURATION_SECONDS,
            CallMaxDurationSeconds,
        ),
        call_silence_end_seconds=integer(
            "CALL_SILENCE_END_SECONDS",
            DEFAULT_CALL_SILENCE_END_SECONDS,
            CallSilenceEndSeconds,
        ),
        api_requests_per_user_per_minute=integer(
            "API_REQUESTS_PER_USER_PER_MINUTE",
            DEFAULT_API_REQUESTS_PER_USER_PER_MINUTE,
            ApiRequestsPerMinute,
        ),
        api_requests_per_ip_per_minute=integer(
            "API_REQUESTS_PER_IP_PER_MINUTE",
            DEFAULT_API_REQUESTS_PER_IP_PER_MINUTE,
            ApiRequestsPerMinute,
        ),
        api_exports_per_user_per_minute=integer(
            "API_EXPORTS_PER_USER_PER_MINUTE",
            DEFAULT_API_EXPORTS_PER_USER_PER_MINUTE,
            ApiRequestsPerMinute,
        ),
    )
    if int(settings.hard_limit_multiple) < int(settings.soft_limit_multiple):
        raise ValidationFailedError(
            "SPEND_HARD_LIMIT_MULTIPLE must not be below SPEND_SOFT_LIMIT_MULTIPLE."
        )

    return SpendGuardSettingsSection(spend_guard=settings)
