from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.spend.constrained_integers import (
    ApiRequestsPerMinute,
    CallMaxDurationSeconds,
    CallSilenceEndSeconds,
    PlatformDailySpendBudgetMicroUsd,
    SpendLimitMultiple,
)

DEFAULT_SOFT_LIMIT_MULTIPLE: int = 5
DEFAULT_HARD_LIMIT_MULTIPLE: int = 15
DEFAULT_CALL_MAX_DURATION_SECONDS: int = 600
DEFAULT_CALL_SILENCE_END_SECONDS: int = 30
DEFAULT_API_REQUESTS_PER_USER_PER_MINUTE: int = 600
DEFAULT_API_REQUESTS_PER_IP_PER_MINUTE: int = 120
DEFAULT_API_EXPORTS_PER_USER_PER_MINUTE: int = 30


class SpendGuardSettings(ImmutableDTO):
    """
    Brakes on what abuse may cost: daily spend limits per business, the
    platform's daily budget, voice call caps and generic API limits.

    `soft_limit_multiple`, `hard_limit_multiple` (SPEND_SOFT_LIMIT_MULTIPLE,
    SPEND_HARD_LIMIT_MULTIPLE; 5 and 15): a business's default daily spend
    limits as multiples of its plan's planned daily provider cost; the
    platform team may set a business's own (`business_limits`).
    `soft_limit_model_id` (SPEND_SOFT_LIMIT_MODEL_ID): the cheaper model a
    business answers on past its soft limit; unset, the cheaper model of
    the assistant's own provider (`cheaper_model_of`).
    `platform_daily_budget_micro_usd` (PLATFORM_DAILY_SPEND_BUDGET_USD, in
    whole dollars): the spend the platform plans for a UTC day; the
    `spend_budget` alert fires at 80 % of it. Unset: no budget alert.
    `call_max_duration_seconds`, `call_silence_end_seconds`
    (CALL_MAX_DURATION_SECONDS 600, CALL_SILENCE_END_SECONDS 30): the voice
    agent ends a call at that length or after that much silence.
    `api_requests_per_user_per_minute` (API_REQUESTS_PER_USER_PER_MINUTE,
    600), `api_exports_per_user_per_minute` (API_EXPORTS_PER_USER_PER_MINUTE,
    30) and `api_requests_per_ip_per_minute` (API_REQUESTS_PER_IP_PER_MINUTE,
    120, requests without a token): the generic request limits (429 with
    Retry-After).
    """

    soft_limit_multiple: SpendLimitMultiple = SpendLimitMultiple(
        DEFAULT_SOFT_LIMIT_MULTIPLE
    )
    hard_limit_multiple: SpendLimitMultiple = SpendLimitMultiple(
        DEFAULT_HARD_LIMIT_MULTIPLE
    )
    soft_limit_model_id: LlmModelId | None = None
    platform_daily_budget_micro_usd: PlatformDailySpendBudgetMicroUsd | None = None
    call_max_duration_seconds: CallMaxDurationSeconds = CallMaxDurationSeconds(
        DEFAULT_CALL_MAX_DURATION_SECONDS
    )
    call_silence_end_seconds: CallSilenceEndSeconds = CallSilenceEndSeconds(
        DEFAULT_CALL_SILENCE_END_SECONDS
    )
    api_requests_per_user_per_minute: ApiRequestsPerMinute = ApiRequestsPerMinute(
        DEFAULT_API_REQUESTS_PER_USER_PER_MINUTE
    )
    api_requests_per_ip_per_minute: ApiRequestsPerMinute = ApiRequestsPerMinute(
        DEFAULT_API_REQUESTS_PER_IP_PER_MINUTE
    )
    api_exports_per_user_per_minute: ApiRequestsPerMinute = ApiRequestsPerMinute(
        DEFAULT_API_EXPORTS_PER_USER_PER_MINUTE
    )
