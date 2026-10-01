from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.billing.constrained_integers import (
    DiscountPercent,
    GracePeriodDays,
    IncludedDialogs,
    IncludedVoiceMinutes,
    MoneyAmountMinor,
    TrialDays,
)
from app.schemas.typings.businesses.booleans import IsVoiceEnabled
from app.schemas.typings.localization.constrained_strings import CurrencyCode


class Money(ImmutableDTO):
    """Amount in minor units of an ISO 4217 currency."""

    amount_minor: MoneyAmountMinor
    currency_code: CurrencyCode


class PlanDefinition(ImmutableDTO):
    """
    Subscription plan with a package (concept "Цены и тарифы").

    Prices are defined in EUR; local-currency prices come from the price book.
    """

    key: PlanKey
    names: LocalizedText
    descriptions: LocalizedText
    monthly_price: Money
    setup_fee: Money
    included_voice_minutes: IncludedVoiceMinutes
    included_dialogs: IncludedDialogs
    overage_price_per_minute: Money
    annual_discount_percent: DiscountPercent
    trial_days: TrialDays
    grace_period_days: GracePeriodDays
    channels: list[ChannelKind]
    is_voice_included: IsVoiceEnabled
