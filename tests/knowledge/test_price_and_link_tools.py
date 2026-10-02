"""The price lookup and send-link tools over the knowledge base and profile."""

import pytest

from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.profiles import BusinessAddress, BusinessLink
from app.schemas.dto.knowledge import PriceLookupQuery, SendLinkQuery
from app.schemas.dto.profiles.profile_steps import (
    ChannelsStepInput,
    ContactsAndHoursStepInput,
)
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.strings import AddressText
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.knowledge.harness import KnowledgeHarness
from tests.knowledge.knowledge_base_helpers import add_item, price_titles, save_step


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
