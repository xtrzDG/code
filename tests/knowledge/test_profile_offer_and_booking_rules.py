"""The offer step and booking rules: the business currency and niche defaults."""

import pytest

from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.knowledge import KnowledgeItemKind, KnowledgeItemSource
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.knowledge_admin import KnowledgeItemUpsertInput
from app.schemas.dto.profiles.business_profile import (
    BookingRulesInput,
)
from app.schemas.dto.profiles.profile_steps import (
    BookingRulesStepInput,
    OfferStepInput,
)
from app.schemas.exceptions.application_errors import (
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import (
    MinNoticeMinutes,
    PartySize,
    SlotDurationMinutes,
)
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
)
from app.schemas.typings.profiles.strings import (
    CancellationPolicyText,
)
from tests.knowledge.harness import KnowledgeHarness
from tests.knowledge.wizard_helpers import answer, save_step


def test_offer_step_upserts_items_in_the_business_currency_without_duplicates() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    offer = OfferStepInput(
        items=[
            KnowledgeItemUpsertInput(
                kind=KnowledgeItemKind.MENU_ITEM,
                title=KnowledgeTitle("Хачапури по-аджарски"),
                price_minor=MoneyAmountMinor(1800),
            )
        ]
    )

    first = save_step(harness, business.id, offer)
    second = save_step(harness, business.id, offer)

    assert len(first.saved_knowledge_items) == 1
    assert first.saved_knowledge_items[0].currency_code == "GEL"
    assert first.saved_knowledge_items[0].formatted_price == "18,00\xa0₾"
    assert first.saved_knowledge_items[0].source is KnowledgeItemSource.PROFILE
    assert second.saved_knowledge_items[0].id == first.saved_knowledge_items[0].id
    assert len(harness.knowledge_item_repo.list_by_business(business.id)) == 1


def test_offer_step_rejects_prices_in_another_currency_and_saves_nothing() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    with pytest.raises(ValidationFailedError, match="business currency GEL"):
        save_step(
            harness,
            business.id,
            OfferStepInput(
                items=[
                    KnowledgeItemUpsertInput(
                        kind=KnowledgeItemKind.MENU_ITEM,
                        title=KnowledgeTitle("Pizza"),
                        price_minor=MoneyAmountMinor(900),
                    ),
                    KnowledgeItemUpsertInput(
                        kind=KnowledgeItemKind.MENU_ITEM,
                        title=KnowledgeTitle("Pasta"),
                        price_minor=MoneyAmountMinor(1200),
                        currency_code=CurrencyCode("EUR"),
                    ),
                ]
            ),
        )

    assert harness.knowledge_item_repo.list_by_business(business.id) == []


def test_booking_rules_use_niche_defaults_and_the_business_currency() -> None:
    harness = KnowledgeHarness()
    hotel = harness.add_business(
        niche_key=NicheKey.HOTEL,
        country_code="JP",
        currency_code="JPY",
        timezone="Asia/Tokyo",
        languages=("ja", "en"),
        owner_language="en",
    )

    result = save_step(
        harness,
        hotel.id,
        BookingRulesStepInput(
            booking_rules=BookingRulesInput(
                max_party_size=PartySize(4),
                min_notice_minutes=MinNoticeMinutes(120),
                deposit_minor=MoneyAmountMinor(5000),
                cancellation_policy=CancellationPolicyText("  Free until 24h  "),
            ),
            answers=[
                answer("check_in_time", "15:00"),
                answer("check_out_time", "11:00"),
            ],
        ),
    )

    rules = result.profile.booking_rules
    assert rules is not None
    assert rules.resource_kind is ResourceKind.ROOM
    assert rules.slot_minutes == 1440
    assert rules.deposit_minor == 5000
    assert rules.deposit_currency_code == "JPY"
    assert rules.cancellation_policy == "  Free until 24h  "


def test_booking_rules_reject_foreign_deposits_and_non_booking_niches() -> None:
    harness = KnowledgeHarness()
    restaurant = harness.add_business(
        country_code="FR",
        currency_code="EUR",
        timezone="Europe/Paris",
        languages=("fr", "en"),
        owner_language="fr",
    )
    shop = harness.add_business(niche_key=NicheKey.ONLINE_SHOP)

    with pytest.raises(ValidationFailedError, match="business currency EUR"):
        save_step(
            harness,
            restaurant.id,
            BookingRulesStepInput(
                booking_rules=BookingRulesInput(
                    max_party_size=PartySize(8),
                    deposit_minor=MoneyAmountMinor(1000),
                    deposit_currency_code=CurrencyCode("USD"),
                )
            ),
        )

    with pytest.raises(ValidationFailedError, match="takes no bookings"):
        save_step(
            harness,
            shop.id,
            BookingRulesStepInput(
                booking_rules=BookingRulesInput(max_party_size=PartySize(1))
            ),
        )

    defaults = save_step(
        harness,
        restaurant.id,
        BookingRulesStepInput(
            booking_rules=BookingRulesInput(
                max_party_size=PartySize(8),
                slot_minutes=SlotDurationMinutes(30),
                deposit_minor=MoneyAmountMinor(0),
            )
        ),
    )
    assert defaults.profile.booking_rules is not None
    assert defaults.profile.booking_rules.slot_minutes == 30
    assert defaults.profile.booking_rules.deposit_minor is None
    assert defaults.profile.booking_rules.deposit_currency_code is None
