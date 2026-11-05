from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.spend import SpendLevel
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.spend.constrained_integers import DailySpendLimitMicroUsd
from app.schemas.typings.spend.constrained_strings import SpendDay
from app.schemas.typings.spend.prefixed_id import BusinessLimitsId, SpendLimitMarkId


class BusinessLimitsDocument(BaseDocument):
    """
    The limits of one business, one document per business (the id derives
    from it); a business without one keeps the defaults.

    `widget_allowed_origins`: the websites (scheme, host and port, no path)
    that may show the business's website chat. Empty: any website may (the
    default, as before the list existed). The cabinet's own pages (the
    hosted chat page and the live preview) always may.
    `daily_soft_limit_micro_usd`, `daily_hard_limit_micro_usd`: the
    business's own spend ceilings for one of its days, set by the platform
    team; None keeps the plan's defaults (a multiple of its planned daily
    provider cost, `spend_limit_defaults`).
    """

    id: BusinessLimitsId
    business_id: BusinessId
    widget_allowed_origins: list[PublicBaseUrl] = Field(
        default_factory=list[PublicBaseUrl]
    )
    daily_soft_limit_micro_usd: DailySpendLimitMicroUsd | None = None
    daily_hard_limit_micro_usd: DailySpendLimitMicroUsd | None = None


class SpendLimitMarkDocument(BaseDocument):
    """
    One business passed one of its spend limits on one of its days (its own
    time zone): what it had spent by then and the limit it passed.

    The id derives from the business, the day and the level, and a mark is
    only ever inserted when absent: of several processes that see the limit
    passed at once, one stores it and tells the owner and the platform team
    (and, past the hard limit, writes the audit entry). A hard mark also
    lets the next turns of the day skip the spend sum.
    """

    id: SpendLimitMarkId
    business_id: BusinessId
    day: SpendDay
    level: SpendLevel
    spend_micro_usd: CostMicroUsd
    limit_micro_usd: DailySpendLimitMicroUsd
    reached_at: Microseconds
