import base64
import json
from typing import Any

import httpx
import pytest

from app.adapters.llm.menu_extraction_adapter import MenuExtractionAdapter
from app.schemas.constants.knowledge import KnowledgeItemKind, KnowledgeItemSource
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.menu_import import (
    ExtractedMenuItem,
    MenuExtraction,
    MenuExtractionRequest,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.knowledge.constrained_strings import KnowledgeTag
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.menu_import.constrained_floats import ExtractionConfidence
from app.schemas.typings.menu_import.constrained_strings import (
    ExtractedPriceAmount,
    MenuSourceMediaType,
)
from app.schemas.typings.menu_import.strings import MenuSourceBase64
from app.schemas.typings.users.prefixed_id import UserId
from tests.brain.brain_world import ISRAEL, BrainWorld, build_world, scripted
from tests.brain.cabinet_http import bearer, build_cabinet_client
from tests.brain.provider_http_fakes import (
    ScriptedHttp,
    build_openai_client,
    openai_message_item,
    openai_response,
)

MENU_JSON: dict[str, Any] = {
    "items": [
        {
            "kind": "menu_item",
            "title": "აჭარული ხაჭაპური",
            "body": "Cheese bread with egg",
            "price": "18,50",
            "currency": "gel",
            "duration_minutes": None,
            "tags": ["Vegetarian", "hot dish", "!!"],
            "confidence": 0.93,
        },
        {
            "kind": "menu_item",
            "title": "Lemonade",
            "body": None,
            "price": 5,
            "currency": None,
            "duration_minutes": None,
            "tags": [],
            "confidence": 1.7,
        },
        {
            "kind": "service",
            "title": "  ",
            "body": None,
            "price": None,
            "currency": None,
            "duration_minutes": None,
            "tags": [],
            "confidence": 0.5,
        },
        {"kind": "faq", "title": "Parking", "confidence": 0.9},
        "not an object",
    ]
}
PNG_BYTES: bytes = b"\x89PNG\r\n\x1a\n-menu-photo"


def build_adapter(
    http: ScriptedHttp,
    page_handler: Any = None,
    addresses: list[str] | None = None,
) -> MenuExtractionAdapter:
    return MenuExtractionAdapter(
        client=build_openai_client(http),
        model_id=LlmModelId("gpt-5-mini"),
        page_transport=None
        if page_handler is None
        else httpx.MockTransport(page_handler),
        host_resolver=lambda host: (
            ["93.184.216.34"] if addresses is None else addresses
        ),
    )


def extraction_request(**changes: Any) -> MenuExtractionRequest:
    request = MenuExtractionRequest(
        media_type=MenuSourceMediaType("image/png"),
        data_base64=MenuSourceBase64(base64.b64encode(PNG_BYTES).decode()),
        language=LanguageTag("ka"),
        currency_code=CurrencyCode("GEL"),
    )
    return request.model_copy(update=changes)


def menu_response(payload: dict[str, Any] | str) -> Any:
    text: str = payload if isinstance(payload, str) else json.dumps(payload)
    return openai_response([openai_message_item(text)])


def test_photo_menu_is_read_with_vision_and_strict_json() -> None:
    http = ScriptedHttp([menu_response(MENU_JSON)])
    adapter = build_adapter(http)

    extraction = adapter.extract(extraction_request())

    body: dict[str, Any] = http.body(0)
    content: list[dict[str, Any]] = body["input"][0]["content"]
    assert content[0] == {
        "type": "input_image",
        "image_url": "data:image/png;base64," + base64.b64encode(PNG_BYTES).decode(),
        "detail": "high",
    }
    assert "business currency is GEL" in content[1]["text"]
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["text"]["format"]["strict"] is True
    assert body["store"] is False
    assert body["model"] == "gpt-5-mini"
    assert [item.title for item in extraction.items] == [
        KnowledgeTitle("აჭარული ხაჭაპური"),
        KnowledgeTitle("Lemonade"),
    ]
    first, second = extraction.items
    assert first.price == ExtractedPriceAmount("18.50")
    assert first.currency_code == CurrencyCode("GEL")
    assert first.tags == [KnowledgeTag("vegetarian"), KnowledgeTag("hot-dish")]
    assert second.price == ExtractedPriceAmount("5")
    assert float(second.confidence) == 1.0
    assert int(extraction.skipped_line_count) == 3


def test_pdf_and_text_menus_use_file_and_text_inputs() -> None:
    http = ScriptedHttp([menu_response({"items": []}), menu_response({"items": []})])
    adapter = build_adapter(http)
    pdf = b"%PDF-1.7 menu"

    adapter.extract(
        extraction_request(
            media_type=MenuSourceMediaType("application/pdf"),
            data_base64=MenuSourceBase64(base64.b64encode(pdf).decode()),
        )
    )
    adapter.extract(
        extraction_request(
            media_type=MenuSourceMediaType("text/plain"),
            data_base64=MenuSourceBase64(
                base64.b64encode("Борщ — 9 ₾".encode()).decode()
            ),
        )
    )

    assert http.body(0)["input"][0]["content"][0] == {
        "type": "input_file",
        "filename": "menu.pdf",
        "file_data": "data:application/pdf;base64," + base64.b64encode(pdf).decode(),
    }
    assert http.body(1)["input"][0]["content"][0] == {
        "type": "input_text",
        "text": "Борщ — 9 ₾",
    }


def test_web_page_menus_are_fetched_as_visible_text_after_checked_redirects() -> None:
    page_requests: list[str] = []

    def serve(request: httpx.Request) -> httpx.Response:
        page_requests.append(str(request.url))
        if request.url.path == "/menu":
            return httpx.Response(302, headers={"location": "/menu/2026"})

        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text=(
                "<html><head><style>p{}</style><script>var x=1;</script></head>"
                "<body><h1>Menu</h1><p>Shakshuka 45 &#8362;</p></body></html>"
            ),
        )

    http = ScriptedHttp([menu_response({"items": []})])
    adapter = build_adapter(http, serve)

    adapter.extract(
        extraction_request(
            media_type=MenuSourceMediaType("text/html"),
            data_base64=None,
            url=WebLink("https://cafe.example/menu"),
        )
    )

    assert page_requests == [
        "https://cafe.example/menu",
        "https://cafe.example/menu/2026",
    ]
    assert http.body(0)["input"][0]["content"][0] == {
        "type": "input_text",
        "text": "Menu\nShakshuka 45 ₪",
    }


@pytest.mark.parametrize(
    ("url", "addresses"),
    [
        ("http://localhost:8000/menu", None),
        ("https://printer.local/menu", None),
        ("https://intranet.example/menu", ["10.0.0.7"]),
        ("https://metadata.example/latest", ["169.254.169.254"]),
        ("https://loop.example/menu", ["127.0.0.1"]),
        ("https://v6.example/menu", ["::1"]),
    ],
)
def test_links_to_private_addresses_are_refused(
    url: str,
    addresses: list[str] | None,
) -> None:
    def never(request: httpx.Request) -> httpx.Response:
        raise AssertionError("A private address must not be fetched.")

    adapter = build_adapter(ScriptedHttp([]), never, addresses)

    with pytest.raises(ValidationFailedError, match="public address"):
        adapter.extract(
            extraction_request(
                media_type=MenuSourceMediaType("text/html"),
                data_base64=None,
                url=WebLink(url),
            )
        )


def test_redirects_to_private_addresses_are_refused_too() -> None:
    def serve(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://localhost/admin"})

    adapter = build_adapter(ScriptedHttp([]), serve)

    with pytest.raises(ValidationFailedError, match="public address"):
        adapter.extract(
            extraction_request(
                media_type=MenuSourceMediaType("text/html"),
                data_base64=None,
                url=WebLink("https://cafe.example/menu"),
            )
        )


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"data_base64": MenuSourceBase64("not base64!!")}, ValidationFailedError),
        ({"media_type": MenuSourceMediaType("video/mp4")}, ValidationFailedError),
    ],
)
def test_unreadable_uploads_are_rejected(
    changes: dict[str, Any],
    error: type[Exception],
) -> None:
    adapter = build_adapter(ScriptedHttp([]))

    with pytest.raises(error):
        adapter.extract(extraction_request(**changes))


def test_bad_model_output_is_a_provider_error() -> None:
    http = ScriptedHttp([menu_response("not json"), menu_response({"lines": []})])
    adapter = build_adapter(http)

    for _ in range(2):
        with pytest.raises(ExternalServiceError):
            adapter.extract(extraction_request())


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
