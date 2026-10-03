"""Shared inputs for menu import tests: a sample menu, upload requests, link fetches."""

import base64
import json
from typing import Any

from app.adapters.llm.menu_extraction.menu_extraction_adapter import (
    MenuExtractionAdapter,
)
from app.clients.http.safe_http_fetcher import SafeHttpFetcher
from app.schemas.dto.menu_import import MenuExtractionRequest
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.menu_import.constrained_strings import (
    MenuSourceBase64,
    MenuSourceMediaType,
)
from tests.brain.provider_http_fakes import (
    ScriptedHttp,
    build_openai_client,
    openai_message_item,
    openai_response,
)
from tests.web_fetching.fetch_fakes import FakeNetwork

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
    network: FakeNetwork | None = None,
) -> MenuExtractionAdapter:
    """The adapter, reading menu links from `network` (none: no links)."""

    pages: FakeNetwork = FakeNetwork({}) if network is None else network
    return MenuExtractionAdapter(
        client=build_openai_client(http),
        model_id=LlmModelId("gpt-5-mini"),
        page_fetcher=SafeHttpFetcher(resolver=pages.resolve, connector=pages.connect),
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


def link_reasons(error: ValidationFailedError) -> list[tuple[str, list[str]]]:
    return [
        (str(reason.code), [str(detail) for detail in reason.details])
        for reason in error.reasons
    ]


def link_request(url: str = "https://cafe.example/menu") -> MenuExtractionRequest:
    return extraction_request(
        media_type=MenuSourceMediaType("text/html"),
        data_base64=None,
        url=WebLink(url),
    )
