from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.registries import PlanRegistryContract
from app.registries.billing.exchange_rate_registry import ExchangeRateRegistry
from app.registries.billing.plan_registry import PlanRegistry
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.billing import Money
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)

PLANS: PlanRegistryContract = PlanRegistry()
RATES: ExchangeRateRegistryContract = ExchangeRateRegistry()


def money(amount_minor: int, currency_code: str) -> Money:
    return Money(
        amount_minor=MoneyAmountMinor(amount_minor),
        currency_code=CurrencyCode(currency_code),
    )


def test_plans_follow_the_concept() -> None:
    chat = PLANS.get(PlanKey.CHAT)
    voice = PLANS.get(PlanKey.VOICE_AND_CHAT)
    plus = PLANS.get(PlanKey.PLUS)

    assert (chat.monthly_price, voice.monthly_price, plus.monthly_price) == (
        money(9900, "EUR"),
        money(17500, "EUR"),
        money(34900, "EUR"),
    )
    assert (chat.included_voice_minutes, chat.included_dialogs) == (0, 1000)
    assert (voice.included_voice_minutes, voice.included_dialogs) == (400, 1500)
    assert (plus.included_voice_minutes, plus.included_dialogs) == (1000, 3000)
    for plan in (chat, voice, plus):
        assert plan.setup_fee == money(15000, "EUR")
        assert plan.overage_price_per_minute == money(15, "EUR")
        assert plan.annual_discount_percent == 15
        assert plan.trial_days == 14
        assert plan.grace_period_days == 7
        for language in ("en", "ru", "ka"):
            assert LanguageTag(language) in plan.names.values
            assert LanguageTag(language) in plan.descriptions.values


def test_only_voice_plans_include_the_phone() -> None:
    chat = PLANS.get(PlanKey.CHAT)
    voice = PLANS.get(PlanKey.VOICE_AND_CHAT)

    assert ChannelKind.PHONE not in chat.channels
    assert chat.is_voice_included is False
    assert ChannelKind.PHONE in voice.channels
    assert voice.is_voice_included is True
    assert set(chat.channels) == {
        ChannelKind.WHATSAPP,
        ChannelKind.INSTAGRAM,
        ChannelKind.MESSENGER,
        ChannelKind.TELEGRAM,
        ChannelKind.WEB_CHAT,
    }


def test_list_all_is_in_plan_order() -> None:
    assert [plan.key for plan in PLANS.list_all()] == [
        PlanKey.CHAT,
        PlanKey.VOICE_AND_CHAT,
        PlanKey.PLUS,
    ]


def test_price_book_has_lari_prices_and_no_invented_currencies() -> None:
    gel = CurrencyCode("GEL")

    assert PLANS.find_local_monthly_price(PlanKey.CHAT, gel) == money(29300, "GEL")
    assert PLANS.find_local_monthly_price(PlanKey.VOICE_AND_CHAT, gel) == money(
        51700, "GEL"
    )
    assert PLANS.find_local_monthly_price(PlanKey.PLUS, gel) == money(103100, "GEL")
    assert PLANS.find_local_setup_fee(PlanKey.PLUS, gel) == money(44300, "GEL")
    assert PLANS.find_local_monthly_price(PlanKey.PLUS, CurrencyCode("EUR")) == money(
        34900, "EUR"
    )
    assert PLANS.find_local_monthly_price(PlanKey.CHAT, CurrencyCode("USD")) is None
    assert PLANS.find_local_setup_fee(PlanKey.CHAT, CurrencyCode("AMD")) is None


def test_returned_plans_are_copies() -> None:
    plan = PLANS.get(PlanKey.CHAT)
    plan.channels.append(ChannelKind.PHONE)

    assert ChannelKind.PHONE not in PLANS.get(PlanKey.CHAT).channels


def test_exchange_rates_are_official_and_direct_only() -> None:
    eur_to_gel = RATES.find_rate(CurrencyCode("EUR"), CurrencyCode("GEL"))

    assert eur_to_gel is not None
    assert eur_to_gel.rate == 2.9552
    assert eur_to_gel.rate_date == "2026-09-30"
    assert eur_to_gel.source == "National Bank of Georgia"
    assert RATES.find_rate(CurrencyCode("GEL"), CurrencyCode("EUR")) is None
    assert RATES.find_rate(CurrencyCode("EUR"), CurrencyCode("USD")) is None
    assert RATES.list_all() == [eur_to_gel]
