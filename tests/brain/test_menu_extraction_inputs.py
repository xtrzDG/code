"""Menu extraction from photos, PDFs, text and web pages, and bad inputs or output."""

import base64
from typing import Any

import httpx
import pytest

from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.knowledge.constrained_strings import KnowledgeTag
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
)
from app.schemas.typings.menu_import.constrained_strings import (
    ExtractedPriceAmount,
    MenuSourceMediaType,
)
from app.schemas.typings.menu_import.strings import MenuSourceBase64
from tests.brain.menu_extraction_helpers import (
    MENU_JSON,
    PNG_BYTES,
    build_adapter,
    extraction_request,
    menu_response,
)
from tests.brain.provider_http_fakes import (
    ScriptedHttp,
)


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
