from datetime import UTC, datetime, timedelta

import pytest

from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.constants.knowledge import KnowledgeItemKind, KnowledgeItemSource
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeAttribute
from app.schemas.domain.profiles import BusinessAddress, BusinessLink
from app.schemas.dto.knowledge import (
    KnowledgeSearchRequest,
    PriceLookupQuery,
    SendLinkQuery,
)
from app.schemas.dto.knowledge_admin import (
    CreateKnowledgeItemCommand,
    DeleteKnowledgeItemCommand,
    KnowledgeItemDetails,
    KnowledgeItemInput,
    KnowledgeItemListQuery,
    KnowledgeItemPatch,
    KnowledgeItemQuery,
    KnowledgeItemUpsertInput,
    UpdateKnowledgeItemCommand,
    UpsertKnowledgeItemsCommand,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.dto.profiles import (
    ChannelsStepInput,
    ContactsAndHoursStepInput,
    ProfileStepInput,
    SaveProfileStepCommand,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import AddressText
from app.schemas.typings.knowledge.constrained_integers import (
    KnowledgeSearchLimit,
    ServiceDurationMinutes,
)
from app.schemas.typings.knowledge.constrained_strings import (
    KnowledgeAttributeKey,
    KnowledgeTag,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import (
    KnowledgeAttributeValue,
    KnowledgeBody,
    KnowledgeSearchQuery,
    KnowledgeTitle,
)
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.users.prefixed_id import UserId
from tests.knowledge.harness import DEFAULT_NOW, KnowledgeHarness


def add_item(
    harness: KnowledgeHarness,
    business: BusinessDocument,
    title: str,
    kind: KnowledgeItemKind = KnowledgeItemKind.MENU_ITEM,
    price_minor: int | None = None,
    body: str | None = None,
    is_active: bool = True,
    languages: tuple[str, ...] = (),
) -> KnowledgeItemDetails:
    return harness.create_knowledge_item.run(
        CreateKnowledgeItemCommand(
            business_id=business.id,
            item=KnowledgeItemInput(
                kind=kind,
                title=KnowledgeTitle(title),
                body=None if body is None else KnowledgeBody(body),
                price_minor=(
                    None if price_minor is None else MoneyAmountMinor(price_minor)
                ),
                is_active=is_active,
                languages=[LanguageTag(language) for language in languages],
            ),
        )
    )


def search(
    harness: KnowledgeHarness,
    business: BusinessDocument,
    query: str,
    language: str,
    limit: int = 5,
) -> list[str]:
    result = harness.search_knowledge.run(
        KnowledgeSearchRequest(
            business_id=business.id,
            query=KnowledgeSearchQuery(query),
            language=LanguageTag(language),
            limit=KnowledgeSearchLimit(limit),
        )
    )
    return [item.title for item in result.items]


def price_titles(
    harness: KnowledgeHarness,
    business: BusinessDocument,
    item_name: str,
    language: str = "en",
) -> list[str]:
    result = harness.get_price.run(
        PriceLookupQuery(
            business_id=business.id,
            item_name=KnowledgeTitle(item_name),
            language=LanguageTag(language),
        )
    )
    return [match.title for match in result.matches]


def save_step(
    harness: KnowledgeHarness,
    business: BusinessDocument,
    step_input: ProfileStepInput,
) -> None:
    harness.save_profile_step.run(
        SaveProfileStepCommand(
            business_id=business.id,
            actor_id=UserId(),
            step_input=step_input,
        )
    )


@pytest.mark.parametrize(
    ("country", "currency", "timezone", "language", "price_minor", "expected"),
    [
        ("GE", "GEL", "Asia/Tbilisi", "ka", 1850, "18,50\xa0₾"),
        ("IT", "EUR", "Europe/Rome", "it", 1250, "12,50\xa0€"),
        ("JP", "JPY", "Asia/Tokyo", "ja", 1500, "￥1,500"),
    ],
)
def test_prices_are_stored_and_formatted_in_the_business_currency(
    country: str,
    currency: str,
    timezone: str,
    language: str,
    price_minor: int,
    expected: str,
) -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(
        country_code=country,
        currency_code=currency,
        timezone=timezone,
        languages=(language, "en"),
        owner_language=language,
    )

    details = add_item(harness, business, "Dish", price_minor=price_minor)

    assert details.price_minor == price_minor
    assert details.currency_code == currency
    assert details.formatted_price == expected
    assert details.source is KnowledgeItemSource.OWNER
    assert details.created_at == harness.wall_clock.now_unix()


@pytest.mark.parametrize("foreign_currency", ["USD", "EUR", "JPY"])
def test_prices_in_another_currency_are_rejected(foreign_currency: str) -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    with pytest.raises(ValidationFailedError, match="business currency GEL"):
        harness.create_knowledge_item.run(
            CreateKnowledgeItemCommand(
                business_id=business.id,
                item=KnowledgeItemInput(
                    kind=KnowledgeItemKind.MENU_ITEM,
                    title=KnowledgeTitle("Khachapuri"),
                    price_minor=MoneyAmountMinor(1800),
                    currency_code=CurrencyCode(foreign_currency),
                ),
            )
        )


def test_items_are_checked_against_the_niche_and_kept_as_written() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(niche_key=NicheKey.HOTEL)

    details = harness.create_knowledge_item.run(
        CreateKnowledgeItemCommand(
            business_id=business.id,
            item=KnowledgeItemInput(
                kind=KnowledgeItemKind.ROOM_TYPE,
                title=KnowledgeTitle("  Double room  "),
                body=KnowledgeBody("   "),
                price_minor=MoneyAmountMinor(25000),
                currency_code=CurrencyCode("GEL"),
                duration_minutes=ServiceDurationMinutes(1440),
                tags=[KnowledgeTag("sea-view"), KnowledgeTag("sea-view")],
                attributes=[
                    KnowledgeAttribute(
                        key=KnowledgeAttributeKey("season"),
                        value=KnowledgeAttributeValue(" summer "),
                    )
                ],
                languages=[LanguageTag("en"), LanguageTag("en")],
            ),
            language=LanguageTag("ru"),
        )
    )

    assert details.title == "  Double room  "
    assert details.body is None
    assert details.tags == ["sea-view"]
    assert details.attributes[0].value == " summer "
    assert details.languages == ["en"]
    assert details.formatted_price == "250,00\xa0GEL"

    with pytest.raises(ValidationFailedError, match="does not use menu_item"):
        add_item(harness, business, "Khachapuri", kind=KnowledgeItemKind.MENU_ITEM)

    faq = add_item(harness, business, "Pets?", kind=KnowledgeItemKind.FAQ)
    assert faq.kind is KnowledgeItemKind.FAQ


@pytest.mark.parametrize(
    ("item_input", "message"),
    [
        (
            KnowledgeItemInput(kind=KnowledgeItemKind.FAQ, title=KnowledgeTitle("  ")),
            "needs a title",
        ),
        (
            KnowledgeItemInput(
                kind=KnowledgeItemKind.FAQ,
                title=KnowledgeTitle("x" * 301),
            ),
            "at most 300",
        ),
        (
            KnowledgeItemInput(
                kind=KnowledgeItemKind.FAQ,
                title=KnowledgeTitle("Parking"),
                attributes=[
                    KnowledgeAttribute(
                        key=KnowledgeAttributeKey("floor"),
                        value=KnowledgeAttributeValue("1"),
                    ),
                    KnowledgeAttribute(
                        key=KnowledgeAttributeKey("floor"),
                        value=KnowledgeAttributeValue("2"),
                    ),
                ],
            ),
            "repeated",
        ),
        (
            KnowledgeItemInput(
                kind=KnowledgeItemKind.FAQ,
                title=KnowledgeTitle("Parking"),
                attributes=[
                    KnowledgeAttribute(
                        key=KnowledgeAttributeKey("floor"),
                        value=KnowledgeAttributeValue(" "),
                    )
                ],
            ),
            "needs a value",
        ),
    ],
)
def test_invalid_items_are_rejected(
    item_input: KnowledgeItemInput, message: str
) -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    with pytest.raises(ValidationFailedError, match=message):
        harness.create_knowledge_item.run(
            CreateKnowledgeItemCommand(business_id=business.id, item=item_input)
        )


def test_patch_changes_only_given_fields_and_null_clears_optional_ones() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    created = add_item(harness, business, "Lobiani", price_minor=900, body="Beans")
    harness.clock_source.set(datetime(2026, 10, 2, 9, 0, tzinfo=UTC))

    patched = harness.update_knowledge_item.run(
        UpdateKnowledgeItemCommand(
            business_id=business.id,
            item_id=created.id,
            patch=KnowledgeItemPatch.model_validate_json(
                '{"body": null, "price_minor": 1000, "is_active": false}'
            ),
        )
    )

    assert patched.title == "Lobiani"
    assert patched.body is None
    assert patched.price_minor == 1000
    assert patched.currency_code == "GEL"
    assert patched.is_active is False
    assert patched.created_at == created.created_at
    assert patched.updated_at > created.updated_at

    cleared = harness.update_knowledge_item.run(
        UpdateKnowledgeItemCommand(
            business_id=business.id,
            item_id=created.id,
            patch=KnowledgeItemPatch.model_validate_json('{"price_minor": null}'),
        )
    )
    assert cleared.price_minor is None
    assert cleared.currency_code is None
    assert cleared.formatted_price is None

    with pytest.raises(ValidationFailedError, match="title cannot be null"):
        harness.update_knowledge_item.run(
            UpdateKnowledgeItemCommand(
                business_id=business.id,
                item_id=created.id,
                patch=KnowledgeItemPatch.model_validate_json('{"title": null}'),
            )
        )

    with pytest.raises(ValidationFailedError, match="business currency"):
        harness.update_knowledge_item.run(
            UpdateKnowledgeItemCommand(
                business_id=business.id,
                item_id=created.id,
                patch=KnowledgeItemPatch.model_validate_json(
                    '{"currency_code": "USD"}'
                ),
            )
        )


def test_patch_keeps_a_price_set_before_a_currency_change() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    created = add_item(harness, business, "Churchkhela", price_minor=500)
    business.currency_code = CurrencyCode("EUR")
    harness.business_repo.save(business)

    renamed = harness.update_knowledge_item.run(
        UpdateKnowledgeItemCommand(
            business_id=business.id,
            item_id=created.id,
            patch=KnowledgeItemPatch(title=KnowledgeTitle("Churchkhela (walnut)")),
            language=LanguageTag("en"),
        )
    )

    assert renamed.currency_code == "GEL"
    assert renamed.formatted_price == "GEL5.00"


def test_list_filters_by_kind_and_active_flag_and_pages_newest_first() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    for minute, (title, kind, is_active) in enumerate(
        [
            ("Khinkali", KnowledgeItemKind.MENU_ITEM, True),
            ("adjarian khachapuri", KnowledgeItemKind.MENU_ITEM, True),
            ("Old dish", KnowledgeItemKind.MENU_ITEM, False),
            ("Parking?", KnowledgeItemKind.FAQ, True),
        ]
    ):
        harness.clock_source.set(DEFAULT_NOW + timedelta(minutes=minute))
        add_item(harness, business, title, kind=kind, is_active=is_active)

    everything = harness.list_knowledge_items.run(
        KnowledgeItemListQuery(business_id=business.id)
    )
    active_menu = harness.list_knowledge_items.run(
        KnowledgeItemListQuery(
            business_id=business.id,
            kind=KnowledgeItemKind.MENU_ITEM,
            is_active=True,
        )
    )
    first_page = harness.list_knowledge_items.run(
        KnowledgeItemListQuery(
            business_id=business.id, page=PageRequest(size=PageSize(3))
        )
    )
    assert first_page.next_cursor is not None
    second_page = harness.list_knowledge_items.run(
        KnowledgeItemListQuery(
            business_id=business.id,
            page=PageRequest(size=PageSize(3), cursor=first_page.next_cursor),
        )
    )

    assert [item.title for item in everything.items] == [
        "Parking?",
        "Old dish",
        "adjarian khachapuri",
        "Khinkali",
    ]
    assert everything.next_cursor is None
    assert [item.title for item in active_menu.items] == [
        "adjarian khachapuri",
        "Khinkali",
    ]
    assert [item.title for item in first_page.items] == [
        "Parking?",
        "Old dish",
        "adjarian khachapuri",
    ]
    assert [item.title for item in second_page.items] == ["Khinkali"]
    assert second_page.next_cursor is None


def test_other_businesses_cannot_read_change_or_delete_an_item() -> None:
    harness = KnowledgeHarness()
    owner_business = harness.add_business()
    other_business = harness.add_business()
    created = add_item(harness, owner_business, "Secret recipe", price_minor=100)

    with pytest.raises(NotFoundError):
        harness.get_knowledge_item.run(
            KnowledgeItemQuery(business_id=other_business.id, item_id=created.id)
        )
    with pytest.raises(NotFoundError):
        harness.update_knowledge_item.run(
            UpdateKnowledgeItemCommand(
                business_id=other_business.id,
                item_id=created.id,
                patch=KnowledgeItemPatch(is_active=False),
            )
        )
    with pytest.raises(NotFoundError):
        harness.delete_knowledge_item.run(
            DeleteKnowledgeItemCommand(
                business_id=other_business.id, item_id=created.id
            )
        )

    assert search(harness, other_business, "secret recipe", "en") == []
    assert price_titles(harness, other_business, "secret recipe") == []
    assert (
        harness.get_knowledge_item.run(
            KnowledgeItemQuery(business_id=owner_business.id, item_id=created.id)
        ).title
        == "Secret recipe"
    )


def test_delete_removes_the_item() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    created = add_item(harness, business, "Lobio")

    deletion = harness.delete_knowledge_item.run(
        DeleteKnowledgeItemCommand(business_id=business.id, item_id=created.id)
    )

    assert deletion.id == created.id
    with pytest.raises(NotFoundError):
        harness.delete_knowledge_item.run(
            DeleteKnowledgeItemCommand(business_id=business.id, item_id=created.id)
        )


def test_bulk_upsert_matches_by_id_or_title_and_validates_the_whole_batch() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    existing = add_item(harness, business, "Khinkali", price_minor=120)

    saved = harness.upsert_knowledge_items.run(
        UpsertKnowledgeItemsCommand(
            business_id=business.id,
            items=[
                KnowledgeItemUpsertInput(
                    kind=KnowledgeItemKind.MENU_ITEM,
                    title=KnowledgeTitle("KHINKALI"),
                    price_minor=MoneyAmountMinor(150),
                ),
                KnowledgeItemUpsertInput(
                    kind=KnowledgeItemKind.MENU_ITEM,
                    title=KnowledgeTitle("Lobiani"),
                    price_minor=MoneyAmountMinor(900),
                ),
                KnowledgeItemUpsertInput(
                    kind=KnowledgeItemKind.MENU_ITEM,
                    title=KnowledgeTitle("lobiani"),
                    price_minor=MoneyAmountMinor(950),
                ),
            ],
            source=KnowledgeItemSource.MENU_IMPORT,
        )
    )

    assert [item.title for item in saved.items] == ["KHINKALI", "lobiani"]
    assert saved.items[0].id == existing.id
    assert saved.items[0].source is KnowledgeItemSource.OWNER
    assert saved.items[1].source is KnowledgeItemSource.MENU_IMPORT
    assert saved.items[1].price_minor == 950
    assert len(harness.knowledge_item_repo.list_by_business(business.id)) == 2

    with pytest.raises(NotFoundError):
        harness.upsert_knowledge_items.run(
            UpsertKnowledgeItemsCommand(
                business_id=business.id,
                items=[
                    KnowledgeItemUpsertInput(
                        id=KnowledgeItemId(),
                        kind=KnowledgeItemKind.FAQ,
                        title=KnowledgeTitle("Unknown"),
                    )
                ],
            )
        )


@pytest.mark.parametrize(
    ("language", "items", "query", "expected_first"),
    [
        (
            "ka",
            [
                ("აჭარული ხაჭაპური", "ყველი, კვერცხი და კარაქი"),
                ("ხინკალი", "ხორცით"),
                ("პარკინგი", "უფასო პარკინგი ეზოში"),
            ],
            "ხაჭაპურის ფასი",
            "აჭარული ხაჭაპური",
        ),
        (
            "ru",
            [
                ("Хачапури по-аджарски", "Сыр, яйцо, масло"),
                ("Салат цезарь", "Курица и романо"),
                ("Парковка", "Бесплатная парковка во дворе"),
            ],
            "есть ли у вас парковка?",
            "Парковка",
        ),
        (
            "en",
            [
                ("Margherita pizza", "Tomato, mozzarella, basil"),
                ("Caesar salad", "Chicken, romaine, parmesan"),
                ("Parking", "Free parking in the yard"),
            ],
            "do you have salads",
            "Caesar salad",
        ),
        (
            "he",
            [
                ("פיצה מרגריטה", "עגבניות, מוצרלה"),
                ("סלט ירקות", "ירקות טריים"),
                ("חניה", "חניה חינם בחצר"),
            ],
            "יש לכם חנייה?",
            "חניה",
        ),
        (
            "ar",
            [
                ("شاورما دجاج", "خبز عربي"),
                ("فلافل", "حمص مقلي"),
                ("موقف السيارات", "موقف مجاني"),
            ],
            "هل يوجد الفلافل",
            "فلافل",
        ),
        (
            "zh",
            [
                ("冰拿铁", "牛奶咖啡"),
                ("绿茶", "热饮"),
                ("停车场", "免费停车"),
            ],
            "有停车位吗",
            "停车场",
        ),
    ],
)
def test_search_finds_the_relevant_fact_in_many_languages(
    language: str,
    items: list[tuple[str, str]],
    query: str,
    expected_first: str,
) -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(languages=(language, "en"), owner_language=language)
    for title, body in items:
        add_item(harness, business, title, body=body, price_minor=1000)

    titles = search(harness, business, query, language)

    assert titles[0] == expected_first


def test_search_skips_inactive_items_respects_the_limit_and_formats_prices() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    for index in range(8):
        add_item(harness, business, f"Pizza {index}", price_minor=1000 + index)
    add_item(harness, business, "Pizza secret", price_minor=1, is_active=False)

    result = harness.search_knowledge.run(
        KnowledgeSearchRequest(
            business_id=business.id,
            query=KnowledgeSearchQuery("pizza"),
            language=LanguageTag("ru"),
            limit=KnowledgeSearchLimit(3),
        )
    )

    assert len(result.items) == 3
    assert all(item.title != "Pizza secret" for item in result.items)
    assert result.items[0].formatted_price is not None
    assert result.items[0].formatted_price.endswith("GEL")
    assert result.items[0].currency_code == "GEL"


def test_search_of_unknown_business_is_not_found() -> None:
    harness = KnowledgeHarness()

    with pytest.raises(NotFoundError):
        harness.search_knowledge.run(
            KnowledgeSearchRequest(
                business_id=BusinessId(),
                query=KnowledgeSearchQuery("pizza"),
                language=LanguageTag("en"),
            )
        )


def test_get_price_matches_fuzzily_and_formats_in_the_request_language() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    add_item(harness, business, "Хачапури по-аджарски", price_minor=1800)
    add_item(harness, business, "Хачапури по-имеретински", price_minor=1500)
    add_item(harness, business, "Лобиани", price_minor=900)
    add_item(harness, business, "Хинкали", price_minor=120, is_active=False)
    add_item(harness, business, "Парковка", kind=KnowledgeItemKind.FAQ)

    result = harness.get_price.run(
        PriceLookupQuery(
            business_id=business.id,
            item_name=KnowledgeTitle("аджарский хачапури"),
            language=LanguageTag("ka"),
        )
    )

    assert [match.title for match in result.matches][0] == "Хачапури по-аджарски"
    assert result.matches[0].formatted_price == "18,00\xa0₾"
    assert price_titles(harness, business, "lobiani") == []
    assert price_titles(harness, business, "Лабиани") == ["Лобиани"]
    assert price_titles(harness, business, "хинкали") == []
    assert price_titles(harness, business, "парковка") == []


@pytest.mark.parametrize(
    ("titles", "item_name", "expected"),
    [
        (["აჭარული ხაჭაპური", "ხინკალი"], "ხაჭაპური", ["აჭარული ხაჭაპური"]),
        (["Margherita pizza", "Latte"], "late", ["Latte"]),
        (["פיצה מרגריטה", "סלט"], "הפיצה", ["פיצה מרגריטה"]),
        (["شاورما دجاج", "فلافل"], "الفلافل", ["فلافل"]),
        (["冰拿铁", "绿茶"], "拿铁", ["冰拿铁"]),
        (["Margherita pizza", "Latte"], "sushi", []),
        (["Fried rice", "Latte"], "price of pizza", []),
    ],
)
def test_get_price_across_scripts_and_not_in_the_price_list(
    titles: list[str],
    item_name: str,
    expected: list[str],
) -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    for title in titles:
        add_item(harness, business, title, price_minor=1000)

    assert price_titles(harness, business, item_name) == expected


def test_send_link_returns_only_links_from_the_profile() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    assert (
        harness.send_link.run(
            SendLinkQuery(business_id=business.id, kind=BusinessLinkKind.MENU)
        ).url
        is None
    )

    save_step(
        harness,
        business,
        ChannelsStepInput(
            links=[
                BusinessLink(
                    kind=BusinessLinkKind.MENU,
                    url=WebLink("https://venue.example/menu.pdf"),
                )
            ]
        ),
    )
    save_step(
        harness,
        business,
        ContactsAndHoursStepInput(
            address=BusinessAddress(
                text=AddressText("Kutaisi, Tsereteli 5"),
                maps_url=WebLink("https://maps.example.com/kutaisi"),
            )
        ),
    )

    menu = harness.send_link.run(
        SendLinkQuery(business_id=business.id, kind=BusinessLinkKind.MENU)
    )
    map_link = harness.send_link.run(
        SendLinkQuery(business_id=business.id, kind=BusinessLinkKind.MAP)
    )
    payment = harness.send_link.run(
        SendLinkQuery(business_id=business.id, kind=BusinessLinkKind.PAYMENT)
    )

    assert menu.url == "https://venue.example/menu.pdf"
    assert map_link.url == "https://maps.example.com/kutaisi"
    assert payment.kind is BusinessLinkKind.PAYMENT
    assert payment.url is None
