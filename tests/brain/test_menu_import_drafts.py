"""Imported menu items: inactive drafts, confirm, discard, prices and HTTP errors."""

import base64
from typing import Any

from app.schemas.constants.knowledge import KnowledgeItemKind, KnowledgeItemSource
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.menu_import import (
    ExtractedMenuItem,
    MenuExtraction,
    MenuExtractionRequest,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.menu_import.constrained_floats import ExtractionConfidence
from app.schemas.typings.menu_import.constrained_strings import ExtractedPriceAmount
from app.schemas.typings.users.prefixed_id import UserId
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.business_setups import ISRAEL
from tests.brain.cabinet_http import bearer, build_cabinet_client
from tests.brain.menu_extraction_helpers import PNG_BYTES
from tests.brain.scripted_turns import scripted


class FakeMenuExtractor:
    """Returns prepared lines and remembers the requests."""

    def __init__(self, items: list[ExtractedMenuItem]) -> None:
        self.items: list[ExtractedMenuItem] = items
        self.requests: list[MenuExtractionRequest] = []

    def extract(self, request: MenuExtractionRequest) -> MenuExtraction:
        self.requests.append(request)
        return MenuExtraction(items=self.items)


def extracted(
    title: str,
    price: str | None,
    currency: str | None,
    confidence: float = 0.9,
) -> ExtractedMenuItem:
    return ExtractedMenuItem(
        kind=KnowledgeItemKind.MENU_ITEM,
        title=KnowledgeTitle(title),
        price=None if price is None else ExtractedPriceAmount(price),
        currency_code=None if currency is None else CurrencyCode(currency),
        confidence=ExtractionConfidence(confidence),
    )


def items_of(world: BrainWorld) -> list[KnowledgeItemDocument]:
    return world.knowledge_item_repo.list_by_business(world.business.id)


def test_import_creates_inactive_drafts_and_confirm_activates_them() -> None:
    world = build_world(scripted())
    extractor = FakeMenuExtractor(
        [
            extracted("Adjarian khachapuri", "18.50", "GEL", 0.93),
            extracted("Lemonade", "5", None, 0.71),
            extracted("Imported wine", "12", "USD", 0.88),
            extracted("Chef's surprise", None, None, 0.4),
        ]
    )
    client = build_cabinet_client(
        world, extractor, {"owner": world.owner_id, "staff": world.staff_id}
    )
    base_url = f"/v1/businesses/{world.business.id}/knowledge/import"

    imported = client.post(
        base_url,
        json={
            "media_type": "image/png",
            "data_base64": base64.b64encode(PNG_BYTES).decode(),
        },
        headers=bearer("staff"),
    )

    assert imported.status_code == 201
    rows: list[dict[str, Any]] = imported.json()["items"]
    assert [row["item"]["title"] for row in rows] == [
        "Adjarian khachapuri",
        "Lemonade",
        "Imported wine",
        "Chef's surprise",
    ]
    assert [row["item"]["price_minor"] for row in rows] == [1850, 500, None, None]
    assert rows[0]["item"]["currency_code"] == "GEL"
    assert rows[0]["item"]["formatted_price"] == "18,50\u00a0₾"
    assert [row["confidence"] for row in rows] == [0.93, 0.71, 0.88, 0.4]
    assert [row["is_currency_mismatch"] for row in rows] == [False, False, True, False]
    assert rows[2]["printed_price"] == "12"
    assert rows[2]["printed_currency_code"] == "USD"
    assert extractor.requests[0].language == "ka"
    assert extractor.requests[0].currency_code == "GEL"
    stored = items_of(world)
    assert all(item.is_active is False for item in stored)
    assert all(item.source is KnowledgeItemSource.MENU_IMPORT for item in stored)

    batch_id: str = imported.json()["batch_id"]
    assert batch_id.startswith("menu_import_")
    assert {str(item.import_batch_id) for item in stored} == {batch_id}

    chosen_ids = [rows[0]["item"]["id"], rows[1]["item"]["id"]]
    confirmed = client.post(
        f"{base_url}/confirm",
        json={"item_ids": chosen_ids},
        headers=bearer("owner"),
    )

    assert confirmed.status_code == 200
    assert [item["id"] for item in confirmed.json()["activated_items"]] == chosen_ids
    active_titles = {str(item.title) for item in items_of(world) if item.is_active}
    assert active_titles == {"Adjarian khachapuri", "Lemonade"}

    # The rest of the import is discarded at once; confirmed items stay,
    # even when they are switched off later.
    lemonade = next(item for item in items_of(world) if item.title == "Lemonade")
    lemonade.is_active = False
    world.knowledge_item_repo.save(lemonade)
    discarded = client.delete(f"{base_url}/{batch_id}", headers=bearer("staff"))

    assert (discarded.status_code, discarded.content) == (204, b""), discarded.text
    assert sorted(str(item.title) for item in items_of(world)) == [
        "Adjarian khachapuri",
        "Lemonade",
    ]
    # Discarding again finds nothing left and changes nothing.
    again = client.delete(f"{base_url}/{batch_id}", headers=bearer("owner"))
    assert again.status_code == 204
    assert len(items_of(world)) == 2


def test_discarding_an_import_touches_only_its_own_drafts() -> None:
    world = build_world(scripted())
    extractor = FakeMenuExtractor([extracted("Tea", "3", None)])
    client = build_cabinet_client(
        world, extractor, {"owner": world.owner_id, "stranger": UserId()}
    )
    base_url = f"/v1/businesses/{world.business.id}/knowledge/import"
    body = {"media_type": "text/plain", "data_base64": "VGVh"}
    first = client.post(base_url, json=body, headers=bearer("owner")).json()
    second = client.post(base_url, json=body, headers=bearer("owner")).json()
    owner_draft = KnowledgeItemDocument(
        business_id=world.business.id,
        kind=KnowledgeItemKind.SERVICE,
        title=KnowledgeTitle("Switched off by the owner"),
        is_active=False,
    )
    world.knowledge_item_repo.save(owner_draft)

    stranger = client.delete(
        f"{base_url}/{first['batch_id']}", headers=bearer("stranger")
    )
    malformed = client.delete(f"{base_url}/not-a-batch", headers=bearer("owner"))
    discarded = client.delete(
        f"{base_url}/{first['batch_id']}", headers=bearer("owner")
    )

    assert (stranger.status_code, malformed.status_code) == (404, 404)
    assert discarded.status_code == 204
    assert sorted(item.id for item in items_of(world)) == sorted(
        [KnowledgeItemId(second["items"][0]["item"]["id"]), owner_draft.id]
    )


def test_prices_follow_the_currency_precision_of_any_business() -> None:
    world = build_world(scripted(), ISRAEL)
    extractor = FakeMenuExtractor([extracted("Shakshuka", "45", "ILS")])
    client = build_cabinet_client(world, extractor, {"owner": world.owner_id})

    imported = client.post(
        f"/v1/businesses/{world.business.id}/knowledge/import",
        json={"media_type": "text/plain", "data_base64": "U2hha3NodWthIDQ1"},
        headers=bearer("owner"),
    )

    item = imported.json()["items"][0]["item"]
    assert item["price_minor"] == 4500
    assert item["currency_code"] == "ILS"
    assert "45" in item["formatted_price"]
    assert "₪" in item["formatted_price"]


def test_menu_import_errors_map_to_http_status_codes() -> None:
    world = build_world(scripted())
    foreign_item = KnowledgeItemDocument(
        business_id=world.business.id,
        kind=KnowledgeItemKind.FAQ,
        title=KnowledgeTitle("Parking"),
    )
    world.knowledge_item_repo.save(foreign_item)
    client = build_cabinet_client(
        world,
        FakeMenuExtractor([]),
        {"owner": world.owner_id, "stranger": UserId()},
    )
    base_url = f"/v1/businesses/{world.business.id}/knowledge/import"
    owner = bearer("owner")

    responses = {
        "both sources": client.post(
            base_url,
            json={
                "media_type": "image/png",
                "data_base64": "AAAA",
                "url": "https://cafe.example/menu",
            },
            headers=owner,
        ),
        "no source": client.post(
            base_url, json={"media_type": "image/png"}, headers=owner
        ),
        "bad media type": client.post(
            base_url,
            json={"media_type": "video/mp4", "data_base64": "AAAA"},
            headers=owner,
        ),
        "bad url": client.post(
            base_url,
            json={"media_type": "text/html", "url": "ftp://cafe.example/menu"},
            headers=owner,
        ),
        "stranger": client.post(
            base_url,
            json={"media_type": "image/png", "data_base64": "AAAA"},
            headers=bearer("stranger"),
        ),
        "confirm nothing": client.post(
            f"{base_url}/confirm", json={"item_ids": []}, headers=owner
        ),
        "confirm unknown": client.post(
            f"{base_url}/confirm",
            json={"item_ids": [str(KnowledgeItemId())]},
            headers=owner,
        ),
        "confirm not imported": client.post(
            f"{base_url}/confirm",
            json={"item_ids": [str(foreign_item.id)]},
            headers=owner,
        ),
    }

    assert {name: response.status_code for name, response in responses.items()} == {
        "both sources": 422,
        "no source": 422,
        "bad media type": 422,
        "bad url": 422,
        "stranger": 404,
        "confirm nothing": 422,
        "confirm unknown": 404,
        "confirm not imported": 422,
    }
    assert len(items_of(world)) == 1
