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
from app.utilities.localization.localized_texts import build_localized_text

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
        names=build_localized_text(en="Chat", ru="Чат", ka="ჩატი"),
        descriptions=build_localized_text(
            en="Up to 1,000 dialogs a month in WhatsApp, Instagram, Messenger, "
            "Telegram and the website chat. For cafes, salons, shops, tours "
            "and guest houses.",
            ru="До 1 000 диалогов в месяц в WhatsApp, Instagram, Messenger, "
            "Telegram и чате на сайте. Для кафе, салонов, магазинов, туров и "
            "гостевых домов.",
            ka="თვეში 1 000-მდე დიალოგი WhatsApp-ში, Instagram-ში, Messenger-ში, "
            "Telegram-სა და საიტის ჩატში. კაფეების, სალონების, მაღაზიების, "
            "ტურებისა და საოჯახო სასტუმროებისთვის.",
        ),
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
        names=build_localized_text(
            en="Voice + chat", ru="Голос + чат", ka="ხმა + ჩატი"
        ),
        descriptions=build_localized_text(
            en="400 call minutes and 1,500 dialogs a month: phone calls plus "
            "every messaging channel. For restaurants, hotels, clinics, "
            "entertainment and car services.",
            ru="400 минут звонков и 1 500 диалогов в месяц: телефон и все "
            "мессенджеры. Для ресторанов, отелей, клиник, развлечений и "
            "автосервисов.",
            ka="თვეში 400 წუთი ზარი და 1 500 დიალოგი: ტელეფონი და ყველა "
            "მესენჯერი. რესტორნების, სასტუმროების, კლინიკების, გართობისა და "
            "ავტოსერვისებისთვის.",
        ),
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
        names=build_localized_text(en="Plus", ru="Плюс", ka="პლუსი"),
        descriptions=build_localized_text(
            en="1,000 call minutes and 3,000 dialogs a month. For busy "
            "restaurants, hotels, clinics and real estate agencies that get "
            "many calls and messages every day.",
            ru="1 000 минут звонков и 3 000 диалогов в месяц. Для загруженных "
            "ресторанов, отелей, клиник и агентств недвижимости, которым "
            "каждый день много звонят и пишут.",
            ka="თვეში 1 000 წუთი ზარი და 3 000 დიალოგი. დატვირთული "
            "რესტორნების, სასტუმროების, კლინიკებისა და უძრავი ქონების "
            "სააგენტოებისთვის, რომლებსაც ყოველდღე ბევრი ურეკავს და სწერს.",
        ),
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
