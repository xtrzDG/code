"""Knowledge search in many languages: relevance, inactive items, limits, prices."""

import pytest

from app.schemas.dto.knowledge import (
    KnowledgeSearchRequest,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_integers import (
    KnowledgeSearchLimit,
)
from app.schemas.typings.knowledge.strings import (
    KnowledgeSearchQuery,
)
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
)
from tests.knowledge.harness import KnowledgeHarness
from tests.knowledge.knowledge_base_helpers import add_item, search


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
