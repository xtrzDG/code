from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.booleans import IsVoiceEnabled
from app.schemas.typings.localization.constrained_strings import CurrencyCode


class Money(ImmutableDTO):
    """Amount in minor units of an ISO 4217 currency."""

    amount_minor: MoneyAmountMinor
    currency_code: CurrencyCode


class PlanDefinition(ImmutableDTO):
    """Subscription plan with its base price in EUR."""

    key: PlanKey
    names: LocalizedText
    descriptions: LocalizedText
    monthly_price: Money
    setup_fee: Money
    channels: list[ChannelKind]
    is_voice_included: IsVoiceEnabled
