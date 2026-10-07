"""
Plans from the concept ("Цены и тарифы", ТЗ section 9).

Prices are set in EUR. The price book adds explicit prices in local
currencies: in Georgia the concept lists 293 / 517 / 1 031 GEL a month and
443 GEL setup. The overage price has no price-book entry: the concept gives
it as "≈ 0.44 GEL", a conversion of 0.15 EUR.

The setup fee is per setup option: the owner who sets the assistant up in
the cabinet's guided setup (SELF_SERVE) pays nothing; DONE_FOR_YOU, where
the platform team sets it up, costs the concept's 150 EUR / 443 GEL.
"""

from app.schemas.constants.billing import PlanKey, SetupOption
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.billing import Money, PlanDefinition, SetupOptionFee
from app.schemas.typings.billing.constrained_integers import (
    DiscountPercent,
    GracePeriodDays,
    IncludedDialogs,
    IncludedVoiceMinutes,
    MoneyAmountMinor,
    TrialDays,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.localization.owner_texts import owner_text

PLAN_BASE_CURRENCY: CurrencyCode = CurrencyCode("EUR")
GEORGIAN_LARI: CurrencyCode = CurrencyCode("GEL")
SETUP_FEE: Money = Money(
    amount_minor=MoneyAmountMinor(15000),
    currency_code=PLAN_BASE_CURRENCY,
)
SETUP_FEES: list[SetupOptionFee] = [
    SetupOptionFee(
        option=SetupOption.SELF_SERVE,
        fee=Money(amount_minor=MoneyAmountMinor(0), currency_code=PLAN_BASE_CURRENCY),
    ),
    SetupOptionFee(option=SetupOption.DONE_FOR_YOU, fee=SETUP_FEE),
]
OVERAGE_PRICE_PER_MINUTE: Money = Money(
    amount_minor=MoneyAmountMinor(15),
    currency_code=PLAN_BASE_CURRENCY,
)
ANNUAL_DISCOUNT_PERCENT: DiscountPercent = DiscountPercent(15)
TRIAL_DAYS: TrialDays = TrialDays(14)
GRACE_PERIOD_DAYS: GracePeriodDays = GracePeriodDays(7)
MESSAGING_CHANNELS: tuple[ChannelKind, ...] = (
    ChannelKind.WHATSAPP,
    ChannelKind.INSTAGRAM,
    ChannelKind.MESSENGER,
    ChannelKind.TELEGRAM,
    ChannelKind.WEB_CHAT,
)
VOICE_AND_MESSAGING_CHANNELS: tuple[ChannelKind, ...] = (
    ChannelKind.PHONE,
    *MESSAGING_CHANNELS,
)


def build_eur_price(amount_in_cents: int) -> Money:
    return Money(
        amount_minor=MoneyAmountMinor(amount_in_cents),
        currency_code=PLAN_BASE_CURRENCY,
    )


def build_gel_price(amount_in_tetri: int) -> Money:
    return Money(
        amount_minor=MoneyAmountMinor(amount_in_tetri),
        currency_code=GEORGIAN_LARI,
    )


PLAN_DEFINITIONS: tuple[PlanDefinition, ...] = (
    PlanDefinition(
        key=PlanKey.CHAT,
        names=owner_text("plans.chat.name"),
        descriptions=owner_text("plans.chat.description"),
        monthly_price=build_eur_price(9900),
        setup_fee=SETUP_FEE,
        included_voice_minutes=IncludedVoiceMinutes(0),
        included_dialogs=IncludedDialogs(1000),
        overage_price_per_minute=OVERAGE_PRICE_PER_MINUTE,
        annual_discount_percent=ANNUAL_DISCOUNT_PERCENT,
        trial_days=TRIAL_DAYS,
        grace_period_days=GRACE_PERIOD_DAYS,
        channels=list(MESSAGING_CHANNELS),
        is_voice_included=False,
        setup_fees=SETUP_FEES,
    ),
    PlanDefinition(
        key=PlanKey.VOICE_AND_CHAT,
        names=owner_text("plans.voice_and_chat.name"),
        descriptions=owner_text("plans.voice_and_chat.description"),
        monthly_price=build_eur_price(17500),
        setup_fee=SETUP_FEE,
        included_voice_minutes=IncludedVoiceMinutes(400),
        included_dialogs=IncludedDialogs(1500),
        overage_price_per_minute=OVERAGE_PRICE_PER_MINUTE,
        annual_discount_percent=ANNUAL_DISCOUNT_PERCENT,
        trial_days=TRIAL_DAYS,
        grace_period_days=GRACE_PERIOD_DAYS,
        channels=list(VOICE_AND_MESSAGING_CHANNELS),
        is_voice_included=True,
        setup_fees=SETUP_FEES,
    ),
    PlanDefinition(
        key=PlanKey.PLUS,
        names=owner_text("plans.plus.name"),
        descriptions=owner_text("plans.plus.description"),
        monthly_price=build_eur_price(34900),
        setup_fee=SETUP_FEE,
        included_voice_minutes=IncludedVoiceMinutes(1000),
        included_dialogs=IncludedDialogs(3000),
        overage_price_per_minute=OVERAGE_PRICE_PER_MINUTE,
        annual_discount_percent=ANNUAL_DISCOUNT_PERCENT,
        trial_days=TRIAL_DAYS,
        grace_period_days=GRACE_PERIOD_DAYS,
        channels=list(VOICE_AND_MESSAGING_CHANNELS),
        is_voice_included=True,
        setup_fees=SETUP_FEES,
    ),
)

# Explicit local prices (concept: GEL price book). Never derived from a rate.
LOCAL_MONTHLY_PRICE_BOOK: dict[PlanKey, tuple[Money, ...]] = {
    PlanKey.CHAT: (build_gel_price(29300),),
    PlanKey.VOICE_AND_CHAT: (build_gel_price(51700),),
    PlanKey.PLUS: (build_gel_price(103100),),
}
# The DONE_FOR_YOU setup fee; SELF_SERVE is free in every currency.
LOCAL_SETUP_FEE_BOOK: dict[PlanKey, tuple[Money, ...]] = {
    PlanKey.CHAT: (build_gel_price(44300),),
    PlanKey.VOICE_AND_CHAT: (build_gel_price(44300),),
    PlanKey.PLUS: (build_gel_price(44300),),
}
