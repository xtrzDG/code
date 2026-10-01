import base64
import binascii
import ipaddress
import json
import re
import socket
from collections.abc import Callable
from html.parser import HTMLParser
from typing import cast
from urllib.parse import urljoin, urlsplit

import httpx
from openai.types.responses import Response
from pydantic import ValidationError

from app.contracts.brain import MenuExtractionAdapterContract
from app.contracts.llm_clients import OpenAiResponsesClientContract
from app.schemas.constants.knowledge import KnowledgeItemKind
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
from app.schemas.typings.knowledge.constrained_integers import ServiceDurationMinutes
from app.schemas.typings.knowledge.constrained_strings import KnowledgeTag
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.menu_import.constrained_floats import ExtractionConfidence
from app.schemas.typings.menu_import.constrained_integers import MenuLineCount
from app.schemas.typings.menu_import.constrained_strings import ExtractedPriceAmount

type HostResolver = Callable[[str], list[str]]

IMAGE_MEDIA_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/webp", "image/gif"}
)
PDF_MEDIA_TYPE: str = "application/pdf"
TEXT_MEDIA_TYPES: frozenset[str] = frozenset({"text/plain", "text/csv", "text/html"})
HTML_MEDIA_TYPE: str = "text/html"
PAGE_TIMEOUT_SECONDS: float = 10.0
MAX_PAGE_BYTES: int = 10 * 1024 * 1024
MAX_REDIRECTS: int = 3
MAX_MENU_TEXT_CHARACTERS: int = 60_000
MAX_OUTPUT_TOKENS: int = 32_000
MAX_TAGS_PER_ITEM: int = 5
REASONING_EFFORT: str = "low"
PRICE_PATTERN: re.Pattern[str] = re.compile(r"^\d{1,12}(?:[.,]\d{1,4})?$")
CURRENCY_PATTERN: re.Pattern[str] = re.compile(r"^[A-Z]{3}$")
TAG_CLEANUP_PATTERN: re.Pattern[str] = re.compile(r"[^a-z0-9_\-]+")
BLOCKED_HOST_SUFFIXES: tuple[str, ...] = (".localhost", ".local", ".internal")
MENU_ITEM_KINDS: list[str] = [
    kind.value
    for kind in KnowledgeItemKind
    if kind not in (KnowledgeItemKind.FAQ, KnowledgeItemKind.POLICY)
]
EXTRACTION_INSTRUCTIONS: str = (
    "You read menus and price lists of businesses (restaurants, salons, hotels, "
    "clubs, shops) in any language and return every line a customer can order "
    "or book as one item.\n"
    "- kind: menu_item for food and drinks, service for services, room_type for "
    "rooms, package for packages and sets, vehicle for vehicles, product for "
    "goods.\n"
    "- title: the name exactly as printed, in the printed language.\n"
    "- body: a short description if printed, else null.\n"
    "- price: the printed price as a plain number in major units with a dot "
    "(for example 18.50), else null. Never compute or guess a price.\n"
    "- currency: the ISO 4217 code of the printed currency (₾ is GEL, € is EUR, "
    "₪ is ILS, ֏ is AMD), or null when no currency is printed.\n"
    "- duration_minutes: the printed duration of a service, else null.\n"
    "- tags: up to five short lowercase English tags (vegetarian, spicy, "
    "kids, alcohol), or an empty list.\n"
    "- confidence: from 0 to 1, how sure you are that title and price are "
    "read correctly (blurred or cut text lowers it).\n"
    "Do not invent items. Skip headings, addresses and opening hours."
)
NULLABLE_STRING: dict[str, object] = {"anyOf": [{"type": "string"}, {"type": "null"}]}
MENU_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": MENU_ITEM_KINDS},
                    "title": {"type": "string"},
                    "body": NULLABLE_STRING,
                    "price": NULLABLE_STRING,
                    "currency": NULLABLE_STRING,
                    "duration_minutes": {
                        "anyOf": [{"type": "integer"}, {"type": "null"}]
                    },
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                },
                "required": [
                    "kind",
                    "title",
                    "body",
                    "price",
                    "currency",
                    "duration_minutes",
                    "tags",
                    "confidence",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}
TEXT_FORMAT: dict[str, object] = {
    "type": "json_schema",
    "name": "menu_items",
    "schema": MENU_SCHEMA,
    "strict": True,
}


class MenuExtractionAdapter(MenuExtractionAdapterContract):
    """
    Reads a menu with a vision-capable OpenAI model (Responses API, strict
    JSON output): photos go as images, PDFs as files, plain text and web
    pages as text. Web pages are fetched over HTTP(S) only from public
    addresses (no loopback, private or link-local hosts), at most
    10 MB, with up to three checked redirects.

    Lines the model returns in an unusable shape (empty title, unknown kind)
    are skipped and counted; malformed prices, currencies, durations and
    tags are dropped from a line rather than failing the import.
    """

    def __init__(
        self,
        client: OpenAiResponsesClientContract,
        model_id: LlmModelId,
        page_transport: httpx.BaseTransport | None = None,
        host_resolver: HostResolver | None = None,
    ) -> None:
        self._client: OpenAiResponsesClientContract = client
        self._model_id: LlmModelId = model_id
        self._page_transport: httpx.BaseTransport | None = page_transport
        self._host_resolver: HostResolver = (
            host_resolver if host_resolver is not None else resolve_host_addresses
        )

    def extract(self, request: MenuExtractionRequest) -> MenuExtraction:
        content: list[dict[str, object]] = self._build_content(request)
        content.append(
            {
                "type": "input_text",
                "text": (
                    "Read this menu. If no currency is printed, the business "
                    f"currency is {request.currency_code}."
                ),
            }
        )
        response: Response = self._client.create_response(
            model=str(self._model_id),
            instructions=EXTRACTION_INSTRUCTIONS,
            input_items=[{"role": "user", "content": content}],
            tools=[],
            reasoning_effort=REASONING_EFFORT,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            text_format=TEXT_FORMAT,
        )
        if response.status == "incomplete" or response.error is not None:
            raise ExternalServiceError("The menu could not be read completely.")

        return parse_menu_extraction(response.output_text)

    def _build_content(self, request: MenuExtractionRequest) -> list[dict[str, object]]:
        if request.data_base64 is not None:
            data: bytes = decode_base64(str(request.data_base64))
            return build_media_content(str(request.media_type), data)

        if request.url is not None:
            media_type, data = self._fetch_page(str(request.url))
            return build_media_content(media_type, data)

        raise ValidationFailedError("Upload a menu file or give a link to it.")

    def _fetch_page(self, url: str) -> tuple[str, bytes]:
        """Download a public page; returns its media type and body."""

        current_url: str = url
        with httpx.Client(
            transport=self._page_transport,
            timeout=PAGE_TIMEOUT_SECONDS,
            follow_redirects=False,
        ) as http_client:
            for _ in range(MAX_REDIRECTS + 1):
                self._require_public_url(current_url)
                try:
                    with http_client.stream("GET", current_url) as response:
                        if response.is_redirect:
                            location: str | None = response.headers.get("location")
                            if location is None:
                                raise ValidationFailedError(
                                    "The menu link redirects to nowhere."
                                )

                            current_url = urljoin(current_url, location)
                            continue

                        if response.status_code >= 400:
                            raise ValidationFailedError(
                                f"The menu link answered HTTP {response.status_code}."
                            )

                        return (
                            read_media_type(response.headers.get("content-type")),
                            read_limited_body(response),
                        )
                except httpx.HTTPError as error:
                    raise ExternalServiceError(
                        f"The menu link cannot be opened: {type(error).__name__}."
                    ) from error

        raise ValidationFailedError("The menu link redirects too many times.")

    def _require_public_url(self, url: str) -> None:
        parts = urlsplit(url)
        host: str = (parts.hostname or "").lower()
        if parts.scheme not in ("http", "https") or host == "":
            raise ValidationFailedError("The menu link must be an http(s) address.")

        if host == "localhost" or host.endswith(BLOCKED_HOST_SUFFIXES):
            raise ValidationFailedError("The menu link must be a public address.")

        try:
            addresses: list[str] = self._host_resolver(host)
        except OSError as error:
            raise ValidationFailedError("The menu link's host is unknown.") from error

        if not addresses or any(
            not is_public_address(address) for address in addresses
        ):
            raise ValidationFailedError("The menu link must be a public address.")


def build_media_content(media_type: str, data: bytes) -> list[dict[str, object]]:
    """Responses input parts for a menu file of the given media type."""

    if media_type in IMAGE_MEDIA_TYPES:
        encoded: str = base64.b64encode(data).decode("ascii")
        return [
            {
                "type": "input_image",
                "image_url": f"data:{media_type};base64,{encoded}",
                "detail": "high",
            }
        ]

    if media_type == PDF_MEDIA_TYPE:
        encoded = base64.b64encode(data).decode("ascii")
        return [
            {
                "type": "input_file",
                "filename": "menu.pdf",
                "file_data": f"data:{PDF_MEDIA_TYPE};base64,{encoded}",
            }
        ]

    if media_type in TEXT_MEDIA_TYPES:
        text: str = data.decode("utf-8", errors="replace")
        if media_type == HTML_MEDIA_TYPE:
            text = extract_visible_text(text)

        return [{"type": "input_text", "text": text[:MAX_MENU_TEXT_CHARACTERS]}]

    raise ValidationFailedError(
        f"Menus can be photos, PDF files, text or web pages, not {media_type}."
    )


def parse_menu_extraction(output_text: str) -> MenuExtraction:
    """
    Validate the model's JSON line by line.

    Raises:
        ExternalServiceError: the output is not the requested JSON object.
    """

    try:
        decoded: object = json.loads(output_text)
    except json.JSONDecodeError as error:
        raise ExternalServiceError("The menu model returned invalid JSON.") from error

    raw_items: object = (
        cast(dict[str, object], decoded).get("items")
        if isinstance(decoded, dict)
        else None
    )
    if not isinstance(raw_items, list):
        raise ExternalServiceError("The menu model returned no item list.")

    items: list[ExtractedMenuItem] = []
    skipped_line_count: int = 0
    for raw_item in cast(list[object], raw_items):
        item: ExtractedMenuItem | None = (
            read_menu_item(cast(dict[str, object], raw_item))
            if isinstance(raw_item, dict)
            else None
        )
        if item is None:
            skipped_line_count += 1
        else:
            items.append(item)

    return MenuExtraction(
        items=items,
        skipped_line_count=MenuLineCount(skipped_line_count),
    )


def read_menu_item(raw_item: dict[str, object]) -> ExtractedMenuItem | None:
    title: object = raw_item.get("title")
    kind: object = raw_item.get("kind")
    if (
        not isinstance(title, str)
        or title.strip() == ""
        or not isinstance(kind, str)
        or kind not in MENU_ITEM_KINDS
    ):
        return None

    body: object = raw_item.get("body")
    try:
        return ExtractedMenuItem(
            kind=KnowledgeItemKind(kind),
            title=KnowledgeTitle(title.strip()),
            body=(
                KnowledgeBody(body.strip())
                if isinstance(body, str) and body.strip() != ""
                else None
            ),
            price=read_price(raw_item.get("price")),
            currency_code=read_currency(raw_item.get("currency")),
            duration_minutes=read_duration(raw_item.get("duration_minutes")),
            tags=read_tags(raw_item.get("tags")),
            confidence=read_confidence(raw_item.get("confidence")),
        )
    except ValidationError, ValueError:
        return None


def read_price(raw_price: object) -> ExtractedPriceAmount | None:
    if isinstance(raw_price, int | float) and not isinstance(raw_price, bool):
        raw_price = f"{raw_price}"

    if not isinstance(raw_price, str):
        return None

    compact: str = raw_price.strip().replace(" ", "").replace(" ", "")
    if PRICE_PATTERN.fullmatch(compact) is None:
        return None

    return ExtractedPriceAmount(compact.replace(",", "."))


def read_currency(raw_currency: object) -> CurrencyCode | None:
    if not isinstance(raw_currency, str):
        return None

    code: str = raw_currency.strip().upper()
    return CurrencyCode(code) if CURRENCY_PATTERN.fullmatch(code) else None


def read_duration(raw_duration: object) -> ServiceDurationMinutes | None:
    if not isinstance(raw_duration, int) or isinstance(raw_duration, bool):
        return None

    try:
        return ServiceDurationMinutes(raw_duration)
    except ValueError:
        return None


def read_tags(raw_tags: object) -> list[KnowledgeTag]:
    if not isinstance(raw_tags, list):
        return []

    tags: list[KnowledgeTag] = []
    for raw_tag in cast(list[object], raw_tags):
        if not isinstance(raw_tag, str):
            continue

        cleaned: str = TAG_CLEANUP_PATTERN.sub("-", raw_tag.strip().lower()).strip("-_")
        try:
            tag = KnowledgeTag(cleaned)
        except ValueError:
            continue

        if tag not in tags:
            tags.append(tag)

    return tags[:MAX_TAGS_PER_ITEM]


def read_confidence(raw_confidence: object) -> ExtractionConfidence:
    if isinstance(raw_confidence, bool) or not isinstance(raw_confidence, int | float):
        return ExtractionConfidence(0.0)

    return ExtractionConfidence(min(1.0, max(0.0, float(raw_confidence))))


def decode_base64(data_base64: str) -> bytes:
    try:
        return base64.b64decode(data_base64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValidationFailedError("The menu file is not valid base64.") from error


def read_media_type(content_type: str | None) -> str:
    if content_type is None:
        return HTML_MEDIA_TYPE

    return content_type.split(";", 1)[0].strip().lower()


def read_limited_body(response: httpx.Response) -> bytes:
    body = bytearray()
    for chunk in response.iter_bytes():
        body.extend(chunk)
        if len(body) > MAX_PAGE_BYTES:
            raise ValidationFailedError(
                "The menu behind the link is larger than 10 MB."
            )

    return bytes(body)


def resolve_host_addresses(host: str) -> list[str]:
    """IP addresses a host name resolves to (raises OSError when unknown)."""

    return sorted(
        {
            str(info[4][0])
            for info in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        }
    )


def is_public_address(address: str) -> bool:
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False

    return parsed.is_global and not parsed.is_multicast


class _VisibleTextParser(HTMLParser):
    """Collects the text of an HTML page without scripts and styles."""

    IGNORED_TAGS: frozenset[str] = frozenset(
        {"script", "style", "noscript", "template"}
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth: int = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in self.IGNORED_TAGS:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self.IGNORED_TAGS and self._ignored_depth > 0:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth == 0 and data.strip() != "":
            self.parts.append(data.strip())


def extract_visible_text(html: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(html)
    parser.close()
    return "\n".join(parser.parts)
