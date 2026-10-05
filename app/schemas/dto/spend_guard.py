"""The spend guard: today's spend, the limits it is held against, the verdict."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.configurations.spend_guard_settings import (
    DEFAULT_CALL_MAX_DURATION_SECONDS,
    DEFAULT_CALL_SILENCE_END_SECONDS,
)
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.spend import (
    OwnerAction,
    RequestLimitClass,
    SpendLevel,
    SpendProvider,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    UsageQuantityTotal,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.spend.constrained_integers import (
    CallMaxDurationSeconds,
    CallSilenceEndSeconds,
    DailySpendLimitMicroUsd,
    SpendPercent,
)
from app.schemas.typings.spend.constrained_strings import SpendDay
from app.schemas.typings.users.prefixed_id import UserId


class UsageKindTotal(ImmutableDTO):
    """The usage of one kind in a window, summed by the database."""

    kind: UsageKind
    quantity: UsageQuantityTotal
    cost_micro_usd: CostMicroUsd


class ProviderSpend(ImmutableDTO):
    """What the platform owes one provider for a window (planned prices fill gaps)."""

    provider: SpendProvider
    spend_micro_usd: CostMicroUsd


class SpendLimits(ImmutableDTO):
    """A business's daily spend ceilings: its own, else its plan's defaults."""

    soft_limit_micro_usd: DailySpendLimitMicroUsd
    hard_limit_micro_usd: DailySpendLimitMicroUsd


class SpendCheckRequest(ImmutableDTO):
    """
    Check a business's spend of its day before a model turn (`model_id`:
    the model the turn would use) or a call (no model of ours).
    """

    business: BusinessDocument
    now: Microseconds
    model_id: LlmModelId | None = None


class SpendVerdict(ImmutableDTO):
    """
    Where the business stands today. `cheaper_model_id`: the model to answer
    on past the soft limit (None at NORMAL and HARD_LIMIT).
    """

    level: SpendLevel
    day: SpendDay
    spend_micro_usd: CostMicroUsd
    limits: SpendLimits
    cheaper_model_id: LlmModelId | None = None


class SpendLimitPassing(ImmutableDTO):
    """A business passed one of its limits today, for the first time."""

    business: BusinessDocument
    level: SpendLevel
    day: SpendDay
    spend_micro_usd: CostMicroUsd
    limit_micro_usd: DailySpendLimitMicroUsd
    providers: list[ProviderSpend] = Field(default_factory=list[ProviderSpend])


class BusinessSpendMark(ImmutableDTO):
    """A business that passed a limit today, for the admin's spend tile."""

    business_id: BusinessId
    business_name: BusinessName
    level: SpendLevel
    spend_micro_usd: CostMicroUsd
    limit_micro_usd: DailySpendLimitMicroUsd
    reached_at: Microseconds


class PlatformSpendView(ImmutableDTO):
    """
    The admin overview's spend tile: the platform's provider spend of the
    current UTC day by provider, the daily mean of the 7 days before, the
    daily budget (when set) and how much of it is used, and the businesses
    that passed one of their limits today.
    """

    day: SpendDay
    total_micro_usd: CostMicroUsd
    providers: list[ProviderSpend]
    week_daily_mean_micro_usd: CostMicroUsd
    budget_micro_usd: CostMicroUsd | None = None
    budget_used_percent: SpendPercent | None = None
    braked_businesses: list[BusinessSpendMark] = Field(
        default_factory=list[BusinessSpendMark]
    )


class VoiceCallLimits(ImmutableDTO):
    """
    The caps of every call of a voice agent (CALL_MAX_DURATION_SECONDS,
    CALL_SILENCE_END_SECONDS): the voice platform ends a call at that length
    or after that much silence, so a prank or a forgotten line cannot run up
    minutes.
    """

    max_duration_seconds: CallMaxDurationSeconds = CallMaxDurationSeconds(
        DEFAULT_CALL_MAX_DURATION_SECONDS
    )
    silence_end_seconds: CallSilenceEndSeconds = CallSilenceEndSeconds(
        DEFAULT_CALL_SILENCE_END_SECONDS
    )


class OwnerActionAdmission(ImmutableDTO):
    """A person of a business is about to take a limited cabinet action."""

    action: OwnerAction
    user_id: UserId
    business_id: BusinessId


class ApiRequestAdmission(ImmutableDTO):
    """
    One API request to count against the generic limits: a signed-in
    person's (`user_id`, by the class of request) or, without a token, its
    client address's.
    """

    limit_class: RequestLimitClass = RequestLimitClass.GENERAL
    user_id: UserId | None = None
    client_ip_address: ClientIpAddress | None = None


class PlatformSpendFigures(ImmutableDTO):
    """The platform's spend of the current UTC day and of the 7 days before."""

    day: SpendDay
    providers: list[ProviderSpend]
    total_micro_usd: CostMicroUsd
    week_total_micro_usd: CostMicroUsd
    week_daily_mean_micro_usd: CostMicroUsd


class AdminSpendQuery(ImmutableDTO):
    """A platform admin opens the overview's spend tile."""

    user_id: UserId


class BusinessSpendLimitsRequest(ImmutableDTO):
    """
    A business's own daily spend limits in micro-USD; None returns that
    limit to the plan's default.
    """

    soft_limit_micro_usd: DailySpendLimitMicroUsd | None = None
    hard_limit_micro_usd: DailySpendLimitMicroUsd | None = None


class BusinessSpendLimitsCommand(ImmutableDTO):
    """A platform admin sets a client's daily spend limits."""

    user_id: UserId
    business_id: BusinessId
    request: BusinessSpendLimitsRequest


class BusinessSpendLimitsView(ImmutableDTO):
    """A client's own daily spend limits (None: the plan's default)."""

    business_id: BusinessId
    soft_limit_micro_usd: DailySpendLimitMicroUsd | None = None
    hard_limit_micro_usd: DailySpendLimitMicroUsd | None = None
